"""Ghost movement and collision helpers for Pac-Man."""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING
import math
import random

from pacman.maze_provider import MazeLevel, can_move
from pacman.models import GhostRuntime

if TYPE_CHECKING:
    from pacman.game import Game

BLOCKED_CELL_CODE = 15
COLLISION_DISTANCE_TILES = 0.42
GHOST_COLORS = [
    (255, 90, 90),
    (90, 220, 255),
    (255, 164, 94),
    (255, 118, 235),
]


def initialize_ghosts(game: "Game", level: MazeLevel) -> None:
    """Spawn four ghosts near maze corners."""
    width = len(level.grid[0])
    height = len(level.grid)
    corners = [
        (0, 0),
        (width - 1, 0),
        (0, height - 1),
        (width - 1, height - 1),
    ]
    available = _walkable_cells(level)
    available.discard((game.spawn_x, game.spawn_y))
    ghosts: list[GhostRuntime] = []

    for idx, (cx, cy) in enumerate(corners):
        chosen = _nearest_walkable(available, cx, cy)
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
                color=GHOST_COLORS[idx],
                recent_cells=deque([chosen], maxlen=6),
                render_from_x=chosen[0],
                render_from_y=chosen[1],
                render_started_ms=0,
            )
        )

    game.ghosts = ghosts
    game.last_ghost_move_ms = 0


def _walkable_cells(level: MazeLevel) -> set[tuple[int, int]]:
    """Return all non-blocked cells of the maze."""
    return {
        (x, y)
        for y, row in enumerate(level.grid)
        for x, code in enumerate(row)
        if code != BLOCKED_CELL_CODE
    }


def _nearest_walkable(
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


def _ghost_available_moves(
    game: "Game",
    ghost: GhostRuntime,
) -> list[tuple[int, int]]:
    """Collect legal one-cell moves for a ghost."""
    if not game.level:
        return []

    moves: list[tuple[int, int]] = []
    cell_code = game.level.grid[ghost.y][ghost.x]
    for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
        if not can_move(cell_code, dx, dy):
            continue
        nx = ghost.x + dx
        ny = ghost.y + dy
        if (
            0 <= nx < len(game.level.grid[0])
            and 0 <= ny < len(game.level.grid)
            and game.level.grid[ny][nx] != BLOCKED_CELL_CODE
        ):
            moves.append((dx, dy))
    return moves


def check_ghost_collision(game: "Game", now_ms: int) -> bool:
    """Return True if a ghost visually overlaps the player."""
    player_x, player_y = game._get_player_render_position(now_ms)
    for ghost in game.ghosts:
        ghost_x, ghost_y = game._get_ghost_render_position(ghost, now_ms)
        distance = math.hypot(ghost_x - player_x, ghost_y - player_y)
        if distance <= COLLISION_DISTANCE_TILES:
            game._on_player_caught()
            return True
    return False


def move_ghosts(game: "Game", now_ms: int) -> None:
    """Move ghosts with a simple chase behavior."""
    if not game.level or not game.ghosts:
        return

    update_order = list(range(len(game.ghosts)))
    if update_order:
        shift = game.ghost_update_index % len(update_order)
        update_order = update_order[shift:] + update_order[:shift]
        game.ghost_update_index += 1

    occupied_now = {(ghost.x, ghost.y) for ghost in game.ghosts}
    reserved_next: set[tuple[int, int]] = set()
    for ghost_idx in update_order:
        ghost = game.ghosts[ghost_idx]
        ghost_prev = (ghost.x, ghost.y)
        occupied_now.discard(ghost_prev)
        moves = _ghost_available_moves(game, ghost)
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
            fallback = [
                move
                for move in moves
                if (
                    (ghost.x + move[0], ghost.y + move[1])
                    not in occupied_now
                    and (ghost.x + move[0], ghost.y + move[1])
                    not in reserved_next
                )
            ]
            if fallback:
                candidates = fallback
            else:
                ghost.stuck_ticks += 1
                reserved_next.add(ghost_prev)
                occupied_now.add(ghost_prev)
                continue

        if ghost.stuck_ticks >= 3:
            random.shuffle(candidates)
            chosen = candidates[0]
        else:
            target_x = game.runtime.player_x
            target_y = game.runtime.player_y
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
        ghost.render_from_x = ghost.x
        ghost.render_from_y = ghost.y
        ghost.render_started_ms = now_ms
        ghost.x += chosen[0]
        ghost.y += chosen[1]
        ghost.stuck_ticks = 0
        ghost.recent_cells.append((ghost.x, ghost.y))
        occupied_now.add((ghost.x, ghost.y))
        reserved_next.add((ghost.x, ghost.y))
