"""Minimal playable Pac-Man-like loop with states."""

from __future__ import annotations

from collections import deque
import random
from threading import Thread

import pygame

from pacman.ghost_logic import (
    check_ghost_collision,
    initialize_ghosts,
    move_ghosts,
)
from pacman.level_flow import (
    check_level_completion,
    find_spawn_position,
    initialize_collectibles,
    start_new_game,
)
from pacman.maze_provider import MazeLevel, MazeProvider, can_move
from pacman.models import GameRuntime, GhostRuntime
from pacman.rendering import draw_game
from pacman.settings import GameSettings


ENTER_KEYS = {pygame.K_RETURN, pygame.K_KP_ENTER}
MOVE_KEYS = {
    pygame.K_UP: (0, -1),
    pygame.K_w: (0, -1),
    pygame.K_RIGHT: (1, 0),
    pygame.K_d: (1, 0),
    pygame.K_DOWN: (0, 1),
    pygame.K_s: (0, 1),
    pygame.K_LEFT: (-1, 0),
    pygame.K_a: (-1, 0),
}
RANDOM_SEED_POOL = (1, 2, 8, 45, 55, 59, 60, 62, 69, 77)
MAX_RANDOM_ATTEMPTS = 2
BLOCKED_CELL_CODE = 15
BASE_WINDOW_WIDTH = 960
BASE_WINDOW_HEIGHT = 720
MIN_WINDOW_WIDTH = 480
MIN_WINDOW_HEIGHT = 360
MAX_WINDOW_WIDTH = 2560
MAX_WINDOW_HEIGHT = 1440
WINDOW_SCREEN_RATIO = 0.9
PLAYER_MOVE_COOLDOWN_MS = 180
GHOST_MOVE_COOLDOWN_MS = 300
COLLISION_DISTANCE_TILES = 0.42


