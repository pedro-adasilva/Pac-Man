"""Minimal playable Pac-Man-like loop with states."""

from __future__ import annotations

import random
from dataclasses import dataclass

import pygame

from pacman.maze_provider import MazeLevel, MazeProvider, can_move
from pacman.settings import GameSettings


ENTER_KEYS = {pygame.K_RETURN, pygame.K_KP_ENTER}
SAFE_RANDOM_SEEDS = (1, 2, 8, 10, 11)


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
        self.runtime = GameRuntime(
            state="menu",
            player_x=0,
            player_y=0,
            score=0,
        )

    def _load_current_level(self) -> MazeLevel:
        """Load the current level from settings."""
        if self.current_level_idx >= len(self.settings.levels):
            self.current_level_idx = 0
        level_config = self.settings.levels[self.current_level_idx]
        seed = level_config.seed
        if seed == 0:
            seed = random.choice(SAFE_RANDOM_SEEDS)
        return self.provider.generate(
            width=level_config.width,
            height=level_config.height,
            seed=seed,
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
                self._draw(screen)
                pygame.display.flip()
                clock.tick(self.settings.fps)
        finally:
            pygame.quit()

    def _process_events(self) -> bool:
        """Process user input based on current state."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if self.runtime.state == "menu":
                    if event.key in ENTER_KEYS:
                        try:
                            level = self._load_current_level()
                        except Exception as exc:  # noqa: BLE001
                            self.level = None
                            self.error_message = (
                                f"Error al generar el laberinto: {exc}"
                            )
                            self.runtime.state = "error"
                        else:
                            self.level = level
                            self.error_message = ""
                            self.runtime.player_x = level.entry[0]
                            self.runtime.player_y = level.entry[1]
                            self.runtime.score = 0
                            self.runtime.state = "playing"
                    elif event.key == pygame.K_q:
                        return False
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

    def _handle_playing_key(self, key: int) -> None:
        """Handle in-game controls and update player position."""
        if not self.level:
            return
        if self.settings.cheat_mode and key == pygame.K_n:
            self.runtime.player_x, self.runtime.player_y = self.level.exit
            self.runtime.score += 500
            self.runtime.state = "game_over"
            return

        move_map = {
            pygame.K_UP: (0, -1),
            pygame.K_w: (0, -1),
            pygame.K_RIGHT: (1, 0),
            pygame.K_d: (1, 0),
            pygame.K_DOWN: (0, 1),
            pygame.K_s: (0, 1),
            pygame.K_LEFT: (-1, 0),
            pygame.K_a: (-1, 0),
        }
        if key not in move_map:
            return

        dx, dy = move_map[key]
        x = self.runtime.player_x
        y = self.runtime.player_y
        cell_code = self.level.grid[y][x]
        if not can_move(cell_code, dx, dy):
            return

        new_x = x + dx
        new_y = y + dy
        if (
            0 <= new_x < len(self.level.grid[0])
            and 0 <= new_y < len(self.level.grid)
        ):
            self.runtime.player_x = new_x
            self.runtime.player_y = new_y
            self.runtime.score += 10

        if (self.runtime.player_x, self.runtime.player_y) == self.level.exit:
            self.runtime.score += 1000
            self.runtime.state = "game_over"

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

        exit_x, exit_y = self.level.exit
        exit_rect = pygame.Rect(
            offset_x + exit_x * cell_size + 5,
            offset_y + exit_y * cell_size + 5,
            cell_size - 10,
            cell_size - 10,
        )
        pygame.draw.rect(screen, (255, 140, 66), exit_rect)

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
        screen.blit(hud, (32, self.settings.window_height - 36))
