# AGENTS.md — guidance for AI coding assistants

You are working in a Python **GenAI** project that enforces strict conventions.
Read this file fully before generating code. Most rules here are enforced by
pre-commit/pre-push hooks and CI (`task ci-check`), so violating them fails the
build — but the real reason for each is below, not just "the linter says so".

Project: **{{project_name}}** · Package: **{{pkg}}** · Python **{{python_version}}**

## Project context

{{domain_summary}}

**Team conventions:** {{team_norms}}

---

## Guiding philosophy — write Clean Code

Follow Robert C. Martin's *Clean Code* principles. They are the *why* behind
every rule and gate below; the gates are just the mechanical backstop.

- **Intention-revealing names.** A name should answer why it exists, what it
  does, and how it's used. If a name needs a comment to explain it, rename it.
  Prefer `elapsed_days` to `d`, `pending_invoices` to `list2`.
- **Functions do one thing**, at a single level of abstraction, and are small.
  A function that needs "and" to describe it should be split. Few arguments
  (zero–three); a long argument list usually wants an object.
- **Code should read like well-written prose** — top to bottom, like a
  newspaper: the high-level story first, details further down. The reader should
  almost never have to jump around to understand a function.
- **Don't repeat yourself.** Duplicated logic is a single concept waiting for a
  name and a home.
- **Leave it cleaner than you found it** (the Boy-Scout rule). Small, safe
  improvements to names and structure as you pass through.
- Comments explain *why*, never *what* the code already says. The best comment
  is a good name that made the comment unnecessary.

---

## Project structure

```
src/{{pkg}}/
  config/      # ONE Settings object (pydantic-settings). Nothing else config-y.
  constants/   # True constants only — domain facts that never change.
  prompts/     # Prompt loaders + versioned prompt YAML, packaged (importlib.resources).
               # The ONLY prompts location — never a root-level prompts/.
  llm/         # LLM client wrappers.
  api/         # FastAPI app + routers + request/response models (if applicable).
  core/        # Business logic.
  logging.py   # The project logger. Import `logger` from here, nowhere else.
tests/          # Mirrors src/ layout (relaxed rules).
notebooks/      # Experimentation sandbox (relaxed rules — see bottom).
scripts/        # YOUR throwaway scripts (relaxed rules) — never the repo root.
ci_pipeline/    # The quality gate's own check scripts (owned by quality-gates).
docs/           # MkDocs documentation source (`task docs-serve` to preview).
```

Import by **package name**, never by folder: `from {{pkg}}.core import extract`,
never `from src...` and never `sys.path.insert(...)`. The project is installed
editable by `uv sync`, so the package resolves everywhere, including notebooks.

**No script files at the repository root** — the gate rejects them. A quick
experiment goes in `scripts/` or `notebooks/`; shipping code goes in `src/{{pkg}}/`.

---

## Typing

- Every function **must type its arguments and its return value**. This is
  enforced on changed code from day one. `def run(items: list[str]) -> int:`
- Use a **pydantic `BaseModel`** for any function taking more than ~2 related
  parameters, or any config-shaped input. Never pass `dict[str, Any]` around for
  structured data — you lose type checking, autocomplete, and validation, and
  the next reader (human or AI) has to guess the keys.
- Deeper typing (locals) is encouraged but advisory for now.

Why pydantic for parameters: a `dict` config is untyped, undocumented, and
silently accepts typos. A model is self-documenting, validates on construction
(`temperature: float = Field(ge=0, le=2)` rejects bad values with a clear
error), refactors safely (rename a field, the IDE updates call sites), and is
the same object FastAPI uses for request bodies — so the pattern compounds.

---

## Configuration, secrets, and constants — the THREE-BUCKET RULE

Conflating these is the root of config sprawl. Route every value to its bucket:

1. **Secrets** (API keys, tokens, passwords) → `.env` (gitignored) +
   `.env.example` (committed, dummy values). Loaded **only** by
   `config/settings.py`. Never hard-code them; never log them.
2. **Configuration** (model name, temperature, batch size, endpoints, feature
   flags, log level) → fields on the `Settings` object, with typed defaults and
   pydantic `Field(...)` validators.
3. **True constants** (`SECONDS_PER_DAY = 86400`, regex patterns, enum-like
   sets) → the `constants/` package. These are genuinely fixed, so `UPPER_CASE`
   is correct here.

Hard rules the linters enforce:

- `load_dotenv()` and `os.getenv()` appear **only** in `config/settings.py`.
  Read configuration via the `Settings` object everywhere else.
