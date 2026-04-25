"""Adapter around external mazegenerator package."""

from __future__ import annotations

from dataclasses import dataclass
import multiprocessing as mp
from queue import Empty

from mazegenerator.mazegenerator import MazeGenerator


NORTH = 1
EAST = 2
SOUTH = 4
WEST = 8


@dataclass(frozen=True)
class MazeLevel:
    """Generated maze data consumed by the game."""

    grid: list[list[int]]
    entry: tuple[int, int]
    exit: tuple[int, int]
    shortest_path: str | bool


def can_move(cell_code: int, dx: int, dy: int) -> bool:
    """Return True when movement from a cell to the neighbor is allowed."""
    if dx == 1 and dy == 0:
        return (cell_code & EAST) == 0
    if dx == -1 and dy == 0:
        return (cell_code & WEST) == 0
    if dx == 0 and dy == 1:
        return (cell_code & SOUTH) == 0
    if dx == 0 and dy == -1:
        return (cell_code & NORTH) == 0
    return False


class MazeProvider:
    """Create game levels through the external wheel package."""

    def __init__(self, timeout_seconds: float = 2.5) -> None:
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _worker(
        width: int,
        height: int,
        perfect: bool,
        seed: int,
        output_queue: mp.Queue[tuple[str, MazeLevel | str]],
    ) -> None:
        """Generate a maze in a child process and return data through queue."""
        try:
            generator = MazeGenerator(
                size=(width, height),
                perfect=perfect,
                seed=seed,
            )
            output_queue.put(
                (
                    "ok",
                    MazeLevel(
                        grid=generator.maze,
                        entry=generator.maze_entry,
                        exit=generator.maze_exit,
                        shortest_path=generator.shortest_path,
                    ),
                )
            )
        except Exception as exc:  # noqa: BLE001
            output_queue.put(("error", str(exc)))

    def _fallback_level(self, width: int, height: int, seed: int) -> MazeLevel:
        """Generate a constrained fallback maze if normal generation stalls."""
        safe_width = min(max(5, width), 15)
        safe_height = min(max(5, height), 15)
        safe_seed = seed if seed > 0 else 42
        generator = MazeGenerator(
            size=(safe_width, safe_height),
            perfect=True,
            seed=safe_seed,
        )
        return MazeLevel(
            grid=generator.maze,
            entry=generator.maze_entry,
            exit=generator.maze_exit,
            shortest_path=generator.shortest_path,
        )

    def generate(
        self,
        width: int,
        height: int,
        perfect: bool,
        seed: int,
    ) -> MazeLevel:
        """Generate a new level and return normalized data."""
        if width < 5 or height < 5:
            raise ValueError("Maze size must be at least 5x5")

        output_queue: mp.Queue[tuple[str, MazeLevel | str]] = mp.Queue()
        process = mp.Process(
            target=self._worker,
            args=(width, height, perfect, seed, output_queue),
            daemon=True,
        )
        process.start()
        process.join(self.timeout_seconds)

        if process.is_alive():
            process.terminate()
            process.join()
            return self._fallback_level(width, height, seed)

        try:
            status, payload = output_queue.get_nowait()
        except Empty:
            return self._fallback_level(width, height, seed)

        if status == "ok" and isinstance(payload, MazeLevel):
            return payload
        return self._fallback_level(width, height, seed)
