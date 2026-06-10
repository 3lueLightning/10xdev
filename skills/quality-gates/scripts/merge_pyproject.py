#!/usr/bin/env python3
"""Idempotently merge the quality-gates [tool.*] sections into a project's
pyproject.toml, preserving existing content, comments, and formatting.

Uses tomlkit. Only adds sections/keys that are absent -- it never overwrites a
value the project already set, so re-running on an existing project is safe.
This is the mechanism that keeps future skill updates non-destructive.

Usage:
    merge_pyproject.py <project_pyproject.toml> <tool_sections.toml>
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import tomlkit


def merge_missing(dst: Any, src: Any) -> None:
    for key, value in src.items():
        if key not in dst:
            dst[key] = value
        elif hasattr(value, "items") and hasattr(dst[key], "items"):
            merge_missing(dst[key], value)
        # else: key exists as a scalar -> respect the project's choice


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: merge_pyproject.py <pyproject.toml> <tool_sections.toml>",
            file=sys.stderr,
        )
        return 2
    target_path, sections_path = sys.argv[1], sys.argv[2]
    target = tomlkit.parse(Path(target_path).read_text())
    sections = tomlkit.parse(Path(sections_path).read_text())
    merge_missing(target, sections)
    with Path(target_path).open("w") as fh:
        fh.write(tomlkit.dumps(target))
    print(f"Merged tool sections into {target_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
