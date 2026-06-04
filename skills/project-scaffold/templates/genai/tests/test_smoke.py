"""Smoke tests — prove the package imports and config loads."""

from {{pkg}} import __version__
from {{pkg}}.config import get_settings


def test_version_present() -> None:
    assert __version__


def test_settings_load() -> None:
    settings = get_settings()
    assert 0.0 <= settings.llm_temperature <= 2.0
