# `llm/` — model client wrappers

Thin wrappers around the LLM provider SDK(s). Centralising calls here means
retries, timeouts, token accounting, and prompt-manager fetch-with-fallback live
in one place, and `core/` depends on a small interface rather than a vendor SDK.
