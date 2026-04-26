"""Minimal playable Pac-Man-like loop with states."""

from __future__ import annotations

from collections import deque
import random
from dataclasses import dataclass
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


@dataclass
class GameRuntime:
    """Mutable runtime data."""

    state: str
    player_x: int
    player_y: int
    score: int


class Game:
    """Main game object handling UI states and play loop."""

    def __init__(self, settings: GameSettings) -> None:
        self.settings = settings
        self.provider = MazeProvider()
        self.current_level_idx = 0
        self.lives = settings.lives
        self.score = 0
        self.level: MazeLevel | None = None
        self.error_message = ""
        self.generation_thread: Thread | None = None
        self.last_move_ms = 0
        self.move_cooldown_ms = 180
        self.move_dx = 0
        self.move_dy = 0
        self.desired_dx = 0
        self.desired_dy = 0
        self.spawn_x = 0
        self.spawn_y = 0
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
            screen = pygame.display.set_mode(
                (self.settings.window_width, self.settings.window_height)
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
            self.runtime.score = 0
            self.move_dx = 0
            self.move_dy = 0
            self.desired_dx = 0
            self.desired_dy = 0
            self._initialize_collectibles(level)
            self.runtime.state = "playing"
        finally:
            self.generation_thread = None

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
            self.runtime.state = "game_over"

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
        if now_ms - self.last_move_ms < self.move_cooldown_ms:
            return

        if self._can_move(self.desired_dx, self.desired_dy):
            self.move_dx = self.desired_dx
            self.move_dy = self.desired_dy

        if self.move_dx == 0 and self.move_dy == 0:
            return

        if self._try_move(self.move_dx, self.move_dy):
            self.last_move_ms = now_ms
            return

        self.move_dx = 0
        self.move_dy = 0

    def _handle_playing_key(self, key: int) -> None:
        """Handle in-game controls and update player position."""
        if not self.level:
            return
        if self.settings.cheat_mode and key == pygame.K_n:
            self.pacgums.clear()
            self.super_pacgums.clear()
            self.runtime.score += 500
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
        font = pygame.font.SysFont("monospace", 34)
        text = font.render("PAC-MAN PYTHON", True, (255, 217, 61))
        sub1 = pygame.font.SysFont("monospace", 20).render(
            "Press ENTER to start", True, (220, 220, 230)
        )
        sub2 = pygame.font.SysFont("monospace", 18).render(
            "Press Q to quit", True, (200, 200, 200)
        )
        screen.blit(text, (40, 60))
        screen.blit(sub1, (40, 120))
        screen.blit(sub2, (40, 160))

    def _draw_loading(self, screen: pygame.Surface) -> None:
        """Draw loading view while a maze is being generated."""
        dots = "." * ((pygame.time.get_ticks() // 300) % 4)
        title = pygame.font.SysFont("monospace", 30).render(
            f"Generating maze{dots}", True, (255, 217, 61)
        )
        sub = pygame.font.SysFont("monospace", 18).render(
            "Press Q to quit", True, (200, 200, 200)
        )
        screen.blit(title, (40, 60))
        screen.blit(sub, (40, 110))

    def _draw_game_over(self, screen: pygame.Surface) -> None:
        """Draw game-over view."""
        if not self.level:
            return
        font = pygame.font.SysFont("monospace", 34)
        title = font.render("LEVEL COMPLETE", True, (132, 255, 158))
        score = pygame.font.SysFont("monospace", 22).render(
            f"Score: {self.runtime.score}", True, (230, 230, 245)
        )
        sub = pygame.font.SysFont("monospace", 20).render(
            "Press ENTER to return to menu", True, (220, 220, 230)
        )
        screen.blit(title, (40, 60))
        screen.blit(score, (40, 120))
        screen.blit(sub, (40, 160))

    def _draw_error(self, screen: pygame.Surface) -> None:
        """Draw maze generation error view."""
        title = pygame.font.SysFont("monospace", 30).render(
            "Maze generation error", True, (255, 140, 140)
        )
        message = pygame.font.SysFont("monospace", 18).render(
            self.error_message, True, (235, 235, 245)
        )
        sub = pygame.font.SysFont("monospace", 18).render(
            "Press Q or ESC to quit", True, (200, 200, 200)
        )
        screen.blit(title, (40, 60))
        screen.blit(message, (40, 110))
        screen.blit(sub, (40, 150))

    def _draw_playing(self, screen: pygame.Surface) -> None:
        """Draw maze, player and HUD."""
        if not self.level:
            return
        cell_size = 24
        offset_x = 32
        offset_y = 32
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
                        screen, wall_color, rect.topleft, rect.topright, 2
                    )
                if code & 2:
                    pygame.draw.line(
                        screen,
                        wall_color,
                        rect.topright,
                        rect.bottomright,
                        2,
                    )
                if code & 4:
                    pygame.draw.line(
                        screen,
                        wall_color,
                        rect.bottomleft,
                        rect.bottomright,
                        2,
                    )
                if code & 8:
                    pygame.draw.line(
                        screen,
                        wall_color,
                        rect.topleft,
                        rect.bottomleft,
                        2,
                    )

        for x, y in self.pacgums:
            center = (
                offset_x + x * cell_size + cell_size // 2,
                offset_y + y * cell_size + cell_size // 2,
            )
            pygame.draw.circle(screen, (255, 235, 180), center, 3)

        for x, y in self.super_pacgums:
            center = (
                offset_x + x * cell_size + cell_size // 2,
                offset_y + y * cell_size + cell_size // 2,
            )
            pygame.draw.circle(screen, (255, 184, 92), center, 6)

        player_rect = pygame.Rect(
            offset_x + self.runtime.player_x * cell_size + 4,
            offset_y + self.runtime.player_y * cell_size + 4,
            cell_size - 8,
            cell_size - 8,
        )
        pygame.draw.ellipse(screen, (255, 217, 61), player_rect)

        hud = pygame.font.SysFont("monospace", 20).render(
            f"Score: {self.runtime.score}", True, (230, 230, 245)
        )
        remaining = len(self.pacgums) + len(self.super_pacgums)
        left = pygame.font.SysFont("monospace", 20).render(
            f"Pacgums: {remaining}", True, (230, 230, 245)
        )
        screen.blit(hud, (32, self.settings.window_height - 36))
        screen.blit(left, (260, self.settings.window_height - 36))
