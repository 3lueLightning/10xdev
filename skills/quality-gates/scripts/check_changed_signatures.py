#!/usr/bin/env python3
"""Enforce that function signatures are typed, on CHANGED code only.

Greenfield-friendly: a function fails only if its `def` line was added or
modified versus the base branch, so pre-existing code never blocks an unrelated
push. Every argument (except self/cls and *args/**kwargs) must be annotated, and
every function must declare a return type.

Usage:
    check_changed_signatures.py            # warn (advisory)
    check_changed_signatures.py --strict   # non-zero exit on violations
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from _common import changed_line_numbers, changed_python_files, fail

EXEMPT_ARGS = {"self", "cls"}


def _missing_annotations(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    problems: list[str] = []
    a = func.args
    positional = [*a.posonlyargs, *a.args, *a.kwonlyargs]
    for arg in positional:
        if arg.arg in EXEMPT_ARGS:
            continue
        if arg.annotation is None:
            problems.append(f"argument '{arg.arg}' is not typed")
    if func.returns is None:
        problems.append("no return type annotation")
    return problems


def check_file(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return []  # ruff's syntax gate reports this separately
    changed = changed_line_numbers(path)
    treat_whole_file = not changed
    out: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not (treat_whole_file or node.lineno in changed):
            continue
        for problem in _missing_annotations(node):
            rel = path
            out.append(f"{rel}:{node.lineno} {node.name}(): {problem}")
    return out


def main() -> int:
    strict = "--strict" in sys.argv
    messages: list[str] = []
    for path in changed_python_files():
        messages.extend(check_file(path))
    if not messages:
        return 0
    if strict:
        return fail(
            messages,
            "Typed signatures required on changed code (args + return). "
            "Add annotations, e.g. def run(items: list[str]) -> int:",
        )
    print("⚠ signature typing (advisory at commit; enforced on push):", file=sys.stderr)
    for m in messages:
        print(f"  - {m}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
