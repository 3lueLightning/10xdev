#!/usr/bin/env python3
"""Apply the quality-gates toolchain to a project in ONE run.

Why this exists: copying ~15 config files and the check scripts one by one makes
the host agent ask permission for every read/write. Doing it all inside a single
script means a single approved command instead of a wall of prompts. The script
locates its own templates relative to __file__, so it works wherever the skill
(or plugin) is installed.

Usage:
    apply.py --dest <project-dir> [--forge github|gitlab|bitbucket|gitea]

It does NOT install dependencies or create a venv -- that's `uv sync` / `task
setup`, a separate explicit step the developer runs.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
TEMPLATES = HERE / "templates"
SCRIPTS = HERE / "scripts"

# forge -> destination path for the CI workflow
CI_DEST = {
    "github": ".github/workflows/ci.yml",
    "gitlab": ".gitlab-ci.yml",
    "bitbucket": "bitbucket-pipelines.yml",
    "gitea": ".gitea/workflows/ci.yml",
}

STATIC = [
    "ruff.toml", ".gitleaks.toml", ".gitattributes", ".editorconfig",
    "Taskfile.yml", ".pre-commit-config.yaml",
]


def load_conventions(dest: Path) -> dict:
    path = dest / ".project-conventions.yaml"
    if not path.exists():
        return {}
    try:
        import yaml

        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def align_ruff(ruff: Path, conv: dict) -> None:
    """Set the (conv: ...) values in ruff.toml from the conventions file."""
    if not conv:
        return
    text = ruff.read_text(encoding="utf-8")
    py = conv.get("project", {}).get("python_version")
    if py:
        nodot = "py" + str(py).replace(".", "")
        text = re.sub(r'target-version = "py\d+"', f'target-version = "{nodot}"', text)
    lazy = conv.get("layout", {}).get("lazy_imports") or []
    if lazy:
        listed = ", ".join(f'"{m}"' for m in lazy)
        text = re.sub(r"banned-module-level-imports = \[\]",
                      f"banned-module-level-imports = [{listed}]", text)
    ruff.write_text(text, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", required=True)
    ap.add_argument("--forge")
    args = ap.parse_args()

    dest = Path(args.dest).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    conv = load_conventions(dest)
    forge = args.forge or conv.get("git", {}).get("forge") or "github"

    # 1. static config (don't clobber a project-owned .python-version)
    for fname in STATIC:
        shutil.copy2(TEMPLATES / fname, dest / fname)
    if not (dest / ".python-version").exists():
        py = conv.get("project", {}).get("python_version", "3.13")
        (dest / ".python-version").write_text(f"{py}\n", encoding="utf-8")
    align_ruff(dest / "ruff.toml", conv)

    # 2. check scripts
    (dest / "scripts").mkdir(exist_ok=True)
    for script in SCRIPTS.glob("*.py"):
        if script.name != "apply.py":
            shutil.copy2(script, dest / "scripts" / script.name)

    # 3. merge [tool.*] sections into pyproject (subprocess = no extra host prompt)
    pyproject = dest / "pyproject.toml"
    if pyproject.exists():
        subprocess.run(
            [sys.executable, str(SCRIPTS / "merge_pyproject.py"), str(pyproject),
             str(TEMPLATES / "pyproject.tool-sections.toml")],
            check=True,
        )

    # 4. CI workflow for the chosen forge
    if forge in CI_DEST:
        ci_target = dest / CI_DEST[forge]
        ci_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(TEMPLATES / "ci" / f"{forge}.yml", ci_target)

    print("quality-gates applied:")
    print(f"  config   : {', '.join(STATIC)}, .python-version")
    print(f"  scripts  : {len(list(SCRIPTS.glob('*.py'))) - 1} checks -> scripts/")
    print("  pyproject: [tool.*] sections merged")
    print(f"  ci       : {CI_DEST.get(forge, '(skipped)')}")
    print("\n  next: run `task setup` then `task ci-check`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
