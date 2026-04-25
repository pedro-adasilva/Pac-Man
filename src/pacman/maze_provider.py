"""Adapter around external mazegenerator package."""

from __future__ import annotations

import multiprocessing as mp
from dataclasses import dataclass
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

    def __init__(self, timeout_seconds: float = 5.0) -> None:
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _worker(
        width: int,
        height: int,
        seed: int,
        output_queue: mp.Queue[tuple[str, MazeLevel | str]],
    ) -> None:
        """Generate a maze in a child process and return data through queue."""
        try:
            generator = MazeGenerator(
                size=(width, height),
                perfect=False,
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
        except KeyboardInterrupt:
            return
        except Exception as exc:  # noqa: BLE001
            output_queue.put(("error", str(exc)))

    def generate(
        self,
        width: int,
        height: int,
        seed: int,
    ) -> MazeLevel:
        """Generate a new level and return normalized data."""
        if width < 5 or height < 5:
            raise ValueError("Maze size must be at least 5x5")

        output_queue: mp.Queue[tuple[str, MazeLevel | str]] = mp.Queue()
        process = mp.Process(
            target=self._worker,
            args=(width, height, seed, output_queue),
            daemon=True,
        )
        process.start()

        try:
            process.join(self.timeout_seconds)
        except KeyboardInterrupt:
            if process.is_alive():
                process.terminate()
                process.join()
            raise

        if process.is_alive():
            process.terminate()
            process.join()
            raise TimeoutError(
                "Maze generation timed out after "
                f"{self.timeout_seconds:.1f} seconds"
            )

        try:
            status, payload = output_queue.get_nowait()
        except Empty:
            raise RuntimeError("Maze generator did not return a result")

        if status == "ok" and isinstance(payload, MazeLevel):
            return payload
        raise RuntimeError(f"Maze generator failed: {payload}")
