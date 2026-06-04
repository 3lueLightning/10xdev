"""FastAPI application entrypoint.

Request/response bodies are pydantic models — the same pattern used for config
and prompts, so validation is consistent across the codebase. Run locally with:
    uv run uvicorn {{pkg}}.api.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from {{pkg}}.config import get_settings
from {{pkg}}.logging import logger

app = FastAPI(title="{{project_name}}")


class HealthResponse(BaseModel):
    status: str
    model: str


@app.get("/health")
def health() -> HealthResponse:
    settings = get_settings()
    logger.info("health check")
    return HealthResponse(status="ok", model=settings.llm_model)
