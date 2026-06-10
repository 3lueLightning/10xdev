#!/usr/bin/env python3
"""Warn/fail on oversized files and functions, using conventions thresholds.

Ruff has no file-length rule and only a statement-count proxy for functions, so
this fills the gap with line-based limits. Complexity (ruff C901) is the primary
quality signal; these line limits are a coarse backstop for the genuinely huge.
tests/ and notebooks/ are exempt (relaxed dirs).

Defaults (overridable in .project-conventions.yaml):
    file_length:     warn 450, fail 600
    function_length: warn 100, fail 150
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from common import (
    changed_python_files,
    fail,
    is_relaxed,
    load_conventions,
    repo_root,
)


def all_python_files() -> list:
    root = repo_root()
    return (
        [p for p in (root / "src").rglob("*.py") if not is_relaxed(p)]
        if (root / "src").exists()
        else [p for p in root.rglob("*.py") if not is_relaxed(p) and ".venv" not in p.parts]
    )


def function_line_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    linenos = [getattr(n, "end_lineno", None) or getattr(n, "lineno", None) for n in ast.walk(node)]
    linenos = [n for n in linenos if n is not None]
    last = max(linenos) if linenos else node.lineno
    return last - node.lineno + 1


def check_file(path: Path, fl: dict, func_l: dict) -> tuple[list[str], list[str]]:
    warns: list[str] = []
    fails: list[str] = []
    text = path.read_text()
    n_lines = text.count("\n") + 1
    if n_lines >= fl["fail"]:
        fails.append(f"{path}: {n_lines} lines (limit {fl['fail']}) -- split this module")
    elif n_lines >= fl["warn"]:
        warns.append(f"{path}: {n_lines} lines (warn {fl['warn']})")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return warns, fails
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            length = function_line_count(node)
            if length >= func_l["fail"]:
                fails.append(
                    f"{path}:{node.lineno} {node.name}(): {length} lines "
                    f"(limit {func_l['fail']}) -- break it up"
                )
            elif length >= func_l["warn"]:
                warns.append(
                    f"{path}:{node.lineno} {node.name}(): {length} lines (warn {func_l['warn']})"
                )
    return warns, fails


def main() -> int:
    conv = load_conventions()["quality"]
    fl = conv["file_length"]
    func_l = conv["function_length"]
    changed_only = "--changed-only" in sys.argv
    files = changed_python_files() if changed_only else all_python_files()

    all_warns: list[str] = []
    all_fails: list[str] = []
    for path in files:
        w, f = check_file(path, fl, func_l)
        all_warns.extend(w)
        all_fails.extend(f)

    for w in all_warns:
        print(f"⚠ {w}", file=sys.stderr)
    return fail(all_fails, "Oversized files/functions exceed the hard limit.")


if __name__ == "__main__":
    raise SystemExit(main())