class Game:
    """Main game object handling UI states and play loop."""

    def __init__(self, settings: GameSettings) -> None:
        """Initialize a new game with provided settings.

        Args:
            settings: GameSettings object with game configuration.
        """
        self.settings = settings
        self.window_width = settings.window_width
        self.window_height = settings.window_height
        self.provider = MazeProvider()
        self.current_level_idx = 0
        self.lives = settings.lives
        self.score = 0
        self.level: MazeLevel | None = None
        self.error_message = ""
        self.generation_thread: Thread | None = None
        self.last_move_ms = 0
        self.last_ghost_move_ms = 0
        self.move_cooldown_ms = PLAYER_MOVE_COOLDOWN_MS
        self.ghost_move_cooldown_ms = GHOST_MOVE_COOLDOWN_MS
        self.move_dx = 0
        self.move_dy = 0
        self.desired_dx = 0
        self.desired_dy = 0
        self.spawn_x = 0
        self.spawn_y = 0
        self.player_render_from_x = 0
        self.player_render_from_y = 0
        self.player_render_started_ms = 0
        self.ghosts: list[GhostRuntime] = []
        self.ghost_update_index = 0
        self.game_over_reason = "win"
        self.pacgums: set[tuple[int, int]] = set()
        self.super_pacgums: set[tuple[int, int]] = set()
        self.recent_random_seeds: deque[int] = deque(maxlen=8)
        self.runtime = GameRuntime(
            state="menu",
            player_x=0,
            player_y=0,
            score=0,
        )

    def _pick_random_seed(self) -> int:
        """Pick a random seed, avoiding very recent values."""
        available = [
            seed
            for seed in RANDOM_SEED_POOL
            if seed not in self.recent_random_seeds
        ]
        if not available:
            available = list(RANDOM_SEED_POOL)
        candidate = random.choice(available)
        self.recent_random_seeds.append(candidate)
        return candidate

    def _load_current_level(self) -> MazeLevel:
        """Load the current level from settings."""
        if self.current_level_idx >= len(self.settings.levels):
            self.current_level_idx = 0
        level_config = self.settings.levels[self.current_level_idx]
        if level_config.seed != 0:
            return self.provider.generate(
                width=level_config.width,
                height=level_config.height,
                seed=level_config.seed,
            )

        errors: list[str] = []
        for _ in range(MAX_RANDOM_ATTEMPTS):
            seed = self._pick_random_seed()
            try:
                return self.provider.generate(
                    width=level_config.width,
                    height=level_config.height,
                    seed=seed,
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"seed {seed}: {exc}")

        details = " | ".join(errors[-3:])
        raise RuntimeError(
            "No se pudo generar el laberinto tras varios intentos. "
            f"Detalles: {details}"
        )

    def run(self) -> None:
        """Initialize pygame and run until quit."""
        pygame.init()
        try:
            self.window_width, self.window_height = (
                self._resolve_window_size()
            )
            screen = pygame.display.set_mode(
                (self.window_width, self.window_height)
            )
            pygame.display.set_caption("Pac-Man Python")
            clock = pygame.time.Clock()

            running = True
            while running:
                running = self._process_events()
                self._poll_generation_state()
                self._handle_continuous_movement()
                self._draw(screen)
                pygame.display.flip()
                clock.tick(self.settings.fps)
        finally:
            pygame.quit()

    def _resolve_window_size(self) -> tuple[int, int]:
        """Compute a window size adapted to the current desktop."""
        desktop_w = 0
        desktop_h = 0

        try:
            desktop_sizes = pygame.display.get_desktop_sizes()
        except Exception:  # noqa: BLE001
            desktop_sizes = []

        if desktop_sizes:
            desktop_w, desktop_h = desktop_sizes[0]
        else:
            display_info = pygame.display.Info()
            desktop_w = display_info.current_w
            desktop_h = display_info.current_h

        if desktop_w <= 0 or desktop_h <= 0:
            return self.settings.window_width, self.settings.window_height

        target_width = int(desktop_w * WINDOW_SCREEN_RATIO)
        target_height = int(desktop_h * WINDOW_SCREEN_RATIO)

        target_width = max(MIN_WINDOW_WIDTH, target_width)
        target_height = max(MIN_WINDOW_HEIGHT, target_height)
        target_width = min(MAX_WINDOW_WIDTH, target_width)
        target_height = min(MAX_WINDOW_HEIGHT, target_height)

        return target_width, target_height

    def _ui_scale(self) -> float:
        """Return UI scale factor relative to base resolution."""
        scale_x = self.window_width / BASE_WINDOW_WIDTH
        scale_y = self.window_height / BASE_WINDOW_HEIGHT
        return max(0.75, min(2.0, min(scale_x, scale_y)))

    def _start_level_generation(self) -> None:
        """Start level generation in a background thread."""
        if self.generation_thread is not None:
            return
        self.level = None
        self.error_message = ""
        self.move_dx = 0
        self.move_dy = 0
        self.desired_dx = 0
        self.desired_dy = 0
        self.last_move_ms = 0
        self.last_ghost_move_ms = 0
        self.ghosts = []
        self.ghost_update_index = 0
        self.runtime.state = "loading"
        self.generation_thread = Thread(
            target=self._generate_level_background,
            daemon=True,
        )
        self.generation_thread.start()

    def _generate_level_background(self) -> None:
        """Generate the level without blocking the UI loop."""
        try:
            level = self._load_current_level()
        except Exception as exc:  # noqa: BLE001
            self.level = None
            self.error_message = f"Error al generar el laberinto: {exc}"
            self.runtime.state = "error"
        else:
            self.level = level
            self.spawn_x, self.spawn_y = self._find_spawn_position(level)
            self.runtime.player_x = self.spawn_x
            self.runtime.player_y = self.spawn_y
            self.player_render_from_x = self.spawn_x
            self.player_render_from_y = self.spawn_y
            self.player_render_started_ms = 0
            self.move_dx = 0
            self.move_dy = 0
            self.desired_dx = 0
            self.desired_dy = 0
            self._initialize_collectibles(level)
            self._initialize_ghosts(level)
            self.runtime.state = "playing"
        finally:
            self.generation_thread = None

    def _initialize_ghosts(self, level: MazeLevel) -> None:
        """Spawn four ghosts near maze corners."""
        initialize_ghosts(self, level)

    def _initialize_collectibles(self, level: MazeLevel) -> None:
        """Create pacgums and super-pacgums for the current level."""
        initialize_collectibles(self, level)

    def _find_spawn_position(self, level: MazeLevel) -> tuple[int, int]:
        """Find the walkable cell closest to the maze center."""
        return find_spawn_position(level)

    def _consume_collectibles_at_player(self) -> None:
        """Consume collectible under player and update score."""
        pos = (self.runtime.player_x, self.runtime.player_y)
        if pos in self.pacgums:
            self.pacgums.remove(pos)
            self.runtime.score += self.settings.points_per_pacgum
        if pos in self.super_pacgums:
            self.super_pacgums.remove(pos)
            self.runtime.score += self.settings.points_per_super_pacgum

    def _check_level_completion(self) -> None:
        """Advance to the next level or end the game when cleared."""
        check_level_completion(self)

    def _start_new_game(self) -> None:
        """Reset progression data and start from the first level."""
        start_new_game(self)

    def _on_player_caught(self) -> None:
        """Handle player collision with a ghost."""
        if self.settings.cheat_mode:
            return
        self.lives -= 1
        if self.lives <= 0:
            self.lives = 0
            self.game_over_reason = "lose"
            self.runtime.state = "game_over"
            return

        self.runtime.player_x = self.spawn_x
        self.runtime.player_y = self.spawn_y
        self.player_render_from_x = self.spawn_x
        self.player_render_from_y = self.spawn_y
        self.player_render_started_ms = pygame.time.get_ticks()
        self.move_dx = 0
        self.move_dy = 0
        self.desired_dx = 0
        self.desired_dy = 0
        self.last_move_ms = 0
        for ghost in self.ghosts:
            ghost.x = ghost.spawn_x
            ghost.y = ghost.spawn_y
            ghost.dir_x = 0
            ghost.dir_y = 0
            ghost.stuck_ticks = 0
            ghost.recent_cells.clear()
            ghost.recent_cells.append((ghost.spawn_x, ghost.spawn_y))
            ghost.render_from_x = ghost.spawn_x
            ghost.render_from_y = ghost.spawn_y
            ghost.render_started_ms = pygame.time.get_ticks()

    def _poll_generation_state(self) -> None:
        """Resolve stale loading state if worker ended unexpectedly."""
        if self.runtime.state != "loading":
            return
        if self.generation_thread is not None:
            return
        if self.level is None and not self.error_message:
            self.error_message = "Error inesperado durante la carga del nivel."
            self.runtime.state = "error"

    def _process_events(self) -> bool:
        """Process user input and handle state transitions.

        Returns:
            bool: False if game should quit, True otherwise.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    return False
                if self.runtime.state == "menu":
                    if event.key in ENTER_KEYS:
                        self._start_new_game()
                        self._start_level_generation()
                elif self.runtime.state == "error":
                    if event.key in (pygame.K_q, pygame.K_ESCAPE):
                        return False
                elif (
                    self.runtime.state == "game_over"
                    and event.key in ENTER_KEYS
                ):
                    self.runtime.state = "menu"
                elif self.runtime.state == "playing":
                    self._handle_playing_key(event.key)
        return True

    def _handle_continuous_movement(self) -> None:
        """Move while direction keys are held down."""
        if self.runtime.state != "playing" or not self.level:
            return
        now_ms = pygame.time.get_ticks()
        if now_ms - self.last_move_ms >= self.move_cooldown_ms:
            if self._can_move(self.desired_dx, self.desired_dy):
                self.move_dx = self.desired_dx
                self.move_dy = self.desired_dy

            if self.move_dx != 0 or self.move_dy != 0:
                if self._try_move(self.move_dx, self.move_dy, now_ms):
                    self.last_move_ms = now_ms
                else:
                    self.move_dx = 0
                    self.move_dy = 0

        if now_ms - self.last_ghost_move_ms >= self.ghost_move_cooldown_ms:
            self._move_ghosts(now_ms)
            self.last_ghost_move_ms = now_ms

        self._check_ghost_collision(now_ms)

    def _handle_playing_key(self, key: int) -> None:
        """Handle in-game controls and update player position.

        Args:
            key: Pygame key code from event.
        """
        if not self.level:
            return
        if self.settings.cheat_mode and key == pygame.K_n:
            self.pacgums.clear()
            self.super_pacgums.clear()
            self.runtime.score += 500
            self.game_over_reason = "win"
            self.runtime.state = "game_over"
            return

        if key not in MOVE_KEYS:
            return

        dx, dy = MOVE_KEYS[key]
        self.desired_dx = dx
        self.desired_dy = dy

    def _can_move(self, dx: int, dy: int) -> bool:
        """Check if player can move in the given direction.

        Args:
            dx: Change in x direction (-1, 0, or 1).
            dy: Change in y direction (-1, 0, or 1).

        Returns:
            bool: True if movement is allowed, False otherwise.
        """
        if not self.level:
            return False
        if dx == 0 and dy == 0:
            return False

        x = self.runtime.player_x
        y = self.runtime.player_y
        cell_code = self.level.grid[y][x]
        return can_move(cell_code, dx, dy)

    def _try_move(self, dx: int, dy: int, now_ms: int) -> bool:
        """Attempt player movement and check level completion.

        Collects items under the player and updates game state.
            dx: Change in x direction.
            dy: Change in y direction.
            now_ms: Current time in milliseconds.

        Returns:
            bool: True if move succeeded, False otherwise.
        """
        if not self.level:
            return False

        x = self.runtime.player_x
        y = self.runtime.player_y
        cell_code = self.level.grid[y][x]
        if not can_move(cell_code, dx, dy):
            return False

        new_x = x + dx
        new_y = y + dy
        if (
            0 <= new_x < len(self.level.grid[0])
            and 0 <= new_y < len(self.level.grid)
        ):
            self.player_render_from_x = self.runtime.player_x
            self.player_render_from_y = self.runtime.player_y
            self.player_render_started_ms = now_ms
            self.runtime.player_x = new_x
            self.runtime.player_y = new_y
        else:
            return False

        self._consume_collectibles_at_player()
        self._check_level_completion()
        return True

    def _reset_game(self) -> None:
        """Return to menu without regenerating level."""
        self.runtime.state = "menu"
        self.lives = self.settings.lives
        self.score = 0

    def _draw(self, screen: pygame.Surface) -> None:
        """Render current game state to screen.

        Args:
            screen: Pygame surface to draw to.
        """
        draw_game(self, screen)

    def _check_ghost_collision(self, now_ms: int) -> bool:
        """Check for collisions between player and ghosts.

        Args:
            now_ms: Current time in milliseconds.

        Returns:
            bool: True if collision detected, False otherwise.
        """
        return check_ghost_collision(self, now_ms)

    def _move_ghosts(self, now_ms: int) -> None:
        """Update ghost positions with AI chase logic.

        Args:
            now_ms: Current time in milliseconds.
        """
        move_ghosts(self, now_ms)

    def _get_player_render_position(self, now_ms: int) -> tuple[float, float]:
        """Get smoothly interpolated player position for rendering.

        Args:
            now_ms: Current time in milliseconds.

        Returns:
            tuple[float, float]: (x, y) position in tile coordinates.
        """
        return self._interpolate_cell_position(
            from_x=self.player_render_from_x,
            from_y=self.player_render_from_y,
            to_x=self.runtime.player_x,
            to_y=self.runtime.player_y,
            started_ms=self.player_render_started_ms,
            cooldown_ms=self.move_cooldown_ms,
            now_ms=now_ms,
        )

    def _get_ghost_render_position(
        self,
        ghost: GhostRuntime,
        now_ms: int,
    ) -> tuple[float, float]:
        """Return interpolated ghost position in tile coordinates."""
        return self._interpolate_cell_position(
            from_x=ghost.render_from_x,
            from_y=ghost.render_from_y,
            to_x=ghost.x,
            to_y=ghost.y,
            started_ms=ghost.render_started_ms,
            cooldown_ms=self.ghost_move_cooldown_ms,
            now_ms=now_ms,
        )

    def _interpolate_cell_position(
        self,
        from_x: int,
        from_y: int,
        to_x: int,
        to_y: int,
        started_ms: int,
        cooldown_ms: int,
        now_ms: int,
    ) -> tuple[float, float]:
        """Return interpolated tile coordinates for smooth rendering."""
        if cooldown_ms <= 0:
            return float(to_x), float(to_y)

        elapsed = max(0, now_ms - started_ms)
        progress = min(1.0, elapsed / cooldown_ms)
        return (
            from_x + (to_x - from_x) * progress,
            from_y + (to_y - from_y) * progress,
        )
