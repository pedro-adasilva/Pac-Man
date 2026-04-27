"""Level setup and progression helpers for Pac-Man."""

from __future__ import annotations

from typing import TYPE_CHECKING
import random

from pacman.maze_provider import MazeLevel

if TYPE_CHECKING:
    from pacman.game import Game


def walkable_cells(level: MazeLevel) -> set[tuple[int, int]]:
    """Return all non-blocked cells of the maze."""
    return {
        (x, y)
        for y, row in enumerate(level.grid)
        for x, code in enumerate(row)
        if code != 15
    }


def nearest_walkable(
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


def find_spawn_position(level: MazeLevel) -> tuple[int, int]:
    """Find the walkable cell closest to the maze center."""
    width = len(level.grid[0])
    height = len(level.grid)
    center_x = width // 2
    center_y = height // 2
    candidates: list[tuple[int, int]] = []

    for y, row in enumerate(level.grid):
        for x, code in enumerate(row):
            if code == 15:
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


def compute_super_pacgum_positions(
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


def initialize_collectibles(game: "Game", level: MazeLevel) -> None:
    """Create pacgums and super-pacgums for the current level."""
    width = len(level.grid[0])
    height = len(level.grid)
    all_cells = {(x, y) for y in range(height) for x in range(width)}
    blocked = {
        (x, y)
        for y, row in enumerate(level.grid)
        for x, code in enumerate(row)
        if code == 15
    }
    blocked.add((game.spawn_x, game.spawn_y))

    game.super_pacgums = compute_super_pacgum_positions(
        width=width,
        height=height,
        available=all_cells - blocked,
    )

    regular_candidates = list(all_cells - blocked - game.super_pacgums)
    random.shuffle(regular_candidates)
    target = min(game.settings.pacgum, len(regular_candidates))
    game.pacgums = set(regular_candidates[:target])


def start_new_game(game: "Game") -> None:
    """Reset progression data and start from the first level."""
    game.current_level_idx = 0
    game.lives = game.settings.lives
    game.runtime.score = 0
    game.move_dx = 0
    game.move_dy = 0
    game.desired_dx = 0
    game.desired_dy = 0
    game.game_over_reason = "win"


def check_level_completion(game: "Game") -> None:
    """Advance to the next level or end the game when cleared."""
    if not game.pacgums and not game.super_pacgums:
        if game.current_level_idx + 1 < len(game.settings.levels):
            game.current_level_idx += 1
            game._start_level_generation()
            return
        game.game_over_reason = "win"
        game.runtime.state = "game_over"
