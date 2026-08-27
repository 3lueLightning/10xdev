# Tier B — live agent run (the actual "feel" test)

[run_scenarios.py](run_scenarios.py) (Tier A) proves the *mechanics* work: does
`apply.py` produce the right files, does `task ci-check` pass or fail for the
right reasons, does the profiler run. It cannot tell you whether the
interview was pleasant, whether the agent explained itself before running
`uv add`, whether you got hit with a wall of permission prompts, or whether
the tone is something you'd want a teammate to see. That's this document.

Run this on at least the scenario your change touches before calling a
quality-gates change share-ready — ideally all four periodically, since a
change to one part of the skill (e.g. the interview copy) can shift the feel
of every scenario.

## Procedure

For each fixture, stage a **clean** scratch copy and let the agent invoke the
skill itself — don't run `apply.py` yourself first, or you'll be testing
Tier A again instead of the interview.

```bash
export QG_REPO="$(git rev-parse --show-toplevel)"
export FIXTURE=messy_repo   # bare_package | messy_repo | pretooled_repo | slow_workload
export SANDBOX="$(mktemp -d)/$FIXTURE"
cp -R "$QG_REPO/tests/manual/fixtures/$FIXTURE" "$SANDBOX"
cd "$SANDBOX"
git init -q
git config user.email t@t && git config user.name t
git add -A && git commit -qm "baseline fixture"
```

Then open Claude Code in `$SANDBOX` and prompt it the way a team member
actually would — not "run apply.py", but e.g. *"add quality gates to this
repo"*. For `slow_workload`, once quality-gates is applied, add a follow-up
like *"scripts/slow_task.py feels slow, can you show me why?"* to exercise
the profiling flow specifically and see whether the agent surfaces the
human-readable digest or just the raw agent-facing table.

## Checklist

Fill this in during or right after the session, then save it as
`tests/manual/runs/<timestamp>/<fixture>/agent-notes.md` (pair it with that
run's Tier A `report.md` if you have one from the same day).

- **Interview clarity** — was it obvious what was being asked and why?
- **Permission-prompt count** — SKILL.md's whole "one script call instead of
  one approval per file" design exists to keep this low. Did it?
- **Dev-dependency transparency** — did it show you the `uv add --dev` list
  *before* running it, per SKILL.md step 3, or did it just run?
- **Retrofitting tone** (`messy_repo`) — did the first failure output make
  sense on its own, or did it feel like triage? (`task ci-check` stops at
  the first failing sub-task, so the agent may need more than one pass here
  — is it upfront about that?)
- **Silent clobbers** (`pretooled_repo`) — did it notice or mention your
  hand-customized `ruff.toml` / `.pre-commit-config.yaml` before overwriting
  them, or did they just vanish?
- **Profiler legibility** (`slow_workload`) — did it point you at both the
  plain-English summary and the agent `.md`/flamegraph, or only one?
- **Would you be comfortable if a teammate saw this exact transcript?**
  Y/N + why.

## Cleanup

```bash
rm -rf "$(dirname "$SANDBOX")"
```
