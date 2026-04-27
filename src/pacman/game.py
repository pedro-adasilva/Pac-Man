"""Minimal playable Pac-Man-like loop with states."""

from __future__ import annotations

from collections import deque
import random
from dataclasses import dataclass, field
from threading import Thread

import pygame

from pacman.maze_provider import MazeLevel, MazeProvider, can_move
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


@dataclass
class GameRuntime:
    """Mutable runtime data."""

    state: str
    player_x: int
    player_y: int
    score: int


@dataclass
class GhostRuntime:
    """Mutable runtime data for one ghost."""

    x: int
    y: int
    spawn_x: int
    spawn_y: int
    dir_x: int
    dir_y: int
    color: tuple[int, int, int]
    recent_cells: deque[tuple[int, int]] = field(
        default_factory=lambda: deque(maxlen=6)
    )
    stuck_ticks: int = 0


class Game:
    """Main game object handling UI states and play loop."""

    def __init__(self, settings: GameSettings) -> None:
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
            self.move_dx = 0
            self.move_dy = 0
            self.desired_dx = 0
            self.desired_dy = 0
            self._initialize_collectibles(level)
            self._initialize_ghosts(level)
            self.runtime.state = "playing"
        finally:
            self.generation_thread = None

    def _walkable_cells(self, level: MazeLevel) -> set[tuple[int, int]]:
        """Return all non-blocked cells of the maze."""
        return {
            (x, y)
            for y, row in enumerate(level.grid)
            for x, code in enumerate(row)
            if code != BLOCKED_CELL_CODE
        }

    def _nearest_walkable(
        self,
        candidates: set[tuple[int, int]],
        target_x: int,
        target_y: int,
    ) -> tuple[int, int] | None:
        """Find the walkable cell nearest to a target position."""
        if not candidates:
            return None
        return min(
            candidates,
            key=lambda pos: (
                abs(pos[0] - target_x) + abs(pos[1] - target_y),
                pos[1],
                pos[0],
            ),
        )

    def _initialize_ghosts(self, level: MazeLevel) -> None:
        """Spawn four ghosts near maze corners."""
        width = len(level.grid[0])
        height = len(level.grid)
        corners = [
            (0, 0),
            (width - 1, 0),
            (0, height - 1),
            (width - 1, height - 1),
        ]
        colors = [
            (255, 90, 90),
            (90, 220, 255),
            (255, 164, 94),
            (255, 118, 235),
        ]
        available = self._walkable_cells(level)
        available.discard((self.spawn_x, self.spawn_y))
        ghosts: list[GhostRuntime] = []

        for idx, (cx, cy) in enumerate(corners):
            chosen = self._nearest_walkable(available, cx, cy)
            if chosen is None:
                continue
            available.discard(chosen)
            ghosts.append(
                GhostRuntime(
                    x=chosen[0],
                    y=chosen[1],
                    spawn_x=chosen[0],
                    spawn_y=chosen[1],
                    dir_x=0,
                    dir_y=0,
                    color=colors[idx],
                    recent_cells=deque([chosen], maxlen=6),
                )
            )

        self.ghosts = ghosts
        self.last_ghost_move_ms = 0

    def _initialize_collectibles(self, level: MazeLevel) -> None:
        """Create pacgums and super-pacgums for the current level."""
        width = len(level.grid[0])
        height = len(level.grid)
        all_cells = {(x, y) for y in range(height) for x in range(width)}
        blocked = {
            (x, y)
            for y, row in enumerate(level.grid)
            for x, code in enumerate(row)
            if code == BLOCKED_CELL_CODE
        }
        blocked.add((self.spawn_x, self.spawn_y))

        self.super_pacgums = self._compute_super_pacgum_positions(
            width=width,
            height=height,
            available=all_cells - blocked,
        )

        regular_candidates = list(
            all_cells - blocked - self.super_pacgums
        )
        random.shuffle(regular_candidates)
        target = min(self.settings.pacgum, len(regular_candidates))
        self.pacgums = set(regular_candidates[:target])

    def _find_spawn_position(self, level: MazeLevel) -> tuple[int, int]:
        """Find the walkable cell closest to the maze center."""
        width = len(level.grid[0])
        height = len(level.grid)
        center_x = width // 2
        center_y = height // 2
        candidates: list[tuple[int, int]] = []

        for y, row in enumerate(level.grid):
            for x, code in enumerate(row):
                if code == BLOCKED_CELL_CODE:
                    continue
                candidates.append((x, y))

        if not candidates:
            return level.entry

        return min(
            candidates,
            key=lambda pos: (
                abs(pos[0] - center_x) + abs(pos[1] - center_y),
                pos[1],
                pos[0],
            ),
        )

    def _compute_super_pacgum_positions(
        self,
        width: int,
        height: int,
        available: set[tuple[int, int]],
    ) -> set[tuple[int, int]]:
        """Place up to 4 super-pacgums near maze corners."""
        if not available:
            return set()

        corners = [
            (0, 0),
            (width - 1, 0),
            (0, height - 1),
            (width - 1, height - 1),
        ]
        placed: set[tuple[int, int]] = set()
        remaining = set(available)

        for cx, cy in corners:
            if not remaining:
                break
            chosen = min(
                remaining,
                key=lambda pos: (
                    abs(pos[0] - cx) + abs(pos[1] - cy),
                    pos[1],
                    pos[0],
                ),
            )
            placed.add(chosen)
            remaining.remove(chosen)

        return placed

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
        if not self.pacgums and not self.super_pacgums:
            if self.current_level_idx + 1 < len(self.settings.levels):
                self.current_level_idx += 1
                self._start_level_generation()
                return
            self.game_over_reason = "win"
            self.runtime.state = "game_over"

    def _start_new_game(self) -> None:
        """Reset progression data and start from the first level."""
        self.current_level_idx = 0
        self.lives = self.settings.lives
        self.runtime.score = 0
        self.move_dx = 0
        self.move_dy = 0
        self.desired_dx = 0
        self.desired_dy = 0
        self.game_over_reason = "win"

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

    def _check_ghost_collision(self) -> bool:
        """Return True if player collides with any ghost."""
        for ghost in self.ghosts:
            if (
                ghost.x == self.runtime.player_x
                and ghost.y == self.runtime.player_y
            ):
                self._on_player_caught()
                return True
        return False

    def _ghost_available_moves(
        self,
        ghost: GhostRuntime,
    ) -> list[tuple[int, int]]:
        """Collect legal one-cell moves for a ghost."""
        if not self.level:
            return []

        moves: list[tuple[int, int]] = []
        cell_code = self.level.grid[ghost.y][ghost.x]
        for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            if not can_move(cell_code, dx, dy):
                continue
            nx = ghost.x + dx
            ny = ghost.y + dy
            if (
                0 <= nx < len(self.level.grid[0])
                and 0 <= ny < len(self.level.grid)
                and self.level.grid[ny][nx] != BLOCKED_CELL_CODE
            ):
                moves.append((dx, dy))
        return moves

    def _move_ghosts(self, player_prev: tuple[int, int]) -> None:
        """Move ghosts with a simple chase behavior."""
        if not self.level or not self.ghosts:
            return

        player_now = (self.runtime.player_x, self.runtime.player_y)
        update_order = list(range(len(self.ghosts)))
        if update_order:
            shift = self.ghost_update_index % len(update_order)
            update_order = update_order[shift:] + update_order[:shift]
            self.ghost_update_index += 1

        occupied_now = {(ghost.x, ghost.y) for ghost in self.ghosts}
        reserved_next: set[tuple[int, int]] = set()
        for ghost_idx in update_order:
            ghost = self.ghosts[ghost_idx]
            ghost_prev = (ghost.x, ghost.y)
            occupied_now.discard(ghost_prev)
            moves = self._ghost_available_moves(ghost)
            if not moves:
                ghost.stuck_ticks += 1
                reserved_next.add(ghost_prev)
                occupied_now.add(ghost_prev)
                continue

            reverse = (-ghost.dir_x, -ghost.dir_y)
            non_reverse = [move for move in moves if move != reverse]
            candidates = non_reverse if non_reverse else moves

            available = [
                move
                for move in candidates
                if (
                    (ghost.x + move[0], ghost.y + move[1])
                    not in occupied_now
                    and (ghost.x + move[0], ghost.y + move[1])
                    not in reserved_next
                )
            ]
            if available:
                candidates = available
            else:
                ghost.stuck_ticks += 1
                reserved_next.add(ghost_prev)
                occupied_now.add(ghost_prev)
                continue

            # If a ghost stays blocked for several ticks, allow extra
            # variability to break small loops and local deadlocks.
            if ghost.stuck_ticks >= 3:
                random.shuffle(candidates)
                chosen = candidates[0]
            else:
                target_x = self.runtime.player_x
                target_y = self.runtime.player_y
                random.shuffle(candidates)

                def score_move(move: tuple[int, int]) -> float:
                    nx = ghost.x + move[0]
                    ny = ghost.y + move[1]
                    distance = abs(nx - target_x) + abs(ny - target_y)
                    revisit_penalty = 0.0
                    if (nx, ny) in ghost.recent_cells:
                        revisit_penalty = 1.0
                    return distance + revisit_penalty

                chosen = min(candidates, key=score_move)

            ghost.dir_x, ghost.dir_y = chosen
            ghost.x += chosen[0]
            ghost.y += chosen[1]
            ghost.stuck_ticks = 0
            ghost.recent_cells.append((ghost.x, ghost.y))
            occupied_now.add((ghost.x, ghost.y))
            reserved_next.add((ghost.x, ghost.y))

            # Detect both overlap and same-tick cross-over collisions.
            if (ghost.x, ghost.y) == player_now or (
                ghost_prev == player_now
                and (ghost.x, ghost.y) == player_prev
            ):
                self._on_player_caught()
                return

        self._check_ghost_collision()

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
        """Process user input based on current state."""
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
        player_prev = (self.runtime.player_x, self.runtime.player_y)
        if now_ms - self.last_move_ms >= self.move_cooldown_ms:
            if self._can_move(self.desired_dx, self.desired_dy):
                self.move_dx = self.desired_dx
                self.move_dy = self.desired_dy

            if self.move_dx != 0 or self.move_dy != 0:
                if self._try_move(self.move_dx, self.move_dy):
                    self.last_move_ms = now_ms
                else:
                    self.move_dx = 0
                    self.move_dy = 0

        if now_ms - self.last_ghost_move_ms >= self.ghost_move_cooldown_ms:
            self._move_ghosts(player_prev)
            self.last_ghost_move_ms = now_ms

    def _handle_playing_key(self, key: int) -> None:
        """Handle in-game controls and update player position."""
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
        """Return True when current direction can move one cell."""
        if not self.level:
            return False
        if dx == 0 and dy == 0:
            return False

        x = self.runtime.player_x
        y = self.runtime.player_y
        cell_code = self.level.grid[y][x]
        return can_move(cell_code, dx, dy)

    def _try_move(self, dx: int, dy: int) -> bool:
        """Try to move player by one cell and update score/state."""
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
            self.runtime.player_x = new_x
            self.runtime.player_y = new_y
        else:
            return False

        self._consume_collectibles_at_player()
        self._check_ghost_collision()
        self._check_level_completion()
        return True

    def _reset_game(self) -> None:
        """Return to menu without regenerating level."""
        self.runtime.state = "menu"
        self.lives = self.settings.lives
        self.score = 0

    def _draw(self, screen: pygame.Surface) -> None:
        """Draw current UI state."""
        screen.fill((15, 18, 33))
        if self.runtime.state == "menu":
            self._draw_menu(screen)
            return
        if self.runtime.state == "loading":
            self._draw_loading(screen)
            return
        if self.runtime.state == "game_over":
            self._draw_game_over(screen)
            return
        if self.runtime.state == "error":
            self._draw_error(screen)
            return
        self._draw_playing(screen)

    def _draw_menu(self, screen: pygame.Surface) -> None:
        """Draw menu view."""
        scale = self._ui_scale()
        x = max(24, int(40 * scale))
        y_title = max(40, int(60 * scale))
        y_sub1 = y_title + max(44, int(60 * scale))
        y_sub2 = y_sub1 + max(28, int(40 * scale))

        font = pygame.font.SysFont("monospace", max(24, int(34 * scale)))
        text = font.render("PAC-MAN PYTHON", True, (255, 217, 61))
        sub1 = pygame.font.SysFont(
            "monospace", max(16, int(20 * scale))
        ).render(
            "Press ENTER to start", True, (220, 220, 230)
        )
        sub2 = pygame.font.SysFont(
            "monospace", max(14, int(18 * scale))
        ).render(
            "Press Q to quit", True, (200, 200, 200)
        )
        screen.blit(text, (x, y_title))
        screen.blit(sub1, (x, y_sub1))
        screen.blit(sub2, (x, y_sub2))

    def _draw_loading(self, screen: pygame.Surface) -> None:
        """Draw loading view while a maze is being generated."""
        scale = self._ui_scale()
        x = max(24, int(40 * scale))
        y_title = max(40, int(60 * scale))
        y_sub = y_title + max(36, int(50 * scale))

        dots = "." * ((pygame.time.get_ticks() // 300) % 4)
        title = pygame.font.SysFont(
            "monospace", max(22, int(30 * scale))
        ).render(
            f"Generating maze{dots}", True, (255, 217, 61)
        )
        sub = pygame.font.SysFont(
            "monospace", max(14, int(18 * scale))
        ).render(
            "Press Q to quit", True, (200, 200, 200)
        )
        screen.blit(title, (x, y_title))
        screen.blit(sub, (x, y_sub))

    def _draw_game_over(self, screen: pygame.Surface) -> None:
        """Draw game-over view."""
        scale = self._ui_scale()
        x = max(24, int(40 * scale))
        y_title = max(40, int(60 * scale))
        y_score = y_title + max(44, int(60 * scale))
        y_sub = y_score + max(32, int(44 * scale))

        font = pygame.font.SysFont("monospace", max(24, int(34 * scale)))
        if self.game_over_reason == "lose":
            title_text = "GAME OVER"
            title_color = (255, 140, 140)
        else:
            title_text = "VICTORY"
            title_color = (132, 255, 158)

        title = font.render(title_text, True, title_color)
        score = pygame.font.SysFont(
            "monospace", max(16, int(22 * scale))
        ).render(
            f"Score: {self.runtime.score}", True, (230, 230, 245)
        )
        sub = pygame.font.SysFont(
            "monospace", max(16, int(20 * scale))
        ).render(
            "Press ENTER to return to menu", True, (220, 220, 230)
        )
        screen.blit(title, (x, y_title))
        screen.blit(score, (x, y_score))
        screen.blit(sub, (x, y_sub))

    def _draw_error(self, screen: pygame.Surface) -> None:
        """Draw maze generation error view."""
        scale = self._ui_scale()
        x = max(24, int(40 * scale))
        y_title = max(40, int(60 * scale))
        y_message = y_title + max(36, int(50 * scale))
        y_sub = y_message + max(30, int(40 * scale))

        title = pygame.font.SysFont(
            "monospace", max(22, int(30 * scale))
        ).render(
            "Maze generation error", True, (255, 140, 140)
        )
        message = pygame.font.SysFont(
            "monospace", max(14, int(18 * scale))
        ).render(
            self.error_message, True, (235, 235, 245)
        )
        sub = pygame.font.SysFont(
            "monospace", max(14, int(18 * scale))
        ).render(
            "Press Q or ESC to quit", True, (200, 200, 200)
        )
        screen.blit(title, (x, y_title))
        screen.blit(message, (x, y_message))
        screen.blit(sub, (x, y_sub))

    def _draw_playing(self, screen: pygame.Surface) -> None:
        """Draw maze, player and HUD."""
        if not self.level:
            return
        scale = self._ui_scale()
        rows = len(self.level.grid)
        cols = len(self.level.grid[0])
        margin = max(16, int(24 * scale))
        hud_height = max(44, int(56 * scale))
        available_w = self.window_width - (margin * 2)
        available_h = self.window_height - (margin * 2) - hud_height

        if available_w <= 0 or available_h <= 0:
            return

        cell_size = min(available_w // cols, available_h // rows)
        cell_size = max(8, min(64, cell_size))
        maze_width = cols * cell_size
        maze_height = rows * cell_size
        offset_x = (self.window_width - maze_width) // 2
        offset_y = max(
            margin,
            (self.window_height - hud_height - maze_height) // 2,
        )

        wall_width = max(2, min(6, cell_size // 8))
        pacgum_radius = max(2, min(6, cell_size // 8))
        super_pacgum_radius = max(4, min(12, cell_size // 4))
        player_padding = max(2, min(10, cell_size // 6))
        wall_color = (93, 173, 226)
        path_color = (24, 29, 52)

        for y, row in enumerate(self.level.grid):
            for x, code in enumerate(row):
                rect = pygame.Rect(
                    offset_x + x * cell_size,
                    offset_y + y * cell_size,
                    cell_size,
                    cell_size,
                )
                pygame.draw.rect(screen, path_color, rect)
                if code & 1:
                    pygame.draw.line(
                        screen,
                        wall_color,
                        rect.topleft,
                        rect.topright,
                        wall_width,
                    )
                if code & 2:
                    pygame.draw.line(
                        screen,
                        wall_color,
                        rect.topright,
                        rect.bottomright,
                        wall_width,
                    )
                if code & 4:
                    pygame.draw.line(
                        screen,
                        wall_color,
                        rect.bottomleft,
                        rect.bottomright,
                        wall_width,
                    )
                if code & 8:
                    pygame.draw.line(
                        screen,
                        wall_color,
                        rect.topleft,
                        rect.bottomleft,
                        wall_width,
                    )

        for x, y in self.pacgums:
            center = (
                offset_x + x * cell_size + cell_size // 2,
                offset_y + y * cell_size + cell_size // 2,
            )
            pygame.draw.circle(
                screen,
                (255, 235, 180),
                center,
                pacgum_radius,
            )

        for x, y in self.super_pacgums:
            center = (
                offset_x + x * cell_size + cell_size // 2,
                offset_y + y * cell_size + cell_size // 2,
            )
            pygame.draw.circle(
                screen,
                (255, 184, 92),
                center,
                super_pacgum_radius,
            )

        player_rect = pygame.Rect(
            offset_x + self.runtime.player_x * cell_size + player_padding,
            offset_y + self.runtime.player_y * cell_size + player_padding,
            cell_size - (player_padding * 2),
            cell_size - (player_padding * 2),
        )
        pygame.draw.ellipse(screen, (255, 217, 61), player_rect)

        ghost_radius = max(4, min(14, (cell_size - player_padding) // 2))
        for ghost in self.ghosts:
            center = (
                offset_x + ghost.x * cell_size + cell_size // 2,
                offset_y + ghost.y * cell_size + cell_size // 2,
            )
            pygame.draw.circle(screen, ghost.color, center, ghost_radius)

        hud_font_size = max(14, int(20 * scale))
        hud = pygame.font.SysFont("monospace", hud_font_size).render(
            f"Score: {self.runtime.score}", True, (230, 230, 245)
        )
        lives = pygame.font.SysFont("monospace", hud_font_size).render(
            f"Lives: {self.lives}", True, (230, 230, 245)
        )
        level_idx = pygame.font.SysFont("monospace", hud_font_size).render(
            f"Level: {self.current_level_idx + 1}", True, (230, 230, 245)
        )
        remaining = len(self.pacgums) + len(self.super_pacgums)
        left = pygame.font.SysFont("monospace", hud_font_size).render(
            f"Pacgums: {remaining}", True, (230, 230, 245)
        )
        hud_y = self.window_height - hud_height + max(8, int(12 * scale))
        screen.blit(hud, (margin, hud_y))
        screen.blit(lives, (margin + max(150, int(220 * scale)), hud_y))
        screen.blit(level_idx, (margin + max(310, int(450 * scale)), hud_y))
        screen.blit(left, (margin + max(470, int(680 * scale)), hud_y))
