"""Runtime models for Pac-Man game state."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


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
    render_from_x: int = 0
    render_from_y: int = 0
    render_started_ms: int = 0
    eaten_until_ms: int = 0
