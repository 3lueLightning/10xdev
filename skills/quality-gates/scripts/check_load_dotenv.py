#!/usr/bin/env python3
"""Allow load_dotenv() (and os.getenv) only in the settings module.

Configuration and secrets flow through ONE pydantic-settings object. Scattered
load_dotenv()/os.getenv() calls are the root of config sprawl, so they are
restricted to the settings module declared in .project-conventions.yaml.
"""

from __future__ import annotations

import ast
from pathlib import Path

from _common import changed_python_files, fail, load_conventions


def check_file(path: Path, settings_rel: str) -> list[str]:
    if str(path).replace("\\", "/").endswith(settings_rel):
        return []
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return []
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            name = getattr(fn, "attr", None) or getattr(fn, "id", None)
            if name == "load_dotenv":
                out.append(f"{path}:{node.lineno} load_dotenv() outside the settings module")
            if name == "getenv" or (isinstance(fn, ast.Attribute) and fn.attr == "getenv"):
                out.append(
                    f"{path}:{node.lineno} os.getenv() outside the settings module "
                    f"-- read config via Settings instead"
                )
    return out


def main() -> int:
    conv = load_conventions()
    settings_rel = conv.get("layout", {}).get("settings_module", "config/settings.py")
    messages: list[str] = []
    for path in changed_python_files():
        messages.extend(check_file(path, settings_rel))
    return fail(
        messages,
        f"Environment access belongs in {settings_rel} (the Settings object), "
        f"not scattered across modules.",
    )


if __name__ == "__main__":
    raise SystemExit(main())
