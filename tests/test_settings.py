"""Basic tests for config loading."""

from __future__ import annotations

from pathlib import Path

from pacman.settings import GameSettings, load_settings


def test_load_settings_from_default_config() -> None:
    """Default config should be parseable into GameSettings."""
    settings = load_settings(Path("config/game_config.jsonc"))
    assert isinstance(settings, GameSettings)
    assert settings.maze_width > 0
    assert settings.maze_height > 0
