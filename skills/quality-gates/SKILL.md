---
name: quality-gates
description: Install and run the full Python quality apparatus on a project - uv, ruff (lint+format), mypy/pyright type checking, bandit/pip-audit/guarddog security, deptry dependency hygiene, gitleaks secret scanning, pytest with coverage, py-spy/scalene profiling, plus a two-stage pre-commit/pre-push hook system and multi-forge CI that all run one unified `task ci-check`. Use this whenever the user wants to add linting, formatting, type checking, security scanning, dependency auditing, profiling, git hooks, or CI to a Python project, asks to "set up quality gates / tooling / checks", wants commits fast but pushes strict, or wants to make a messy vibe-coded repo conform to standards. Pairs with project-scaffold (which calls this) and ai-project-guidance.
---

# Quality Gates

Install a fast-commit / strict-push quality system onto a Python project. The
guiding principle: **pre-commit is fast and forgiving so people commit often;
pre-push is the full gate so nothing unverified reaches the remote; CI runs the
exact same `task ci-check` so "passes locally" equals "passes in CI".**

This skill is idempotent — safe to run on a fresh scaffold or an existing repo.
It reads `.project-conventions.yaml` for thresholds and naming rules, falling
back to built-in defaults when that file is absent.

## Prerequisites

Two tools must exist on the machine. Check first; if missing, give install
instructions and stop rather than guessing:

