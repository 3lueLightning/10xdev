#!/usr/bin/env python3
"""Forbid committed script files at the repository root.

The root of the project is for configuration and documentation, not code.
Production code lives in src/<pkg>/, the gate's own checks in ci_pipeline/,
and personal experiments in scripts/ or notebooks/ (both relaxed sandboxes).
A stray run_me.py at the root bypasses all of that structure, so this check
fails the gate when a tracked or staged script sits directly at the root.
"""

from __future__ import annotations

from common import fail, run_git

SCRIPT_SUFFIXES = (".py", ".sh", ".bash", ".zsh")


def root_scripts() -> list[str]:
    tracked = run_git("ls-files").splitlines()
    staged = run_git("diff", "--cached", "--name-only", "--diff-filter=d").splitlines()
    return sorted(
        name for name in {*tracked, *staged} if "/" not in name and name.endswith(SCRIPT_SUFFIXES)
    )


def main() -> int:
    messages = [
        f"{name}: scripts don't belong at the repo root -- move it into "
        f"src/<pkg>/ (shipping code), scripts/ (personal experiments), or "
        f"ci_pipeline/ (gate tooling)"
        for name in root_scripts()
    ]
    return fail(messages, "Script files committed at the repository root.")


if __name__ == "__main__":
    raise SystemExit(main())
