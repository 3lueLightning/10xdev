# HANDOFF — 10xdev skills

Context for whoever (human or agent) continues this work. The four skills under
`skills/` are built, tested, and packaged; this explains the design, the
decisions already locked, how to test, what's known-incomplete, and the next
steps (plugin packaging + permission ergonomics).

## What this is

Four composable Claude Code skills that scaffold Python **GenAI** projects for a
team of ~20 junior engineers and then keep the code clean. Dependency/build
order: **quality-gates → ai-project-guidance → project-scaffold → git-setup**
(scaffold orchestrates the other three). GenAI-only and greenfield for v1.

## The skills

1. **quality-gates** — installs uv, ruff (lint + format; replaces black), mypy
   (advisory) + pyright, bandit, pip-audit, deptry, codespell (with a user-owned
   `.codespell-ignore.txt` dictionary), gitleaks (via pre-commit), pytest +
   coverage (measured, gated only if a target is set). guarddog / py-spy /
   scalene are deliberately NOT dev deps — the Taskfile runs them via `uvx` /
   `uv run --with` so they never pollute the lockfile (guarddog's semgrep chain
   caused unfixable pip-audit CVEs). Two-stage hooks: pre-commit fast/forgiving
   (file-modifying fixers are pinned to the commit stage so a push is never
   aborted mid-flight), pre-push = `task ci-check` (strict). Multi-forge CI
   (github/gitlab/bitbucket/gitea) all calling `task ci-check`. Custom AST
   checks are copied into the project's **`ci_pipeline/`** (`scripts/` is the
   user's relaxed sandbox): `check_changed_signatures`, `check_banned_names`,
   `check_module_state`, `check_load_dotenv`, `check_sizes`, `check_new_deps`,
   `check_root_scripts`, plus `common.py`, `merge_pyproject.py`,
   `profile_summary.py`, and **`apply.py`** (one-shot installer, see
   "Permissions").
2. **ai-project-guidance** — generates a canonical `AGENTS.md` + thin `CLAUDE.md`.
   Includes a Clean Code philosophy section, a "never circumvent a failing gate"
   section, and a "coach the developer" section.
3. **project-scaffold** — orchestrator. Interviews the user (`interview.yaml`;
   question first, options with an Enter-able default, "why it matters" last),
   then runs **`scripts/render.py`** once to materialise the whole tree
   (including `docs/` + `mkdocs.yml` and the `scripts/` sandbox), writes
   `.project-conventions.yaml`, and calls the other three skills.
4. **git-setup** — creates the remote repo via gh/glab/tea when the user has
   admin and none exists, main+dev branches + branch protection, leaves the
   working copy on `dev`; always writes `.repo-config/REPO-SETUP.md` as fallback.

## Decisions already locked (do not silently relitigate)

- **src-layout, with the package name repeated**: `myproj/src/myproj/`. `src/` is
  an un-importable marker; the inner `src/<pkg>/` is the importable package and
  *must* be the distribution name. Explained to users in `src/README.md`.
- **Three-bucket config**: secrets → `.env`, loaded ONLY in `config/settings.py`
  via pydantic-settings `get_settings()`; configuration → `Settings` fields;
  true constants → `constants/`. No `os.getenv`/`load_dotenv` elsewhere
  (`check_load_dotenv.py`). No `global`, no mutable module-level state
  (`check_module_state.py` + ruff PLW0603).
- **Naming, three distinct rules** (`check_banned_names.py`, applied to
  identifiers only — never string literals, so dict keys / dataframe columns are
  exempt):
  1. *vague-when-alone* (`data`, `helper`, `process`, … by themselves; compounds
     like `data_loader` are fine) — `naming.banned_when_alone`.
  2. *banned token anywhere* (`new`/`old`/`tmp`/`temp` as a word token in an
     identifier → `new_data`, `data_new`, the variable `new_car`, `NewOrder` all
     rejected; `renew`/`news`/`template` are fine because matching is token-wise)
     — `naming.banned_tokens`. **This is the corrected rule** — an earlier
     version banned only suffixes; that was wrong.
  3. *no single-underscore prefix at module level* (names AND module filenames —
     `_common.py` is rejected). Rationale: in a service nothing imports modules
     from outside, so `_internal` marks nothing. Per dbader's underscore
     semantics, `self._attr` in classes, `__dunder__`, trailing `class_`, and
     the bare `_` throwaway stay allowed.
  Casing (snake_case / PascalCase / UPPER_CASE) is enforced by ruff `N`.
- **Project layout names**: gate tooling lives in `ci_pipeline/`; `scripts/` is
  the user's relaxed sandbox (in `layout.relaxed_dirs` with tests/notebooks);
  no script files at the repo root (`check_root_scripts.py`); docs are MkDocs
  (material + mkdocstrings, `task docs-serve`); repo configuration (REPO-SETUP,
  branch-protection payloads) lives in `.repo-config/`, not `docs/`.
- **Prompts** live as versioned YAML **inside the package** at
  `src/<pkg>/prompts/`, loaded via `importlib.resources` (wheel/container-safe).
  Exactly one location — never a root-level `prompts/`. If a prompt manager
  (Langfuse/Langsmith) is chosen, no prompts folder/loader is created at all.
- **Sizes/complexity** (in `.project-conventions.yaml`): file warn 450 / fail
  600; function warn 100 / fail 150; C901 ≤ 10 is the primary signal; PLR0915=70.
- **Relaxed sandboxes**: `tests/` and `notebooks/` skip lint/type/size/naming;
  secret scanning still applies. Notebooks keep outputs, no nbstripout.
- **Config provenance**: generated configs are annotated `(qg-default)` vs
  `(conv: KEY)` (see `ruff.toml`), and each carries an "owned by quality-gates"
  header. Honour this when adding config.
