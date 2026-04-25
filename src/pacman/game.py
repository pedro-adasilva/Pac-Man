"""Minimal playable Pac-Man-like loop with states."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from pacman.maze_provider import MazeLevel, MazeProvider, can_move
from pacman.settings import GameSettings


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
        self.level: MazeLevel = self.provider.generate(
            width=settings.maze_width,
            height=settings.maze_height,
            perfect=settings.maze_perfect,
            seed=settings.maze_seed,
        )
        self.runtime = GameRuntime(
            state="menu",
            player_x=self.level.entry[0],
            player_y=self.level.entry[1],
            score=0,
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
                if (
                    self.runtime.state == "menu"
                    and event.key == pygame.K_RETURN
                ):
                    self.runtime.state = "playing"
                elif (
                    self.runtime.state == "game_over"
                    and event.key == pygame.K_RETURN
                ):
                    self._reset_game()
                elif self.runtime.state == "playing":
                    self._handle_playing_key(event.key)
        return True

    def _handle_playing_key(self, key: int) -> None:
        """Handle in-game controls and update player position."""
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
        """Reset game runtime and regenerate level."""
        self.level = self.provider.generate(
            width=self.settings.maze_width,
            height=self.settings.maze_height,
            perfect=self.settings.maze_perfect,
            seed=self.settings.maze_seed,
        )
        self.runtime.state = "menu"
        self.runtime.player_x, self.runtime.player_y = self.level.entry
        self.runtime.score = 0

    def _draw(self, screen: pygame.Surface) -> None:
        """Draw current UI state."""
        screen.fill((15, 18, 33))
        if self.runtime.state == "menu":
            self._draw_menu(screen)
            return
        if self.runtime.state == "game_over":
            self._draw_game_over(screen)
            return
        self._draw_playing(screen)

    def _draw_menu(self, screen: pygame.Surface) -> None:
        """Draw menu view."""
        font = pygame.font.SysFont("monospace", 34)
        text = font.render("PAC-MAN PYTHON", True, (255, 217, 61))
        sub = pygame.font.SysFont("monospace", 20).render(
            "Press ENTER to start", True, (220, 220, 230)
        )
        screen.blit(text, (40, 60))
        screen.blit(sub, (40, 120))

    def _draw_game_over(self, screen: pygame.Surface) -> None:
        """Draw game-over view."""
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

    def _draw_playing(self, screen: pygame.Surface) -> None:
        """Draw maze, player and HUD."""
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
