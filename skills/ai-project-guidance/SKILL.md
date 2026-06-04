---
name: ai-project-guidance
description: Generate and maintain the AI-assistant guidance files for a Python GenAI project - a canonical AGENTS.md (typing, naming, the three-bucket config/secrets/constants rule with pydantic-settings, async/concurrency dos-and-donts, logging levels, prompt management, banned identifiers, file/function size limits, notebook sandbox rules) plus a thin CLAUDE.md pointer. Use whenever the user wants to create or refresh AGENTS.md / CLAUDE.md, set coding conventions for AI assistants, give the copilot rules to follow, or standardize how Claude Code / Copilot / gemini-cli behave in a repo. Called by project-scaffold; also runnable standalone to (re)generate guidance as a project evolves. Interoperates with other tools that read AGENTS.md.
---

# AI Project Guidance

Generate the guidance files that tell AI coding assistants (Claude Code, Copilot,
gemini-cli, etc.) how to write code in this project. `AGENTS.md` is the emerging
cross-tool standard and is the single source of truth; `CLAUDE.md` is a thin
pointer to it so the two never drift.

This is a GenAI-focused skill (v1). The conventions it encodes match exactly what
the `quality-gates` hooks enforce, so the guidance and the gates agree.

## What to do

### 1. Gather project facts

Read `.project-conventions.yaml` if present (written by `project-scaffold`) for
the package name, Python version, banned-name additions, prompt management, and
size thresholds. If absent, ask for the package name and Python version, and use
sensible defaults for the rest.

### 2. Render AGENTS.md

Copy `templates/AGENTS.md` to the project root, substituting:

- `{{project_name}}` — the human project name.
- `{{pkg}}` — the import package under `src/`.
- `{{python_version}}` — e.g. `3.13`.
- `{{domain_summary}}` and `{{team_norms}}` — from the `guidance:` block in
  `.project-conventions.yaml` if present. If there's no guidance block, delete
  the whole "## Project context" section rather than leaving empty placeholders.

If the conventions file extends the banned-name list (`naming.extra_banned`),
adds banned suffixes (`naming.banned_suffixes`, e.g. `_new`/`_old`), or changes
size thresholds, reflect those in the rendered file so guidance matches the
gates. If prompt management is Langfuse/Langsmith, keep the observability
paragraph and note prompts are managed externally (no in-repo `prompts/`); if
it's YAML-only, prompts live in `src/<pkg>/prompts/` (the flag defaults off).

### 3. Add CLAUDE.md

Copy `templates/CLAUDE.md` to the project root unchanged. It only points to
AGENTS.md — do not duplicate content.

### 4. Confirm

Tell the user the two files were created and that re-running this skill refreshes
them (e.g. after thresholds change). The files are safe to hand-edit; re-running
regenerates from the template, so substantial local edits should instead go into
`.project-conventions.yaml` where this skill reads them.

## Notes

- Keep one source of truth. If a future tool wants a differently-named guidance
  file, make it a pointer to AGENTS.md too, never a second copy.
- The guidance deliberately explains *why* each rule exists rather than just
  asserting it — assistants (and humans) follow rules they understand and ignore
  rules they don't.
