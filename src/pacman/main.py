"""Entry point for Pac-Man project."""

from __future__ import annotations

from pathlib import Path
import sys

from pacman.game import Game
from pacman.settings import load_settings


def main() -> int:
    """Run game startup and handle fatal errors gracefully."""
    try:
        settings = load_settings(Path("config/game_config.jsonc"))
        game = Game(settings)
        game.run()
        return 0
    except KeyboardInterrupt:
        print("Game interrupted by user.", file=sys.stderr)
        return 130
    except Exception as exc:  # noqa: BLE001
        print(f"Fatal error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
