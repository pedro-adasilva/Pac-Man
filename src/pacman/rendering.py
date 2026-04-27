"""Rendering helpers for Pac-Man game views."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from pacman.game import Game


def draw_game(game: "Game", screen: pygame.Surface) -> None:
    """Draw current UI state based on game runtime state."""
    screen.fill((15, 18, 33))
    if game.runtime.state == "menu":
        _draw_menu(game, screen)
        return
    if game.runtime.state == "loading":
        _draw_loading(game, screen)
        return
    if game.runtime.state == "game_over":
        _draw_game_over(game, screen)
        return
    if game.runtime.state == "error":
        _draw_error(game, screen)
        return
    _draw_playing(game, screen)


def _draw_menu(game: "Game", screen: pygame.Surface) -> None:
    """Draw menu view."""
    scale = game._ui_scale()
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


def _draw_loading(game: "Game", screen: pygame.Surface) -> None:
    """Draw loading view while a maze is being generated."""
    scale = game._ui_scale()
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


def _draw_game_over(game: "Game", screen: pygame.Surface) -> None:
    """Draw game-over view."""
    scale = game._ui_scale()
    x = max(24, int(40 * scale))
    y_title = max(40, int(60 * scale))
    y_score = y_title + max(44, int(60 * scale))
    y_sub = y_score + max(32, int(44 * scale))

    font = pygame.font.SysFont("monospace", max(24, int(34 * scale)))
    if game.game_over_reason == "lose":
        title_text = "GAME OVER"
        title_color = (255, 140, 140)
    else:
        title_text = "VICTORY"
        title_color = (132, 255, 158)

    title = font.render(title_text, True, title_color)
    score = pygame.font.SysFont(
        "monospace", max(16, int(22 * scale))
    ).render(
        f"Score: {game.runtime.score}", True, (230, 230, 245)
    )
    sub = pygame.font.SysFont(
        "monospace", max(16, int(20 * scale))
    ).render(
        "Press ENTER to return to menu", True, (220, 220, 230)
    )
    screen.blit(title, (x, y_title))
    screen.blit(score, (x, y_score))
    screen.blit(sub, (x, y_sub))


def _draw_error(game: "Game", screen: pygame.Surface) -> None:
    """Draw maze generation error view."""
    scale = game._ui_scale()
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
        game.error_message, True, (235, 235, 245)
    )
    sub = pygame.font.SysFont(
        "monospace", max(14, int(18 * scale))
    ).render(
        "Press Q or ESC to quit", True, (200, 200, 200)
    )
    screen.blit(title, (x, y_title))
    screen.blit(message, (x, y_message))
    screen.blit(sub, (x, y_sub))


def _draw_playing(game: "Game", screen: pygame.Surface) -> None:
    """Draw maze, player and HUD."""
    if not game.level:
        return
    scale = game._ui_scale()
    rows = len(game.level.grid)
    cols = len(game.level.grid[0])
    margin = max(16, int(24 * scale))
    hud_height = max(44, int(56 * scale))
    available_w = game.window_width - (margin * 2)
    available_h = game.window_height - (margin * 2) - hud_height

    if available_w <= 0 or available_h <= 0:
        return

    cell_size = min(available_w // cols, available_h // rows)
    cell_size = max(8, min(64, cell_size))
    maze_width = cols * cell_size
    maze_height = rows * cell_size
    offset_x = (game.window_width - maze_width) // 2
    offset_y = max(
        margin,
        (game.window_height - hud_height - maze_height) // 2,
    )

    wall_width = max(2, min(6, cell_size // 8))
    pacgum_radius = max(2, min(6, cell_size // 8))
    super_pacgum_radius = max(4, min(12, cell_size // 4))
    player_padding = max(2, min(10, cell_size // 6))
    wall_color = (93, 173, 226)
    path_color = (24, 29, 52)

    for y, row in enumerate(game.level.grid):
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

    for x, y in game.pacgums:
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

    for x, y in game.super_pacgums:
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
        0,
        0,
        cell_size - (player_padding * 2),
        cell_size - (player_padding * 2),
    )
    now_ms = pygame.time.get_ticks()
    player_x, player_y = game._get_player_render_position(now_ms)
    player_rect.x = int(offset_x + player_x * cell_size + player_padding)
    player_rect.y = int(offset_y + player_y * cell_size + player_padding)
    pygame.draw.ellipse(screen, (255, 217, 61), player_rect)

    ghost_radius = max(4, min(14, (cell_size - player_padding) // 2))
    for ghost in game.ghosts:
        ghost_x, ghost_y = game._get_ghost_render_position(
            ghost,
            now_ms,
        )
        center = (
            int(offset_x + ghost_x * cell_size + cell_size // 2),
            int(offset_y + ghost_y * cell_size + cell_size // 2),
        )
        pygame.draw.circle(screen, ghost.color, center, ghost_radius)

    hud_font_size = max(14, int(20 * scale))
    hud = pygame.font.SysFont("monospace", hud_font_size).render(
        f"Score: {game.runtime.score}", True, (230, 230, 245)
    )
    lives = pygame.font.SysFont("monospace", hud_font_size).render(
        f"Lives: {game.lives}", True, (230, 230, 245)
    )
    level_idx = pygame.font.SysFont("monospace", hud_font_size).render(
        f"Level: {game.current_level_idx + 1}", True, (230, 230, 245)
    )
    remaining = len(game.pacgums) + len(game.super_pacgums)
    left = pygame.font.SysFont("monospace", hud_font_size).render(
        f"Pacgums: {remaining}", True, (230, 230, 245)
    )
    hud_y = game.window_height - hud_height + max(8, int(12 * scale))
    screen.blit(hud, (margin, hud_y))
    screen.blit(lives, (margin + max(150, int(220 * scale)), hud_y))
    screen.blit(level_idx, (margin + max(310, int(450 * scale)), hud_y))
    screen.blit(left, (margin + max(470, int(680 * scale)), hud_y))
