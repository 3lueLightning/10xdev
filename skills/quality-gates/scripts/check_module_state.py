#!/usr/bin/env python3
"""Forbid mutable module-level state (a "no global variables" rule).

Allowed at module scope: imports, function/class defs, dunders, and immutable
constants -- UPPER_CASE names and/or `Final`-annotated names. Flagged: a
module-level name bound to a mutable literal (list/dict/set) or whose value is
mutated, which is the kind of global state that breaks tests and concurrency.
Use the Settings singleton or dependency injection instead.

The `global` keyword itself is banned by ruff (PLW0603); this catches the case
ruff cannot see -- a mutable defined and mutated at module level.
"""

from __future__ import annotations

import ast
from pathlib import Path

from _common import changed_line_numbers, changed_python_files, fail

MUTABLE_NODES = (ast.List, ast.Dict, ast.Set, ast.ListComp, ast.DictComp, ast.SetComp)


def _is_constish(name: str) -> bool:
    return name.isupper() or name.startswith("__")


def check_file(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return []
    changed = changed_line_numbers(path)
    treat_whole_file = not changed
    out: list[str] = []
    for node in tree.body:  # module level only
        targets: list[ast.expr] = []
        value: ast.expr | None = None
        is_final = False
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
            is_final = "Final" in ast.dump(node.annotation)
        else:
            continue
        if is_final:
            continue
        for tgt in targets:
            if not isinstance(tgt, ast.Name) or _is_constish(tgt.id):
                continue
            if isinstance(value, MUTABLE_NODES) and (treat_whole_file or tgt.lineno in changed):
                out.append(
                    f"{path}:{tgt.lineno} module-level mutable '{tgt.id}' "
                    f"-- move into Settings or a function, or make it a constant"
                )
    return out


def main() -> int:
    messages: list[str] = []
    for path in changed_python_files():
        messages.extend(check_file(path))
    return fail(messages, "Mutable module-level (global) state is not allowed.")


if __name__ == "__main__":
    raise SystemExit(main())