- **No `global` keyword. No mutable module-level state** (a bare `CACHE = {}` at
  module scope that gets mutated). It breaks tests and concurrency — put it in
  `Settings`, inject it, or use a cached accessor (`@lru_cache get_settings()`).
- Don't invent a `FOO_CONSTANT` at the top of a feature file for something that's
  really configuration. If it changes per environment or run, it's config → `Settings`.

---

## Naming

- **English identifiers only.** Comments may be in any language (e.g. a German
  prompt string or a Portuguese note is fine); names must be English.
- **Banned when used alone**: helper, helpers, util, utils, data, manager,
  handler, process, stuff, thing, foo, bar, baz, new, old, temp, tmp. Compounds
  are fine (`user_helper`, `data_loader`) — the bare token is not.
- **Banned as a word anywhere**: `new`, `old`, `tmp`, `temp`. Wherever one of
  these appears as a token in an identifier — `new_data`, `data_new`, the
  variable `new_car`, `tmp_result`, the class `NewOrder` — it's rejected. Such a
  name records *when* or *which version*, and goes stale the instant there's a
  newer one; name the thing for what it holds (`pending_users`, not `users_new`).
  This applies to **identifiers only** — string literals, dict keys and
  dataframe columns are exempt, so `car_data["new_car"]` and `df["car_old"]` are
  perfectly fine. Matching is token-wise, so `renew`, `news`, `template` are fine.
