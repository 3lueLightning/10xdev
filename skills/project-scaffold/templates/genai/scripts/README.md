# `scripts/` — your relaxed sandbox for throwaway scripts

Personal experiments, one-off data pokes, quick API smoke tests — they live
here, not at the repo root (the gate rejects scripts committed at the root) and
not in `src/` (where the full standards apply).

Like `notebooks/`, this folder is exempt from lint, typing, size, and naming
checks. Two things still hold: **no secrets** (gitleaks scans everything), and
once a script grows into something the project relies on, graduate it into
`src/` where the standards apply.

Not to be confused with `ci_pipeline/`, which holds the quality gate's own
check scripts and is owned by the quality-gates skill.
