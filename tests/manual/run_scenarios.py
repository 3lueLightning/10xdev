#!/usr/bin/env python3
"""Tier-A mechanical harness for the quality-gates skill.

Not a pytest suite (that's tests/test_*.py, which checks the scripts'
mechanics). This is the "does it actually feel right end to end" harness: for
each fixture under fixtures/, it stages a scratch git repo, applies
quality-gates the same way apply.py does it, runs the real gate
(`task setup` + `task ci-check`), and — for the profiler fixture — runs the
profiler against a genuinely slow script and renders both the agent-facing
table and a plain-English digest. Every scenario gets a dated report under
runs/ so you can diff today's feel against last month's before calling a
change to the skill share-ready.

This only covers what a script can observe mechanically. It cannot tell you
whether the interview was pleasant or the agent explained itself well before
running `uv add` — that's what AGENT_RUN.md (Tier B, a live Claude Code
session against the same fixtures) is for.

Usage:
    uv run tests/manual/run_scenarios.py                 # all scenarios
    uv run tests/manual/run_scenarios.py --scenario messy_repo
    uv run tests/manual/run_scenarios.py --keep           # keep scratch dirs
    uv run tests/manual/run_scenarios.py --list
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
FIXTURES = HERE / "fixtures"
APPLY_PY = REPO_ROOT / "skills" / "quality-gates" / "scripts" / "apply.py"

# Mirrors SKILL.md step 3 exactly (guarddog/py-spy/scalene excluded on purpose --
# they're run on demand via uvx, never added to the project's lockfile).
DEV_DEPS = [
    "ruff",
    "mypy",
    "pyright",
    "bandit",
    "pip-audit",
    "deptry",
    "codespell",
    "pytest",
    "pytest-cov",
    "pre-commit",
    "pydantic-settings",
    "tomlkit",
    "pyyaml",
]

SCENARIOS: dict[str, dict] = {
    "bare_package": {
        "description": "Pure greenfield: `uv init --package` output, no "
        "tooling and no tests at all. Checks whether the from-nothing apply "
        "is immediately usable. Known result: `task ci-check` fails out of "
        "the box here because pytest exits 5 (no tests collected) -- "
        "quality-gates alone doesn't seed a placeholder test the way "
        "project-scaffold does. Worth knowing before you tell a team "
        "'run this on your empty repo.'",
        "profile_target": None,
    },
    "messy_repo": {
        "description": "Retrofit story: a repo the team wrote before any "
        "tooling existed, with several real violations already committed "
        "(mutable module state, a banned name token, os.getenv() outside "
        "settings, an untyped signature, a script at the repo root). Checks "
        "how loudly ci-check fails on day one and whether that failure "
        "output would make sense to the team member seeing it first.",
        "profile_target": None,
    },
    "pretooled_repo": {
        "description": "Merge story: a repo that already hand-hardened some "
        "[tool.*] pyproject sections, plus a hand-customized ruff.toml and "
        ".pre-commit-config.yaml, before quality-gates ever touched it. "
        "Checks what survives apply.py and what gets silently overwritten.",
        "profile_target": None,
    },
    "slow_workload": {
        "description": "Profiler fixture: scripts/slow_task.py has a real "
        "CPU hotspot (naive recursive fib) and a real memory hog (a growing "
        "list). Checks that `task profile-quick` / `task profile-mem` "
        "actually work and that the output is legible both to an agent "
        "(the .md table) and to a human (a plain-English digest). Also "
        "inherits the zero-tests `task ci-check` failure from bare_package "
        "since it's otherwise a bare package -- that's expected here, the "
        "point of this scenario is section 5, not section 4.",
        "profile_target": "scripts/slow_task.py",
    },
}


def run(cmd: list[str], cwd: Path, timeout: int = 600) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout + proc.stderr


def tail(text: str, n: int = 40) -> str:
    lines = text.strip("\n").splitlines()
    return "\n".join(lines[-n:])


def git(scratch: Path, *args: str) -> tuple[int, str]:
    return run(["git", *args], cwd=scratch)


def top_table_row(md_text: str) -> list[str] | None:
    """First data row of a `| a | b | c |` markdown table (after the `|---|` separator)."""
    lines = md_text.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("|---"):
            for row in lines[i + 1 :]:
                if row.strip().startswith("|"):
                    cells = [c.strip().strip("`") for c in row.strip().strip("|").split("|")]
                    return cells
            break
    return None


def human_cpu_digest(md_text: str, script_rel: str) -> str:
    row = top_table_row(md_text)
    if not row or len(row) < 3:
        return "No CPU hotspot could be extracted from the profile (too few samples?)."
    name, loc, pct = row[0], row[1], row[2]
    return (
        f"The profiler found the hot path in `{name}()` at {loc} -- it's eating "
        f"~{pct} of CPU time while running `{script_rel}`. If that's a naive "
        f"recursive or nested-loop shape, that's usually the fix (memoize, "
        f"vectorize, or cache). Open `.profiles/latest.svg` in a browser for "
        f"the visual flamegraph."
    )


def human_mem_digest(md_text: str) -> str:
    row = top_table_row(md_text)
    if not row or len(row) < 3:
        return "No memory hotspot could be extracted from the profile."
    loc, cpu, peak_mb = row[0], row[1], row[2]
    return (
        f"Peak memory was driven by {loc} (~{peak_mb} MB, {cpu} CPU there too). "
        f"If that's a list/dict being built eagerly, consider a generator or "
        f"chunking instead of holding it all in memory at once."
    )


def stage_scenario(name: str, scratch: Path) -> None:
    shutil.copytree(FIXTURES / name, scratch)
    git(scratch, "init", "-q")
    git(scratch, "config", "user.email", "quality-gates-harness@example.com")
    git(scratch, "config", "user.name", "quality-gates harness")
    git(scratch, "add", "-A")
    git(scratch, "commit", "-qm", "baseline fixture")


def diff_excerpt(scratch: Path, path: str, max_lines: int = 20) -> str:
    _, out = git(scratch, "diff", "--", path)
    lines = out.splitlines()
    if len(lines) > max_lines:
        lines = [*lines[:max_lines], f"... ({len(out.splitlines()) - max_lines} more lines)"]
    return "\n".join(lines)


def run_scenario(name: str, spec: dict, work_root: Path, out_dir: Path, keep: bool) -> None:
    print(f"\n=== {name} ===")
    scratch = work_root / name
    stage_scenario(name, scratch)
    pre_existing = set(git(scratch, "ls-files")[1].splitlines())

    report = [
        f"# Scenario: {name}",
        "",
        f"Run at: {datetime.now(UTC).isoformat()}Z",
        "",
        f"Fixture: `tests/manual/fixtures/{name}/`",
        "",
        "## What this scenario is for",
        "",
        spec["description"],
        "",
    ]

    # 1. apply quality-gates
    print("  applying quality-gates ...")
    code, out = run(["uv", "run", str(APPLY_PY), "--dest", ".", "--forge", "github"], cwd=scratch)
    report += [
        "## 1. Apply quality-gates",
        "",
        "Command: `uv run apply.py --dest . --forge github`",
        f"Exit code: {code}",
        "",
        "```",
        tail(out, 25),
        "```",
        "",
    ]

    _, status = git(scratch, "status", "--porcelain")
    touched = [line[3:] for line in status.splitlines() if line.strip()]
    modified_existing = [f for f in touched if f in pre_existing]
    newly_added = [f for f in touched if f not in pre_existing]

    report += ["### Newly added files", ""]
    report += [f"- {f}" for f in sorted(newly_added)] or ["- (none)"]
    report += ["", "### Pre-existing files modified by apply.py", ""]
    if modified_existing:
        for f in sorted(modified_existing):
            report += [f"- `{f}`", "", "```diff", diff_excerpt(scratch, f), "```", ""]
    else:
        report += ["- (none -- nothing pre-existing was touched)", ""]

    git(scratch, "add", "-A")
    git(scratch, "commit", "-qm", "apply quality-gates")

    # apply.py deliberately does NOT install the dev tools -- SKILL.md step 3
    # has the agent show the user this list, then run `uv add --dev` as its
    # own visible action. Do that here so task setup/ci-check have something
    # to run; the actual "did it explain itself first" question is Tier B's.
    print("  adding dev dependencies ...")
    dev_code, dev_out = run(["uv", "add", "--dev", *DEV_DEPS], cwd=scratch)
    report += [
        "## 1b. Add dev dependencies (SKILL.md step 3, not done by apply.py)",
        "",
        f"Command: `uv add --dev {' '.join(DEV_DEPS)}`",
        f"Exit code: {dev_code}",
        "",
        "```",
        tail(dev_out, 15),
        "```",
        "",
    ]
    git(scratch, "add", "-A")
    git(scratch, "commit", "-qm", "add dev dependencies")

    # idempotency: run again, expect no diff
    print("  checking idempotency ...")
    run(["uv", "run", str(APPLY_PY), "--dest", ".", "--forge", "github"], cwd=scratch)
    _, status2 = git(scratch, "status", "--porcelain")
    idempotent = not status2.strip()
    report += [
        "## 2. Idempotency (apply.py run a second time)",
        "",
        "Idempotent: yes -- no changes on re-run."
        if idempotent
        else f"Idempotent: **no** -- second run changed:\n\n```\n{status2}\n```",
        "",
    ]
    git(scratch, "checkout", "--", ".")
    git(scratch, "clean", "-fdq")

    # setup + ci-check
    print("  task setup ...")
    setup_code, setup_out = run(["task", "setup"], cwd=scratch)
    report += [
        "## 3. `task setup`",
        "",
        f"Exit code: {setup_code}",
        "",
        "```",
        tail(setup_out, 20),
        "```",
        "",
    ]

    print("  task ci-check (this can take a while) ...")
    ci_code, ci_out = run(["task", "ci-check"], cwd=scratch, timeout=900)
    verdict = "PASSED" if ci_code == 0 else "FAILED"
    report += [
        f"## 4. `task ci-check` -- {verdict}",
        "",
        f"Exit code: {ci_code}",
        "",
        "```",
        tail(ci_out, 60),
        "```",
        "",
    ]

    # profiler
    target = spec.get("profile_target")
    if target:
        print("  profiling ...")
        report += ["## 5. Profiler", ""]
        pq_code, pq_out = run(
            ["task", "profile-quick", "--", "uv", "run", "python", target], cwd=scratch
        )
        latest_md = scratch / ".profiles" / "latest.md"
        if pq_code == 0 and latest_md.exists():
            md_text = latest_md.read_text()
            report += [
                "### CPU profile",
                "",
                "**For humans:**",
                "",
                human_cpu_digest(md_text, target),
                "",
                "**For the agent** (raw `ci_pipeline/profile_summary.py` output):",
                "",
                md_text,
                "",
            ]
        else:
            report += [
                "### CPU profile",
                "",
                f"`task profile-quick` did not produce a report (exit {pq_code}). "
                f"On macOS py-spy needs elevated privileges -- try running this "
                f"scenario's profiling step manually with `sudo`.",
                "",
                "```",
                tail(pq_out, 15),
                "```",
                "",
            ]

        pm_code, pm_out = run(["task", "profile-mem", "--", target], cwd=scratch)
        mem_md = scratch / ".profiles" / "mem.md"
        if pm_code == 0 and mem_md.exists():
            md_text = mem_md.read_text()
            report += [
                "### Memory profile",
                "",
                "**For humans:**",
                "",
                human_mem_digest(md_text),
                "",
                "**For the agent** (raw `ci_pipeline/profile_summary.py --mem` output):",
                "",
                md_text,
                "",
            ]
        else:
            report += [
                "### Memory profile",
                "",
                f"`task profile-mem` did not produce a report (exit {pm_code}).",
                "",
                "```",
                tail(pm_out, 15),
                "```",
                "",
            ]

    report += [
        "## Your subjective notes (fill in after a Tier-B live-agent run)",
        "",
        "- Interview clarity:",
        "- Permission-prompt count / friction:",
        "- Anything here you wouldn't want your team to see:",
        "- Would you ship this as-is? Y/N + why:",
        "",
    ]

    dest = out_dir / name
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "report.md").write_text("\n".join(report), encoding="utf-8")
    print(f"  report: {dest / 'report.md'}  [{verdict}]")

    if keep:
        print(f"  scratch kept at: {scratch}")
    else:
        shutil.rmtree(scratch, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--scenario",
        action="append",
        choices=sorted(SCENARIOS),
        help="run only this scenario (repeatable)",
    )
    ap.add_argument(
        "--keep", action="store_true", help="keep scratch dirs instead of deleting them"
    )
    ap.add_argument(
        "--out",
        type=Path,
        help="output dir for the report (default: tests/manual/runs/<timestamp>)",
    )
    ap.add_argument("--list", action="store_true", help="list scenarios and exit")
    args = ap.parse_args()

    if args.list:
        for name, spec in SCENARIOS.items():
            print(f"{name}: {spec['description']}")
        return 0

    names = args.scenario or list(SCENARIOS)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    out_dir = args.out or (HERE / "runs" / stamp)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.keep:
        # A TemporaryDirectory would delete itself (and any scratch dirs we
        # asked to keep) on exit, so use a persistent location instead.
        work_root = out_dir / "scratch"
        work_root.mkdir(parents=True, exist_ok=True)
        for name in names:
            run_scenario(name, SCENARIOS[name], work_root, out_dir, args.keep)
    else:
        with tempfile.TemporaryDirectory(prefix="qg-scenarios-") as tmp:
            work_root = Path(tmp)
            for name in names:
                run_scenario(name, SCENARIOS[name], work_root, out_dir, args.keep)

    print(f"\nAll reports under: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
