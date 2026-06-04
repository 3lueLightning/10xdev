#!/usr/bin/env python3
"""Print packages newly added to uv.lock vs the previous commit, one per line.

Feeds `task audit-new-deps`, which runs guarddog only on the new packages so the
slow supply-chain scan touches just what changed.
"""

from __future__ import annotations

import re
import subprocess

from _common import repo_root


def _names(blob: str) -> set[str]:
    # uv.lock is TOML with [[package]] tables; grab name = "..." entries.
    return set(re.findall(r'^\s*name\s*=\s*"([^"]+)"', blob, flags=re.MULTILINE))


def main() -> int:
    lock = repo_root() / "uv.lock"
    if not lock.exists():
        return 0
    current = _names(lock.read_text())
    prev_blob = subprocess.run(
        ["git", "show", "HEAD:uv.lock"], capture_output=True, text=True
    ).stdout
    previous = _names(prev_blob) if prev_blob else set()
    for name in sorted(current - previous):
        print(name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
