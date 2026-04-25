"""Settings loader for game configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json

try:
    import commentjson
except Exception:  # pragma: no cover - fallback when dependency is missing
    commentjson = None


@dataclass(frozen=True)
class GameSettings:
    """Static game settings loaded from config."""

    window_width: int
    window_height: int
    fps: int
    maze_width: int
    maze_height: int
    maze_perfect: bool
    maze_seed: int
    cheat_mode: bool
    highscores_file: str


DEFAULT_CONFIG_PATH = Path("config/game_config.jsonc")


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


def load_settings(config_path: Path = DEFAULT_CONFIG_PATH) -> GameSettings:
    """Load and validate game settings from disk."""
    data = _load_raw_json(config_path)

    try:
        return GameSettings(
            window_width=int(data.get("window_width", 960)),
            window_height=int(data.get("window_height", 720)),
            fps=int(data.get("fps", 60)),
            maze_width=int(data.get("maze_width", 21)),
            maze_height=int(data.get("maze_height", 21)),
            maze_perfect=bool(data.get("maze_perfect", False)),
            maze_seed=int(data.get("maze_seed", 0)),
            cheat_mode=bool(data.get("cheat_mode", False)),
            highscores_file=str(
                data.get("highscores_file", "data/highscores.json")
            ),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("Configuration values have invalid types") from exc
