"""Settings loader for game configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import sys

try:
    import commentjson
except Exception:  # pragma: no cover - fallback when dependency is missing
    commentjson = None


@dataclass(frozen=True)
class LevelConfig:
    """Configuration for one level."""

    width: int
    height: int
    seed: int
    num_ghosts: int


@dataclass(frozen=True)
class GameSettings:
    """Static game settings loaded from config."""

    window_width: int
    window_height: int
    fps: int
    levels: list[LevelConfig]
    lives: int
    pacgum: int
    points_per_pacgum: int
    points_per_super_pacgum: int
    points_per_ghost: int
    level_max_time: int
    cheat_mode: bool
    highscores_file: str


def _load_raw_json(config_path: Path) -> dict[str, Any]:
    """Load JSON data from a file that may include comments."""
    try:
        with config_path.open("r", encoding="utf-8") as fobj:
            if commentjson is not None:
                return dict(commentjson.load(fobj))
            return dict(json.load(fobj))
    except FileNotFoundError as exc:
        raise ValueError(
            f"Configuration file not found: {config_path}"
        ) from exc
    except Exception as exc:
        raise ValueError(f"Invalid configuration file: {config_path}") from exc


def _clamp(value: int, min_val: int, max_val: int) -> int:
    """Clamp value between min and max, logging warning."""
    if value < min_val or value > max_val:
        print(
            f"WARNING: Value {value} out of range [{min_val}, {max_val}], "
            f"clamping to {max(min_val, min(max_val, value))}",
            file=sys.stderr,
        )
    return max(min_val, min(max_val, value))


def _load_level_config(level_data: dict[str, Any]) -> LevelConfig:
    """Parse a single level config, clamping to safe defaults."""
    if not isinstance(level_data, dict):
        level_data = {}

    try:
        width = int(level_data.get("width", 21))
        height = int(level_data.get("height", 21))
        seed = int(level_data.get("seed", 42))
        num_ghosts = int(level_data.get("num_ghosts", 1))
    except (TypeError, ValueError):
        width, height, seed, num_ghosts = 21, 21, 42, 1

    width = _clamp(width, 5, 100)
    height = _clamp(height, 5, 100)
    num_ghosts = _clamp(num_ghosts, 0, 10)

    return LevelConfig(
        width=width,
        height=height,
        seed=seed,
        num_ghosts=num_ghosts,
    )


def load_settings(config_path: Path) -> GameSettings:
    """Load and validate game settings from disk."""
    try:
        data = _load_raw_json(config_path)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise

    try:
        window_width = int(data.get("window_width", 960))
        window_height = int(data.get("window_height", 720))
        fps = int(data.get("fps", 60))
        lives = int(data.get("lives", 3))
        pacgum = int(data.get("pacgum", 42))
        points_per_pacgum = int(data.get("points_per_pacgum", 10))
        points_per_super_pacgum = int(
            data.get("points_per_super_pacgum", 50)
        )
        points_per_ghost = int(data.get("points_per_ghost", 200))
        level_max_time = int(data.get("level_max_time", 90))
    except (TypeError, ValueError):
        (
            window_width,
            window_height,
            fps,
            lives,
            pacgum,
            points_per_pacgum,
            points_per_super_pacgum,
            points_per_ghost,
            level_max_time,
        ) = (960, 720, 60, 3, 42, 10, 50, 200, 90)

    window_width = _clamp(window_width, 480, 2560)
    window_height = _clamp(window_height, 360, 1440)
    fps = _clamp(fps, 10, 240)
    lives = _clamp(lives, 1, 10)
    pacgum = _clamp(pacgum, 0, 1000)
    points_per_pacgum = _clamp(points_per_pacgum, 0, 1000)
    points_per_super_pacgum = _clamp(points_per_super_pacgum, 0, 5000)
    points_per_ghost = _clamp(points_per_ghost, 0, 10000)
    level_max_time = _clamp(level_max_time, 10, 600)

    levels_data = data.get("levels", [{"width": 21, "height": 21}])
    if not isinstance(levels_data, list) or not levels_data:
        levels_data = [{"width": 21, "height": 21}]

    levels = [_load_level_config(level) for level in levels_data]

    cheat_mode = bool(data.get("cheat_mode", False))
    highscores_file = str(
        data.get("highscores_file", "data/highscores.json")
    )

    return GameSettings(
        window_width=window_width,
        window_height=window_height,
        fps=fps,
        levels=levels,
        lives=lives,
        pacgum=pacgum,
        points_per_pacgum=points_per_pacgum,
        points_per_super_pacgum=points_per_super_pacgum,
        points_per_ghost=points_per_ghost,
        level_max_time=level_max_time,
        cheat_mode=cheat_mode,
        highscores_file=highscores_file,
    )