- **No single-underscore prefix at module level** (enforced by the naming gate).
  This is a backend service — nothing imports your modules from outside, so the
  "internal use" hint of `_configure` vs `configure` distinguishes nothing.
  Name module-level functions, classes, constants, and module *files* plainly
  (`common.py`, not `_common.py`). The underscore forms that DO carry meaning
  (see https://dbader.org/blog/meaning-of-underscores-in-python) stay allowed:
  `self._attr` / `def _method` inside a class (genuinely internal to the
  object), `__dunder__` protocol names, a trailing underscore to dodge a
  keyword (`class_`), and the bare `_` throwaway variable.
- **Casing (ruff `N`):** `snake_case` for functions and variables, `PascalCase`
  for classes, `UPPER_CASE` for module-level constants.
- **Spelling is checked** (codespell, in the gate). If it flags a legitimate
  domain term or product name, add the word to `.codespell-ignore.txt` (one
  lowercase word per line) — don't disable the check.

---

## Functions and files

- Functions: aim under 50 lines; warn at 100; **hard fail at 150**.
- Files: aim under 300; warn at 450; **hard fail at 600** — split the module.
- Cyclomatic complexity ≤ 10 (the primary signal — a branchy function trips this
  before the line limit). If you're nesting three `if`s and a loop, extract.
- Prefer many small, well-named functions over one orchestrator that does
  everything. It's easier to test, profile, and reason about.

---

## Imports

- All imports at the **top of the file** (ruff PLC0415). The only exception is a
  genuinely heavy or optional module that must load lazily — and that must be
  allow-listed in `.project-conventions.yaml` `lazy_imports`, not done ad hoc.
- Use `uv add <pkg>` to add a dependency, never `uv pip install` — deptry fails
  the push if an imported package isn't declared in `pyproject.toml`.
- No unused imports, no duplicate imports, imports sorted (ruff `I`/`F401` auto-fix).
- Use **pathlib**, not `os.path` (ruff PTH).

---

## Logging

Import the logger from one place: `from {{pkg}}.logging import logger`. Never
use `print()` (ruff T20 fails it) — prints don't carry level, timestamp, or
location and vanish in production.

- **Never log secrets, credentials, tokens, or PII at any level.** Scrub
  sensitive fields before they reach a sink (loguru `patch()`/`bind()`).
- Use the levels deliberately:
  - **DEBUG** — diagnostic detail for development (payloads, intermediate values,
    flow tracing). Off in production.
  - **INFO** — normal operational milestones: "request received", "model loaded",
    "processed N items". The narrative of what the app is doing.
  - **WARNING** — unexpected but handled: a retry fired, a fallback was used, a
    deprecated path was hit, a limit is near. The app continues.
  - **ERROR** — an operation failed. Use `logger.exception()` inside `except` so
    the traceback is captured. App still runs.
  - **CRITICAL** — app-level failure, imminent crash or data-loss risk.
- Log level comes from `LOG_LEVEL` in `.env` (via `Settings`); format from
  `LOG_FORMAT` (`console` for dev, `json` for cloud — JSON to stdout lets any
  cloud platform's collector ingest logs without extra wiring).

---

## GenAI specifics

- **Prompts live as versioned YAML inside the package** at
  `src/{{pkg}}/prompts/`, loaded through a `PromptConfig` pydantic model via
  `importlib.resources` (so they ship in the wheel and resolve inside a
  container). Never inline a prompt string inside business logic — prompts change
  often and need to be versioned and reviewed separately from code.
- If prompt-management observability (Langfuse/Langsmith) is configured in
  `Settings` (`*_enabled` flag), fetch prompts from there at runtime with the
  YAML as fallback. The flag defaults off; wire it when ready without restructuring.
- LLM calls go through `src/{{pkg}}/llm/` wrappers, not scattered SDK calls, so
  retries, timeouts, and provider swaps live in one place.

---

## Async and concurrency

The team's common failure mode — get these right:

- **Never block the event loop.** No `time.sleep()` in async code — use
  `await asyncio.sleep()`. No synchronous HTTP/file calls inside `async def`.
- **Concurrent awaits** go through `asyncio.gather()`, not a sequential
  `for ... await` loop. For many LLM/API calls, gather with an
  `asyncio.Semaphore` to bound concurrency and respect rate limits.
- **CPU-bound work** (parsing, embeddings math) goes in a
  `ProcessPoolExecutor`, never a thread pool — the GIL makes threads useless for
  CPU work. Threads are for blocking I/O only.
- Use the provider's **async client** for LLM calls; don't wrap a sync client.

If you generate code that loops over large data, makes concurrent calls, or uses
async/threads, suggest the user run `task profile-quick -- <command>` and offer
to read `.profiles/latest.md` to find the hot spot.

---

## Testing

- pytest, tests under `tests/` mirroring `src/`. Every new module ships with at
  least a smoke test. Coverage is measured (reported in CI) but not gated yet.

---

## Notebooks (relaxed sandbox)

`notebooks/` is for quick experimentation and is **exempt from lint, typing,
size, and dependency checks** — don't apply the rules above there. Two things
still matter: (1) **no secrets** — gitleaks scans notebooks including output
cells, so never paste a key, and be careful what you print; (2) it is **not**
`src/` — once code works, graduate it into `src/` where the standards apply. A
`!uv pip install` in a cell for a quick experiment is fine.

---

## Never circumvent a failing gate

When a commit hook, `git push`, or CI fails, the failure output names a real
violation — **fix the violation, never the gate**. Concretely, all of these are
prohibited responses to a red gate:

- Editing `.pre-commit-config.yaml`, `Taskfile.yml`, `ruff.toml`, or
  `.project-conventions.yaml` to disable or weaken the check that fired.
- `git commit --no-verify` / `git push --no-verify`.
- Adding `# noqa` / `# type: ignore` / bumping a threshold just to get green.

Read the error, find the underlying cause, and fix that — then the push passes
because the code is right. CI runs the identical `task ci-check`, so a locally
silenced gate only moves the failure somewhere more public. If you believe a
gate itself is misconfigured, say so explicitly to the user and let them decide;
that's a team-contract change, not a quick fix.

---

## Coaching the developer (don't just comply — explain)

Many people working in this repo are learning these conventions. When something
you write (or that the user asks for) is blocked by a gate, don't silently
work around it and don't just say "the linter won't allow it." Explain the
reason, then help fix it properly. The gates exist to protect the codebase, and
part of your job is to make that legible.

- **Naming.** If the user insists on a name like `new_user`, `data_new`, or
  `process`, explain that it's blocked because it describes *when/which version*
  or is too vague to say what the value holds, which makes the code harder to
  read and trips the naming gate — then propose a concrete, intention-revealing
  alternative (`pending_user`, `parsed_invoice`, `extract_fields`). If they
  genuinely need that text as data, point out that string keys and dataframe
  columns are exempt: `record["new_user"]` is fine; the *variable* is not.
- **Complexity / length.** If a function is blocked for complexity or length,
  explain that there's a deliberate safety net against functions too tangled to
  read, test, or review — then help simplify: extract well-named helpers, use
  guard clauses to flatten nesting, split distinct responsibilities. Don't just
  bump the threshold.
- **Config / secrets.** If they try to read an env var or hardcode a secret
  outside `config/settings.py`, explain the three-bucket rule and route it
  through `Settings` instead.
- **Proactively**, even when nothing is blocked: suggest clearer names, smaller
  functions, and structure that reads like prose. Aim for code the next person
  understands with as little effort as possible.

---

## When unsure

Ask the user. Do not invent config keys, file paths, environment variable names,
or dependencies. Read `.project-conventions.yaml` for project-specific overrides
(thresholds, banned names, lazy-import allowlist).
