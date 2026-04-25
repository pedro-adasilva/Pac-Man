"""Basic tests for config loading."""

from __future__ import annotations

from pathlib import Path

from pacman.settings import GameSettings, load_settings


def test_load_settings_from_config() -> None:
    """Config should be parseable into GameSettings."""
    settings = load_settings(Path("config.json"))
    assert isinstance(settings, GameSettings)
    assert len(settings.levels) > 0
    assert settings.levels[0].width > 0
    assert settings.levels[0].height > 0
    assert settings.lives > 0
