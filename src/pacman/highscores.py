"""Simple JSON persistent highscore management."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import re


@dataclass(frozen=True)
class HighscoreEntry:
    """One entry in the highscore table."""

    name: str
    score: int


def validate_player_name(name: str) -> str:
    """Validate and normalize a player name.

    Max 10 chars, alphanumeric and spaces only.
    """
    name = str(name).strip()[:10]
    if not re.match(r"^[a-zA-Z0-9 ]*$", name):
        name = re.sub(r"[^a-zA-Z0-9 ]", "", name)[:10]
    return name or "PLAYER"


def load_highscores(file_path: Path) -> list[HighscoreEntry]:
    """Load highscores from disk; return an empty list if file is missing."""
    try:
        with file_path.open("r", encoding="utf-8") as fobj:
            data = json.load(fobj)
        if not isinstance(data, list):
            return []
        result: list[HighscoreEntry] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "AAA"))[:16]
            try:
                score = int(item.get("score", 0))
            except (TypeError, ValueError):
                continue
            result.append(HighscoreEntry(name=name, score=score))
        return sorted(result, key=lambda item: item.score, reverse=True)
    except FileNotFoundError:
        return []
    except Exception:
        return []


def save_highscores(
    file_path: Path,
    entries: list[HighscoreEntry],
    limit: int = 10,
) -> None:
    """Persist sorted highscores to disk."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    sorted_entries = sorted(
        entries,
        key=lambda item: item.score,
        reverse=True,
    )[:limit]
    with file_path.open("w", encoding="utf-8") as fobj:
        json.dump([asdict(item) for item in sorted_entries], fobj, indent=2)


def register_score(
    file_path: Path,
    player_name: str,
    score: int,
    limit: int = 10,
) -> list[HighscoreEntry]:
    """Add a score and save the updated highscore table."""
    player_name = validate_player_name(player_name)
    entries = load_highscores(file_path)
    entries.append(
        HighscoreEntry(name=player_name, score=max(score, 0))
    )
    save_highscores(file_path, entries, limit=limit)
    return load_highscores(file_path)
