# `{{pkg}}` — the importable package

This is the code that ships. Import it **by name** from anywhere
(`from {{pkg}}.core import ...`) — never `from src...` and never with a
`sys.path` hack; `uv sync` installed it editable for you.

Subpackages: `config/` (settings + secrets, the only place env is read),
`constants/` (true constants), `core/` (business logic), `llm/` (model client
wrappers), `prompts/` (prompt YAML + loader), `api/` (HTTP layer, if enabled).
