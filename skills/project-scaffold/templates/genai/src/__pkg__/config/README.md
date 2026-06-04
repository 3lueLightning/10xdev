# `config/` — the single source of configuration

`settings.py` defines one `Settings` object (pydantic-settings) and a cached
`get_settings()`. **This is the only module in the project allowed to read the
environment** (`.env`, `os.environ`). Everything else imports `get_settings()`.

Three buckets, kept separate:
- **Secrets** → `.env` (gitignored), declared as `Settings` fields. Never logged.
- **Configuration** (tunable per environment) → `Settings` fields with defaults.
- **True constants** (never change) → the `constants/` package, not here.
