#!/usr/bin/env python3
"""Entry point for Pac-Man game.

Usage:
    python3 pac-man.py <config.json>
"""

from __future__ import annotations

from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from pacman.game import Game
from pacman.settings import load_settings


def main() -> int:
    """Run game startup and handle fatal errors gracefully."""
    if len(sys.argv) != 2:
        print(
            "Usage: python3 pac-man.py <config.json>",
            file=sys.stderr,
        )
        return 1

    config_path = Path(sys.argv[1])

    try:
        settings = load_settings(config_path)
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
