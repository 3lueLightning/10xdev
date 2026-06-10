# `ci_pipeline/` — the quality gate's own check scripts

Owned by the **quality-gates** skill (re-run it to regenerate). These are the
custom checks that `Taskfile.yml` wires into `task precommit-fast` and
`task ci-check` — naming, signature typing, module state, config hygiene,
sizes, root-script and dependency checks. `common.py` holds their shared
helpers.

This folder is **not** for your own scripts — that's what `scripts/` (relaxed
sandbox) is for. Don't edit these by hand; thresholds and word lists live in
`.project-conventions.yaml`, which every check reads.
