"""Shared pytest fixtures."""

import pytest

from {{pkg}}.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(log_level="DEBUG")