- **`.project-conventions.yaml` is the single contract** every skill reads.
  `render.py` writes it; quality-gates/ai-project-guidance read it. There's a
  `schema_version`, a `deferred` list (Phase-2 answers left at default), and an
  optional `guidance:` block (domain_summary, team_norms) that feeds AGENTS.md.
- **Dynamic Python default**: `render.py --print-python-default` → latest stable
  CPython minor minus one (3.13 as of mid-2026). `render.py` writes
  `.python-version`; quality-gates' `apply.py` won't clobber it.
- **Skill packaging quirk**: template dirs must NOT contain `{` `}` (zip download
  rejects invalid path chars). The package-name placeholder on disk is the
  brace-free token **`__pkg__`** (a directory), which `render.py` substitutes to
  the real name. File *contents* still use `{{pkg}}`/`{{project_name}}`/
  `{{python_version}}` — that's fine, only path names matter.

## The one-pass pattern (and why)

Both scaffolding and gate-application run as a **single script** rather than many
individual file writes, so the host agent approves once instead of per file.
Both carry **PEP 723 inline metadata** and are invoked with `uv run` (never bare
`python`, never a `pip install` first — that's what broke on machines with no
`python` shim and externally-managed Homebrew Pythons):

- `uv run skills/project-scaffold/scripts/render.py --answers a.yaml --dest <parent>`
  → renders tree, substitutes placeholders, applies conditional drops (api:none →
  no `api/`; langfuse/langsmith → no `prompts/`), wires deps + seeds deptry
  DEP002, writes `.python-version` + `.project-conventions.yaml`, prints a banner.
- `uv run skills/quality-gates/scripts/apply.py --dest <project> [--forge ...]`
  → copies config + check scripts (into `ci_pipeline/`), aligns `(conv:)` values
  in `ruff.toml`, merges `[tool.*]` into pyproject (non-destructive; preserves
  render's DEP002 seed), seeds `.codespell-ignore.txt` (never overwrites it),
  drops the CI file. Locates its own templates via `__file__`, so it works
  wherever installed. Does NOT install deps (that's `task setup`/`uv sync`).

The SKILL.md files explicitly forbid reading/`ls`/`grep`-ing the skills' own
`templates/` per file — that's what produced permission-prompt walls.

When extending: keep new file-producing work inside these scripts, not as
per-file agent writes.

## Permissions (answers the prompt-fatigue problem)

Installing a plugin does NOT auto-grant permissions. Two mechanisms reduce
prompts: (1) the one-pass scripts above (one `Bash(python …)` call each), and
(2) a `settings.json` allow-list — see `settings.example.json`. Claude Code runs
read-only `ls`/`cat`/`grep` without prompts, but *piped* commands still prompt
(known issue), which is another reason to prefer the scripts. `/permissions`
shows active rules.

## Testing

- `tests/test_naming.py` — the naming rule cases (incl. the string-key exemption).
- `tests/test_render.py` — renders projects for several answer sets; asserts no
  placeholder/brace leftovers, single package, in-package prompts, conditional
  drops, per-folder READMEs, pinned Python, conventions content.
- `.github/workflows/ci.yml` — runs the above, then scaffolds a project, applies
  the gates, `uv sync`s, and runs the full gate end-to-end.
- Run locally: `pip install pytest pyyaml tomlkit && python -m pytest tests/ -q`.
- **Dogfooding**: the skills' own scripts pass the gate they ship (the naming
  rule caught real `data`/`whole_file_new` violations in earlier drafts — keep
  shipped code clean under the rules, or CI's e2e job fails).

## Known limitations / next steps

1. **3.13 e2e not verified in the original sandbox** — that environment couldn't
   download a 3.13 build, so integration tests ran on 3.12 (logic-identical). On
   a normal machine / GitHub CI, 3.13 fetches fine; the CI job uses 3.12 for
   speed — consider a matrix (3.12, 3.13).
2. **`task` binary** wasn't installable in the original sandbox (release host
   blocked); gate steps were verified by running the underlying commands. Confirm
   `task ci-check` runs clean once `go-task` is installed.
3. **Marketplace `source: "./"`** in `.claude-plugin/marketplace.json` is the
   single-repo convention but should be validated with a real
   `/plugin marketplace add <repo>` + `/plugin install`. Adjust if Claude Code
   wants the plugin in a subdirectory.
4. **Beyond GenAI / brownfield** — v1 is GenAI greenfield. A `--answers` file path
   already exists for non-interactive runs; a future non-GenAI template would
   slot in beside `templates/genai/`.
5. Consider `deployment_target`-driven logging (JSON-on-stdout for cloud) — the
   seam exists in conventions but isn't fully wired.

## File map

- `skills/quality-gates/{SKILL.md, .project-conventions.default.yaml,
  scripts/*.py, templates/*}` — the skill's own `scripts/` dir is the skill
  packaging convention; `apply.py` copies the checks into the *project's*
  `ci_pipeline/`. `templates/ci/{github,gitlab,bitbucket,gitea}.yml` (copied to
  `ci-check.yml` on github/gitea, matching the required status check name).
- `skills/project-scaffold/{SKILL.md, interview.yaml,
  .project-conventions.default.yaml, scripts/render.py, templates/genai/...}` —
  template package dir is `templates/genai/src/__pkg__/`.
- `skills/ai-project-guidance/{SKILL.md, templates/AGENTS.md, templates/CLAUDE.md}`.
- `skills/git-setup/{SKILL.md, ...}`.
- Packaging: `.skill` zips are produced with skill-creator's `package_skill.py`
  for claude.ai/API upload; for Claude Code, skills are read UNPACKED from
  `skills/<name>/SKILL.md` (the plugin layout already provides that).
