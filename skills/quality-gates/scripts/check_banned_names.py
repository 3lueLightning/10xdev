#!/usr/bin/env python3
"""Flag poorly-named identifiers in CHANGED code.

Two rules, applied only to identifiers you DEFINE (variables, function/class
names, arguments) -- never to string literals, so dict keys and dataframe
columns like ``car_data["new_car"]`` are unaffected:

1. Vague-when-alone: a name that is *exactly* one of helper/util/data/manager/...
   is banned, but compounds are fine (``data_loader``, ``user_helper``).
2. Banned tokens anywhere: ``new``/``old``/``tmp``/``temp`` are rejected wherever
   they appear as a word in an identifier -- ``new_data``, ``data_new`` and the
   variable ``new_car`` are all flagged, because they name *when/which version*
   rather than *what*. Matching is token-wise (split on ``_`` and camelCase), so
   ``renew``, ``news`` and ``template`` are fine.

Both lists come from .project-conventions.yaml (naming.banned_when_alone +
naming.extra_banned, and naming.banned_tokens). snake_case / PascalCase / casing
itself is enforced separately by ruff's pep8-naming (N) rules.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from _common import (
    banned_names,
    banned_tokens,
    changed_line_numbers,
    changed_python_files,
    fail,
)

_WORD = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+")


def tokens(name: str) -> list[str]:
    """Split an identifier into lowercase word tokens (snake_case + camelCase)."""
    out: list[str] = []
    for part in name.strip("_").split("_"):
        out += _WORD.findall(part)
    return [t.lower() for t in out if t]


def _iter_names(tree: ast.AST) -> Iterator[tuple[str, int, str]]:
    """Yield (identifier, lineno, kind) for every user-defined name in the tree."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node.name, node.lineno, "function"
            all_args = [
                *node.args.posonlyargs,
                *node.args.args,
                *node.args.kwonlyargs,
                node.args.vararg,
                node.args.kwarg,
            ]
            for arg in all_args:
                if arg is not None:
                    yield arg.arg, arg.lineno, "argument"
        elif isinstance(node, ast.ClassDef):
            yield node.name, node.lineno, "class"
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            # covers assignment, augmented-assign, for/with-as, comprehension and
            # walrus targets -- everywhere a new binding name is introduced.
            yield node.id, node.lineno, "name"


def _check_name(
    name: str,
    lineno: int,
    kind: str,
    *,
    path: Path,
    alone: set[str],
    anywhere: set[str],
    treat_whole_file: bool,
    changed: set[int],
) -> str | None:
    if name.startswith("__") and name.endswith("__"):
        return None  # dunders are protocol, not chosen names
    if not (treat_whole_file or lineno in changed):
        return None
    parts = tokens(name)
    hit = anywhere.intersection(parts)
    if hit:
        word = sorted(hit)[0]
        return (
            f"{path}:{lineno} {kind} '{name}' contains '{word}'; name it for "
            f"what it holds, not when/which version (string keys are exempt)"
        )
    if len(parts) == 1 and parts[0] in alone:
        return f"{path}:{lineno} {kind} '{name}' is too vague on its own"
    return None


def check_file(path: Path, alone: set[str], anywhere: set[str]) -> list[str]:
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return []
    changed = changed_line_numbers(path)
    kwargs = {
        "path": path, "alone": alone, "anywhere": anywhere,
        "treat_whole_file": not changed, "changed": changed,
    }
    return [
        msg
        for name, lineno, kind in _iter_names(tree)
        if (msg := _check_name(name, lineno, kind, **kwargs))  # type: ignore[arg-type]
    ]


def main() -> int:
    alone = banned_names()
    anywhere = banned_tokens()
    messages: list[str] = []
    for path in changed_python_files():
        messages.extend(check_file(path, alone, anywhere))
    return fail(
        messages,
        "Names that don't say what they hold. Rename for what a thing IS "
        "(e.g. 'extract_invoice_fields', not 'process'; 'pending_users', not "
        "'users_new'). Strings, dict keys and dataframe columns are exempt.",
    )


if __name__ == "__main__":
    raise SystemExit(main())
