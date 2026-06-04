"""Single source of truth for configuration and secrets.

This is the ONLY module permitted to read the environment / .env file. Every
other module reads configuration through `get_settings()`. This keeps config in
one typed, validated place instead of scattered os.getenv() calls.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- secrets (populate via .env; never hard-code) ---
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    # --- LLM configuration ---
    llm_model: str = "gpt-4o"
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=1000, gt=0)

    # --- logging ---
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["console", "json"] = "console"

    # --- prompt observability (wire later; defaults off) ---
    langfuse_enabled: bool = False
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached singleton. Import this everywhere; never instantiate Settings directly."""
    return Settings()
