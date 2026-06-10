---
name: project-scaffold
description: Interview-driven scaffolding for a new Python GenAI project. Instead of dumping a giant cookie-cutter template, it asks the user targeted questions (one at a time, with a short rationale each), then generates a minimal-but-correct src-layout package with a Settings object, prompt loaders, logging, optional FastAPI, tests, a relaxed notebooks sandbox, and persists answers to .project-conventions.yaml. It then calls quality-gates (tooling, hooks, CI) and ai-project-guidance (AGENTS.md), and git-setup when the user has admin rights. Use whenever the user wants to start / scaffold / bootstrap / set up a new Python or GenAI or LLM project, create a project skeleton or structure, or "set up a new repo properly". Greenfield only.
---

# Project Scaffold (GenAI, v1)

Create a new Python GenAI project by interviewing the user, then generating a
clean structure in **one pass** and wiring up the rest of the skill suite. The
philosophy: **ask, understand, then build the minimum that's correct** — not a
200-file template nobody touches. Greenfield only.

## Workflow

### 1. Run the interview

Use `interview.yaml`.

- **Show `intro` first** so the user knows what's about to happen.
- Ask the **Phase-1 `essentials` one at a time**, in this exact presentation
  order — question first, options next, rationale last:

  ```
  **QUESTION 3/5**

  Will this expose an HTTP API or websockets?

  - rest — REST API via FastAPI (default — press Enter)
  - rest+ws — REST + WebSockets
  - none — no HTTP layer

  **Why it matters**: If yes, adds a thin FastAPI layer with pydantic
  request/response models; if no, none of that is created.
  ```

  When using a question tool (AskUserQuestion), the default goes FIRST and is
  labelled "(default)" so pressing Enter selects it.
- **Every question must be answerable by pressing Enter** (empty reply = take
  the default). The only exception is `project_name`, which is required — say so.
- For `python_version`, compute the default at ask-time:
  `uv run scripts/render.py --print-python-default` (latest stable CPython minor
  minus one — e.g. 3.13 while 3.14 is current). If that command fails, derive
  the same "penultimate minor" by other means (`uv python list`); **never**
  guess an older version. Accept any version the user types.
- Honour `skip_if` (e.g. skip the forge question when there's no git).
- **Every question also accepts free text** — "let me explain", a comment, or an
  option that isn't listed. Never force a listed choice; reflect back anything
  ambiguous in one line before moving on.
- After the essentials, **show `deferrable_intro` and the optional list** — do
  not silently stop. Let the user refine any Phase-2 items or say "just build
  it"; unanswered ones take their default and are recorded under `deferred`.

Collect all answers into an answers YAML (the keys are the question `id`s).
For non-interactive / CI runs, that same answers file can be supplied directly.

### 2. Generate the structure — one approval, no per-file prompts

Run the renderer **once**, always through `uv run` (the script carries PEP 723
inline metadata, so uv provides its dependencies — never call bare `python` and
never `pip install` anything for it):

```
uv run scripts/render.py --answers <answers>.yaml --dest <parent-dir>
```

This single command creates the whole tree, substitutes `{{pkg}}` /
`{{project_name}}` / `{{python_version}}`, writes `.python-version` and
`.project-conventions.yaml`, wires dependencies into `pyproject.toml`, and prints
a completion banner. It is one action to approve.

**Do not** generate files one at a time with individual writes, and **do not ask
the user whether to create boilerplate** (`.gitignore`, `.env.example`,
`__init__.py`, settings, etc.) — there is nothing to decide; `render.py` writes
them. Likewise **do not read, `ls`, or `grep` this skill's `templates/` files
yourself** — the renderer handles all of them; inspecting them one by one only
triggers a wall of permission prompts. If the tool environment prompts per
write, tell the user up front they can approve the run once ("allow for this
session") rather than approving each file.

`render.py` applies the conditional structure automatically:

- **`api: none`** → no `api/` package is created.
- **`prompt_management: langfuse` or `langsmith`** → no `prompts/` package or
  loader is created (prompts are managed externally); only the SDK is added.
  Otherwise prompts live as YAML **inside the package** at
  `src/<pkg>/prompts/`, loaded via `importlib.resources` (ships in the wheel,
  container-safe). There is exactly one prompts location, never a root-level one.
- LLM SDKs (`openai` / `anthropic` / `google-genai`) and, if an API was chosen,
  `fastapi` + `uvicorn`, are added to dependencies. SDKs not yet imported by the
  starter code (plus `uvicorn`, which is run via CLI) are pre-seeded into
  `[tool.deptry.per_rule_ignores] DEP002`; the quality-gates merge preserves
  this. Remove an entry once your `llm/` wrappers actually import that SDK.

Every folder ships with a `README.md` explaining what belongs in it (including
`src/README.md`, which explains the src-layout and why the package name repeats).

### 3. Call quality-gates

Invoke the `quality-gates` skill against the new project. It reads the
`.project-conventions.yaml` just written and installs uv deps, ruff, type
checking, security/audit, hooks, the Taskfile, the check scripts, and the CI
workflow for the chosen forge. (It merges its `[tool.*]` sections into
`pyproject.toml` non-destructively, preserving the dependency wiring above.)

### 4. Call ai-project-guidance

Invoke the `ai-project-guidance` skill to generate `AGENTS.md` + `CLAUDE.md`,
matching the conventions. If the user gave a `domain_summary` or `team_norms`,
those are in `.project-conventions.yaml` under `guidance:` — fold them in.

### 5. Call git-setup (only if admin)

If `git_status` is "git, I have admin" (or the user confirms they can configure
the repo), invoke the `git-setup` skill. It creates the remote repository when
none exists (via the forge CLI), pushes `main` + `dev`, applies branch
protection, and leaves the working copy **on `dev`** so nothing is ever pushed
to `main` directly. Otherwise skip it entirely — never block on remote
configuration.

### 6. Finish

Run `task setup` then `task ci-check`, and report. The render banner already
signals structural completion; summarise what was created and what was
`deferred`, and tell the user that re-running this skill (or editing
`.project-conventions.yaml` and re-running `quality-gates`) fills in deferred
choices later. If git-setup ran, remind them they are on `dev` and `main` only
moves by PR.

## Principles

- One repo per project. Local-first: never make remote/admin configuration a
  prerequisite for a working local setup.
- Minimal but correct: generate only what the answers justify; everything else is
  added later by re-running, not pre-built "just in case".
- Don't ask about things that have no real decision — just do them.
- The conventions file is the single contract every skill reads — keep it accurate.
