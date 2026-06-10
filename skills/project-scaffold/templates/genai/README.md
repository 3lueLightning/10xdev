# {{project_name}}

A Python GenAI project. This README is the **human** orientation — read it first
and you'll know what's already set up, how the project is organised, and the
conventions you're expected to follow. The full rules with rationale live in
[`AGENTS.md`](AGENTS.md) (written for AI assistants, but a good read for people
too); the exact thresholds live in `.project-conventions.yaml`.

## What's already set up for you

You don't need to configure any of this — it came with the project:

- **A clean package layout** (src-layout) with a place for everything (see below).
- **One command for quality**, `task ci-check`: formatting, linting, type
  checking, security and dependency scanning, and tests. The pre-push git hook
  and CI both run exactly this, so "passes locally" means "passes in CI".
- **Fast, forgiving commits / strict pushes**: committing runs quick checks so
  you commit often; pushing runs the full gate so nothing unreviewed escapes.
- **Settings, logging, prompt loading, tests, and (optionally) a FastAPI app**
  already wired up, so you start writing features, not plumbing.
- **`uv`** for dependency and environment management (`task setup` installs
  everything).

## The packages at a glance

Every folder has its own `README.md` with the details; the one-liners:

- `src/{{pkg}}/` — the importable package (the code that ships). The repeated
  name is intentional — `src/README.md` explains why.
  - `config/` — the single `Settings` object; the **only** place secrets/env are read.
  - `constants/` — values that never change.
  - `core/` — business logic.
  - `llm/` — model client wrappers.
  - `prompts/` — versioned prompt YAML + loader (packaged, container-safe).
  - `api/` — FastAPI app (only if you enabled an API).
- `tests/` — pytest suite (relaxed rules).
- `notebooks/` — experimentation sandbox (relaxed rules; see `00_getting_started`).
- `scripts/` — your own throwaway scripts (relaxed rules; never put scripts at
  the repo root — the gate rejects them).
- `ci_pipeline/` — the quality gate's own check scripts (owned by tooling,
  don't edit by hand).
- `docs/` — MkDocs documentation source (`task docs-serve` to preview).

## Conventions in brief

The project enforces a handful of habits (all checked automatically — see the
next section). In plain terms:

- **Name things for what they are.** Clear, intention-revealing names; no vague
  `data`/`helper`/`process` on their own, and no `new`/`old`/`tmp`/`temp` inside
  a variable name (`pending_users`, not `users_new`). Data values are exempt — a
  dict key or column `"new_car"` is fine, the variable isn't.
- **snake_case** for functions and variables, **PascalCase** for classes,
  **UPPER_CASE** for constants.
- **Small, single-purpose functions** that read top-to-bottom like prose; the
  gate pushes back on functions that get too long or too tangled.
- **Secrets and config live only in `config/settings.py`** — never `os.getenv`
  scattered through the code, never a secret in source.
- **Type your function signatures.** Imports at the top of the file.

The deeper *why* behind each — and the Clean Code principles the project follows
— is in [`AGENTS.md`](AGENTS.md).

## How this project keeps itself honest

`task ci-check` (run by the pre-push hook and CI) bundles: **ruff** (lint +
format), **type checking** (signatures enforced on changed code), the **naming**
and **no-mutable-module-state** and **config-hygiene** checks, **size &
complexity** limits, **bandit** + **pip-audit** + a supply-chain scan for new
dependencies, **deptry** (imports vs declared deps), and **pytest** with
coverage. Run any piece alone: `task lint`, `task typecheck`, `task security`,
`task sizes`, `task test`.

If a check blocks you, it's a safety net, not a wall — the message says what and
why, and your AI assistant is instructed (via `AGENTS.md`) to explain it and help
you fix it properly rather than work around it.

## Quick start

```bash
task setup        # install deps + git hooks (run once after cloning)
task ci-check     # run the full quality gate
```

No `task` yet? `uv tool install go-task-bin` (or read `Taskfile.yml` for the
underlying commands).

## Common tasks

| command | what |
|---|---|
| `task format` | auto-format + auto-fix (includes import ordering) |
| `task ci-check` | full gate (lint, spelling, types, security, audit, deps, tests) |
| `task spell` | spell-check; allow terms via `.codespell-ignore.txt` |
| `task docs-serve` | preview the MkDocs documentation locally |
| `task profile-quick -- uv run python script.py` | CPU flamegraph + LLM-readable summary |
| `task audit-package -- <pkg>` | supply-chain scan before adding a dependency |