- **uv** — `uv --version` (install: https://docs.astral.sh/uv/getting-started/installation/)
- **Task** — `task --version` (install: https://taskfile.dev/installation/)

Everything else is installed *by* this skill via uv, or comes through pre-commit's
managed hooks (gitleaks downloads its own binary — no manual install, which
matters for Windows developers). There are **no Go binaries to install by hand**.

## What to do

Work through these steps in order. Render `{{pkg}}` as the project's import
package name (the directory under `src/`).

### 1. Confirm project shape

The project must be a `src/`-layout package with a `pyproject.toml` containing a
`[build-system]` (so `uv sync` installs it editable and imports resolve cleanly,
including from notebooks). If there's no `pyproject.toml`, run `uv init --package`
first, or defer to the `project-scaffold` skill for greenfield work.

### 2. Apply the toolchain — one command (preferred)

Materialise everything in a single run so the host agent asks for approval once,
not per file. Always go through `uv run` (the script carries PEP 723 inline
metadata, so uv supplies its dependencies — never call bare `python`, never
`pip install` anything for it):

```
uv run scripts/apply.py --dest <project-dir> [--forge github|gitlab|bitbucket|gitea]
```

This copies the static config and the check scripts (into `ci_pipeline/` —
`scripts/` is reserved as the user's relaxed sandbox), aligns the `(conv:)`
values in `ruff.toml` from `.project-conventions.yaml` (e.g. `target-version`),
merges the `[tool.*]` sections into `pyproject.toml` (non-destructively), seeds
the `.codespell-ignore.txt` dictionary, and drops the CI workflow for the forge
(defaulting to the conventions file's `git.forge`). It does **not** install
dependencies — that's `task setup` / `uv sync`, run separately.

**Do not read, `ls`, or `grep` the files under this skill's `templates/`
yourself** — `apply.py` handles every one of them, and browsing them per file
just triggers a wall of permission prompts. The steps below document what it
does (and the manual fallback if you need to apply pieces by hand).

### 2b. (Reference / manual fallback) Copy the static config files

Copy from this skill's `templates/` into the project root (do not overwrite a
file the project already customized without showing the diff first):

- `ruff.toml` — kept separate from pyproject on purpose; it's the config tweaked
  most often. Each value is annotated `(qg-default)` or `(conv: KEY)`; for every
  `(conv:)` line, copy the value from `.project-conventions.yaml` so the config
  matches the team contract. At minimum set `target-version` to the project's
  Python (e.g. `3.13` → `py313`); also reconcile the mccabe/pylint limits and
  `banned-module-level-imports` (from `layout.lazy_imports`) if they were changed.
- `.pre-commit-config.yaml`, `.gitleaks.toml`
- `.codespell-ignore.txt` — the project's allowed-words dictionary for the spell
  check. Seed it only if absent; it is user-owned, never overwrite it.
- `.gitattributes` — LF-canonical line endings across Windows/WSL/macOS. This
  wins over each developer's `core.autocrlf`, so the repo stays consistent.
- `.editorconfig` — 4-space indent, final newline, LF.
- `.python-version` — set to the project's Python version. If the project
  already has one (project-scaffold writes it), leave it as-is.
- `Taskfile.yml` — the task runner that hooks and CI both call.

### 3. Merge the tool config into pyproject.toml

Run the merge script (it preserves existing content, comments, and any value the
project already set — only missing sections are added):

```bash
uv run python scripts/merge_pyproject.py pyproject.toml templates/pyproject.tool-sections.toml
```

If the project doesn't yet have the dev tools, **first show the user this list
and what each tool is for** (one line each — people should never discover
surprise dependencies in their lockfile), then add them as a dev dependency
group:

```bash
uv add --dev ruff mypy pyright bandit pip-audit deptry codespell \
  pytest pytest-cov pre-commit pydantic-settings tomlkit pyyaml
```

Deliberately **not** dev dependencies: `guarddog` (drags in semgrep and a large
CVE surface), `py-spy`, and `scalene` are diagnostic tools the Taskfile runs on
demand via `uvx` / `uv run --with`, so they never pollute the project's lockfile.

### 4. Copy the check scripts

Copy this skill's entire `scripts/` directory into the project's `ci_pipeline/`
folder (these are the custom checks the Taskfile invokes). `scripts/` in the
project is the **user's** relaxed sandbox for throwaway scripts — never put gate
tooling there. The checks are stdlib-only except `merge_pyproject.py` (tomlkit)
and conventions loading (pyyaml).

### 5. Add the CI workflow for the project's forge

Read `.project-conventions.yaml` `git.forge` (or ask). Copy the matching file
from `templates/ci/` to the right place and commit it:

| forge | destination |
|---|---|
| github | `.github/workflows/ci-check.yml` |
| gitlab | `.gitlab-ci.yml` |
| bitbucket | `bitbucket-pipelines.yml` |
| gitea | `.gitea/workflows/ci-check.yml` |

All four call the same `task ci-check`, so switching forges later is a one-file copy.
The workflow is named `ci-check` because that's the status check the branch
protection set up by git-setup requires.

### 6. Install and verify

```bash
task setup        # uv sync + install both hook stages
task ci-check     # run the full gate once to confirm everything is wired
```

Report the result. If `ci-check` fails on pre-existing code, that's expected on a
messy repo — see "Retrofitting" below. On a clean scaffold it should pass.

## The two hook stages (what runs when)

**pre-commit (fast, forgiving — sub-5s):** ruff syntax-only, the changed-line
signature/naming/module-state/dotenv/root-script/size checks (advisory),
codespell on changed files, standard hygiene fixers (trailing whitespace, final
newline, LF, merge-conflict markers — fixers run at commit time ONLY, so a push
is never aborted by a file modified mid-push), large-file guard (auto-skips
git-lfs files), and **gitleaks secret scanning on all files including
notebooks** — output cells can leak keys.

**pre-push = `task ci-check` (strict):** full ruff lint+format, codespell,
root-script check, type checking (signatures enforced on changed lines;
mypy/pyright advisory), bandit, pip-audit CVE scan, deptry dependency hygiene +
`uv lock --check`, pytest with coverage.

`git commit --no-verify` can bypass local hooks — that's why **CI is the real
enforcement**: a PR that fails `task ci-check` cannot merge regardless of what
happened locally. Local hooks are for fast feedback; CI is for authority.

**When a hook or `task ci-check` fails, fix the underlying violation.** Never
"fix" a failing push by editing `.pre-commit-config.yaml`, the Taskfile, or the
thresholds, and never reach for `--no-verify` — weakening the gate to get a
green light defeats its purpose and will fail in CI anyway.

## Key conventions enforced (and which tool)

- **Typed signatures** on changed code — `ci_pipeline/check_changed_signatures.py`
  (deeper typing stays advisory via mypy/pyright until the team hardens it).
- **Casing** — snake_case functions/variables, PascalCase classes, UPPER_CASE
  constants (ruff `N`, pep8-naming).
- **Naming, three rules** — `ci_pipeline/check_banned_names.py`: (1)
  vague-when-alone names (helper/data/manager/foo... by themselves; compounds
  like `data_loader` are fine), (2) banned word-tokens anywhere in an identifier
  (`new`/`old`/`tmp`/`temp` → `new_data`, `data_new`, the variable `new_car` all
  rejected), and (3) no single-underscore prefix on module-level names or module
  filenames — in a service nothing imports your modules from outside, so
  `_configure` vs `configure` marks nothing (see
  https://dbader.org/blog/meaning-of-underscores-in-python; `self._attr`,
  `__dunder__`, trailing `class_` and the bare `_` throwaway stay allowed).
  Only identifiers are checked, so string keys and dataframe columns
  (`car_data["new_car"]`) are exempt. Extensible via conventions
  `naming.extra_banned` and `naming.banned_tokens`.
- **No `global` keyword** (ruff PLW0603) and **no mutable module-level state**
  (`ci_pipeline/check_module_state.py`). Use the Settings singleton or DI instead.
- **`load_dotenv`/`os.getenv` only in the settings module** — `check_load_dotenv.py`.
- **No scripts committed at the repo root** — `ci_pipeline/check_root_scripts.py`;
  personal scripts go in `scripts/` (relaxed sandbox), shipping code in `src/`.
- **Import ordering** — ruff `I` (isort) is in the rule set; `task format`
  auto-fixes it, so import order is never a manual chore.
- **Spelling** — codespell over code, comments and docs; legitimate terms go in
  `.codespell-ignore.txt` (one word per line, user-owned).
- **File/function size** — `ci_pipeline/check_sizes.py` (warn 450/100, fail
  600/150; complexity C901≤10 is the primary signal, lines are the backstop).
- **No imports inside functions** (ruff PLC0415) unless allow-listed in
  conventions `lazy_imports` for genuinely heavy/optional modules.
- **pathlib over os.path** (ruff PTH); **no `print`** (ruff T20); **4 spaces**
  (ruff format + W191 + editorconfig).
- **Dependency hygiene** — deptry fails if an import isn't declared in pyproject
  (catches `uv pip install` without `uv add`); `notebooks/` is excluded.

## Profiling (diagnostic, never a gate)

Outputs are written to `.profiles/` (gitignored). The `.md` summaries are
LLM-readable — when investigating a slowdown, read `.profiles/latest.md`.

- `task profile-quick -- uv run python script.py` → flamegraph SVG + `latest.md`
  table (py-spy runs via `uvx`, no install needed).
- `task profile-mem -- script.py` → scalene CPU+memory `mem.md` (scalene runs
  via `uv run --with scalene`, so it sees the project env without living in it).

Suggest profiling when generated code loops over large data, makes concurrent
LLM/API calls, or uses async/threading — the team rarely profiles on their own.

## Adding dependencies safely

Use `uv add <pkg>`, never `uv pip install` (deptry will fail the latter). Before
adding something unfamiliar, run `task audit-package -- <pkg>` (guarddog
supply-chain scan). `task audit-new-deps` scans only newly-locked packages.

## Retrofitting an existing messy repo

If `task ci-check` drowns the user in pre-existing violations: the size and
signature checks are already changed-lines-only, so they won't block unrelated
work. For the whole-repo checks (ruff, mypy), set them advisory first
(`mypy || true` is already advisory), run `task format` to auto-fix what's
mechanical, and tighten incrementally. Don't make the user fix the entire history
to land one PR.

## Future updates

The tool sections carry managed-region markers and the merge is non-destructive,
so a later version of this skill can update its own config without clobbering
hand edits. Keep that contract: never overwrite user values, only add missing ones.
