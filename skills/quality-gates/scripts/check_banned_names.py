#!/usr/bin/env python3
"""Flag poorly-named identifiers in CHANGED code.

Three rules, applied only to identifiers you DEFINE (variables, function/class
names, arguments) -- never to string literals, so dict keys and dataframe
columns like ``car_data["new_car"]`` are unaffected:

1. Vague-when-alone: a name that is *exactly* one of helper/util/data/manager/...
   is banned, but compounds are fine (``data_loader``, ``user_helper``).
2. Banned tokens anywhere: ``new``/``old``/``tmp``/``temp`` are rejected wherever
   they appear as a word in an identifier -- ``new_data``, ``data_new`` and the
   variable ``new_car`` are all flagged, because they name *when/which version*
   rather than *what*. Matching is token-wise (split on ``_`` and camelCase), so
   ``renew``, ``news`` and ``template`` are fine.
3. No single-underscore prefix at module level: in a service, nothing imports
   your modules from outside, so ``_configure`` vs ``configure`` distinguishes
   nothing -- it is reflexive noise. The underscore conventions that DO carry
   meaning (https://dbader.org/blog/meaning-of-underscores-in-python) stay
   allowed: ``self._attr`` inside a class, ``__dunder__`` protocol names,
   trailing ``class_`` to dodge a keyword, and the bare ``_`` throwaway.
   Module *filenames* follow the same rule (``_common.py`` is rejected;
   ``__init__.py`` is protocol).

The banned-name lists come from .project-conventions.yaml (naming.banned_when_alone
+ naming.extra_banned, and naming.banned_tokens). snake_case / PascalCase / casing
itself is enforced separately by ruff's pep8-naming (N) rules.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from common import (
    banned_names,
    banned_tokens,
    changed_line_numbers,
    changed_python_files,
    fail,
)

WORD_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+")

DUNDER_FILES = {"__init__.py", "__main__.py"}


def tokens(name: str) -> list[str]:
    """Split an identifier into lowercase word tokens (snake_case + camelCase)."""
    out: list[str] = []
    for part in name.strip("_").split("_"):
        out += WORD_RE.findall(part)
    return [t.lower() for t in out if t]


def is_dunder(name: str) -> bool:
    return name.startswith("__") and name.endswith("__")


def iter_defined_names(tree: ast.AST) -> Iterator[tuple[str, int, str]]:
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


def iter_module_level_names(tree: ast.Module) -> Iterator[tuple[str, int, str]]:
    """Yield (identifier, lineno, kind) for names defined at module scope only."""
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node.name, node.lineno, "function"
        elif isinstance(node, ast.ClassDef):
            yield node.name, node.lineno, "class"
        elif isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    yield tgt.id, tgt.lineno, "name"
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            yield node.target.id, node.target.lineno, "name"


@dataclass
class NameRules:
    """The configured rule inputs plus the per-file changed-line filter."""

    path: Path
    alone: set[str]
    anywhere: set[str]
    treat_whole_file: bool
    changed: set[int]

    def in_scope(self, lineno: int) -> bool:
        return self.treat_whole_file or lineno in self.changed

    def banned_violation(self, name: str, lineno: int, kind: str) -> str | None:
        if is_dunder(name) or not self.in_scope(lineno):
            return None
        parts = tokens(name)
        hit = self.anywhere.intersection(parts)
        if hit:
            word = sorted(hit)[0]
            return (
                f"{self.path}:{lineno} {kind} '{name}' contains '{word}'; name it "
                f"for what it holds, not when/which version (string keys are exempt)"
            )
        if len(parts) == 1 and parts[0] in self.alone:
            return f"{self.path}:{lineno} {kind} '{name}' is too vague on its own"
        return None

    def underscore_violation(self, name: str, lineno: int, kind: str) -> str | None:
        if not name.startswith("_") or is_dunder(name) or name == "_":
            return None
        if not self.in_scope(lineno):
            return None
        return (
            f"{self.path}:{lineno} module-level {kind} '{name}': drop the "
            f"leading underscore -- in a service nothing imports this from "
            f"outside, so '_internal' marks nothing (single underscore is for "
            f"class-internal attributes only)"
        )


def check_file(path: Path, alone: set[str], anywhere: set[str]) -> list[str]:
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return []
    changed = changed_line_numbers(path)
    rules = NameRules(
        path=path,
        alone=alone,
        anywhere=anywhere,
        treat_whole_file=not changed,
        changed=changed,
    )
    out = [
        msg
        for name, lineno, kind in iter_defined_names(tree)
        if (msg := rules.banned_violation(name, lineno, kind))
    ]
    out += [
        msg
        for name, lineno, kind in iter_module_level_names(tree)
        if (msg := rules.underscore_violation(name, lineno, kind))
    ]
    if path.name.startswith("_") and path.name not in DUNDER_FILES:
        out.append(
            f"{path}: module filename starts with '_' -- name modules plainly "
            f"(only {', '.join(sorted(DUNDER_FILES))} carry a protocol meaning)"
        )
    return out


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
