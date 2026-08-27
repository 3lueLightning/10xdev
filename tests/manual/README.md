# Subjective / integration testing for quality-gates

`tests/test_*.py` (pytest) checks that the scripts under
`skills/quality-gates/scripts/` do the right thing mechanically —
unit-level, fast, CI-gated. This directory is different: it exercises the
**skill** end to end, scoped to quality-gates alone (deliberately decoupled
from project-scaffold / ai-project-guidance / git-setup, so a change here
doesn't require touching the other skills to evaluate), and asks a harder
question — *does this actually feel right, and would you be comfortable
putting it in front of your team?*

Two tiers:

- **Tier A — [run_scenarios.py](run_scenarios.py)** (mechanical, scripted).
  For each fixture: stage a scratch git repo, run `apply.py`, add the dev
  dependencies SKILL.md step 3 documents (apply.py deliberately doesn't do
  this itself), run `task setup` + `task ci-check`, and — for the profiler
  fixture — run the profiler and render both the agent-facing table and a
  plain-English digest. Writes a dated report to `runs/<timestamp>/<scenario>/report.md`.
  Good for regression: did something that used to pass start failing.

  ```bash
  uv run tests/manual/run_scenarios.py                    # all four scenarios
  uv run tests/manual/run_scenarios.py --scenario messy_repo
  uv run tests/manual/run_scenarios.py --keep              # inspect the scratch repo afterward
  uv run tests/manual/run_scenarios.py --list
  ```

- **Tier B — [AGENT_RUN.md](AGENT_RUN.md)** (live agent, by hand). A real
  Claude Code session against the same fixtures, driven the way a team
  member actually would, with a checklist covering the things Tier A cannot
  see: interview clarity, permission-prompt friction, whether new
  dependencies are explained before they're added, tone. This is where the
  "am I comfortable sharing this with my team" judgment actually gets made.

Run Tier A whenever you touch `skills/quality-gates/`; run Tier B on at
least the scenario your change touches before calling it share-ready.

## Fixtures

Small, static, checked-in repos under `fixtures/` — read or hand-edit them
directly rather than regenerating them.

| fixture | what it's for |
|---|---|
| `bare_package` | pure greenfield, zero tooling, zero tests |
| `messy_repo` | retrofit story: several real pre-existing violations in one file (mutable module state, a banned name token, `os.getenv()` outside settings, an untyped signature, a script at the repo root) |
| `pretooled_repo` | merge story: hand-hardened `[tool.*]` pyproject sections plus a customized `ruff.toml` / `.pre-commit-config.yaml`, to see what survives `apply.py` and what gets silently overwritten |
| `slow_workload` | profiler: `scripts/slow_task.py` has a real CPU hotspot (naive recursive fib) and a real memory hog (a growing list) |

## Platform note

`task profile-quick` (py-spy) requires elevated privileges on macOS — that's
an OS-level ptrace restriction, not a bug in the harness or the skill. If
that section of a report shows `This program requires root on OSX`, rerun
that one step with `sudo`.

## Relationship to the older manual checklist

[quality-gates.md](quality-gates.md) predates this harness and chains through
`project-scaffold`'s `render.py` to get a starting project — useful for
testing the two skills together, but it means every quality-gates-only
question (does retrofitting feel right, does the merge behave) is entangled
with scaffold's own behavior. This harness exists to test quality-gates in
isolation; keep both around, they answer different questions.
