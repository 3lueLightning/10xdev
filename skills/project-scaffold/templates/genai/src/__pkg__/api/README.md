# `api/` — HTTP layer

The FastAPI app and its routers. Request/response shapes are pydantic models.
Keep this layer thin: parse/validate input, call `core/`, shape the response.
Run locally with `uvicorn {{pkg}}.api.main:app --reload`.
