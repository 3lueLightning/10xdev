# 10xdev

A Claude Code plugin that scaffolds Python GenAI projects and keeps them clean —
built so a junior engineer gets production-grade structure on day one and the
conventions explain themselves.

It bundles four composable skills:

- **project-scaffold** — interviews you, then generates a correct `src`-layout
  project in a single pass (package, `Settings`, logging, prompt loader, tests,
  optional FastAPI). One approval, no per-file prompts.
- **quality-gates** — installs the whole apparatus behind one `task ci-check`:
  ruff (lint + format), type checking, bandit / pip-audit / supply-chain scan,
  deptry, size & complexity limits, a token-aware naming check, secret scanning,
  and a two-stage hook system (fast commits, strict pushes) plus multi-forge CI.
- **ai-project-guidance** — generates `AGENTS.md` + `CLAUDE.md` grounded in
  *Clean Code*, including instructions for the assistant to coach the developer
  when a gate fires rather than silently working around it.
- **git-setup** — main/dev branch model and branch protection (when you have
  admin), always with a manual fallback doc.

## Install

```
/plugin marketplace add <your-github-username>/10xdev
/plugin install 10xdev@10xdev
```

Then just ask, e.g. *"scaffold a new GenAI project"* or *"add quality gates to
this repo"* — the skills trigger from their descriptions.

## Stop the permission prompts

The skills do their file work through single scripts (`render.py`, `apply.py`),
so the host agent asks for approval **once** per skill instead of per file. To
remove even that, copy the relevant lines from [`settings.example.json`](settings.example.json)
into `~/.claude/settings.json` (user-wide) or `.claude/settings.json` (per
project). Review anytime with `/permissions`.

## Develop / test

```
pip install pytest pyyaml tomlkit
python -m pytest tests/ -q
```

`tests/test_naming.py` covers the naming rule (banned tokens anywhere in
identifiers; string keys/columns exempt); `tests/test_render.py` renders projects
for several answer sets and asserts the structure. CI (`.github/workflows/ci.yml`)
also scaffolds a project, applies the gates, and runs the full gate end-to-end.

## What the generated project looks like

`src`-layout, package under `src/<name>/`, prompts packaged inside it, a README
in every folder, an `AGENTS.md` with the rules, and a `.project-conventions.yaml`
that is the single contract every gate reads. See `skills/project-scaffold/` for
the template and `HANDOFF.md` for the full design rationale.
