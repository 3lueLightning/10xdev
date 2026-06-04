"""Shared helpers for the quality-gates check scripts.

Everything here is dependency-free (stdlib only) so the hooks run before the
project's own dependencies are guaranteed installed.
"""

from __future__ import annotations

import subprocess
import sys
from functools import lru_cache
from pathlib import Path

# ---------------------------------------------------------------------------
# Conventions
# ---------------------------------------------------------------------------

DEFAULT_CONVENTIONS: dict = {
    "quality": {
        "file_length": {"warn": 450, "fail": 600},
        "function_length": {"warn": 100, "fail": 150},
    },
    "naming": {
        # Vague ONLY when they are the whole name; compounds are fine
        # (data_loader, user_helper). The bare token is what's banned.
        "banned_when_alone": [
            "helper",
            "helpers",
            "util",
            "utils",
            "data",
            "manager",
            "handler",
            "process",
            "stuff",
            "thing",
            "foo",
            "bar",
            "baz",
        ],
        "extra_banned": [],
        # Banned as a *word anywhere* in an identifier: new_data, data_new,
        # new_car are all rejected -- they record when/which version, not what.
        # Only identifiers are checked, so string keys and dataframe columns
        # (car_data["new_car"]) are unaffected. A different word that merely
        # contains the letters (renew, news, template) is fine -- matching is
        # token-wise, not substring.
        "banned_tokens": ["new", "old", "tmp", "temp"],
    },
    "layout": {
        "settings_module": "config/settings.py",
        "relaxed_dirs": ["notebooks", "tests"],
    },
}


@lru_cache(maxsize=1)
def load_conventions(root: str | None = None) -> dict:
    """Read .project-conventions.yaml, falling back to built-in defaults.

    YAML is parsed with PyYAML if available; otherwise the defaults are used so
    the hooks never hard-fail on a missing optional dependency.
    """
    base = Path(root) if root else repo_root()
    path = base / ".project-conventions.yaml"
    parsed: dict = {}
    if path.exists():
        try:
            import yaml  # type: ignore

            parsed = yaml.safe_load(path.read_text()) or {}
        except Exception:
            parsed = {}
    return _deep_merge(DEFAULT_CONVENTIONS, parsed)


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def banned_names(conv: dict | None = None) -> set[str]:
    conv = conv or load_conventions()
    naming = conv.get("naming", {})
    names = list(naming.get("banned_when_alone", []))
    names += list(naming.get("extra_banned", []))
    return {n.strip().lower() for n in names if n.strip()}


def banned_tokens(conv: dict | None = None) -> set[str]:
    """Words rejected anywhere they appear as a token within an identifier."""
    conv = conv or load_conventions()
    naming = conv.get("naming", {})
    return {s.strip().lower() for s in naming.get("banned_tokens", []) if s.strip()}


# ---------------------------------------------------------------------------
# Git / filesystem
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def repo_root() -> Path:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(out.stdout.strip())
    except Exception:
        return Path.cwd()


def _git(*args: str) -> str:
    out = subprocess.run(["git", *args], capture_output=True, text=True)
    return out.stdout


def base_ref() -> str:
    """Best-effort merge base to diff against (origin/dev, dev, or HEAD)."""
    for ref in ("origin/dev", "dev", "origin/main", "main"):
        if _git("rev-parse", "--verify", "--quiet", ref).strip():
            mb = _git("merge-base", "HEAD", ref).strip()
            if mb:
                return mb
    return "HEAD"


def changed_python_files(staged_only: bool = False) -> list[Path]:
    """Python files added/modified vs the base ref (or staged index)."""
    if staged_only:
        names = _git("diff", "--cached", "--name-only", "--diff-filter=d")
    else:
        # Union of: committed-since-base, staged, unstaged, and untracked-new.
        names = _git("diff", "--name-only", "--diff-filter=d", base_ref(), "HEAD")
        names += "\n" + _git("diff", "--cached", "--name-only", "--diff-filter=d")
        names += "\n" + _git("diff", "--name-only", "--diff-filter=d")
        names += "\n" + _git("ls-files", "--others", "--exclude-standard")
    root = repo_root()
    seen: set[str] = set()
    files: list[Path] = []
    for name in names.splitlines():
        name = name.strip()
        if not name or name in seen or not name.endswith(".py"):
            continue
        seen.add(name)
        p = root / name
        if p.exists() and not is_relaxed(p):
            files.append(p)
    return files


def changed_line_numbers(path: Path) -> set[int]:
    """Line numbers in `path` that were added/modified vs the base ref.

    Returns an empty set meaning "treat the whole file as changed" only when no
    diff information is available (e.g. a brand-new untracked file).
    """
    rel = str(path.relative_to(repo_root()))
    diff = _git("diff", "--unified=0", base_ref(), "HEAD", "--", rel)
    diff += _git("diff", "--cached", "--unified=0", "--", rel)
    diff += _git("diff", "--unified=0", "--", rel)
    if not diff.strip():
        return set()  # caller decides; usually "whole file is new"
    lines: set[int] = set()
    for line in diff.splitlines():
        if line.startswith("@@"):
            # @@ -a,b +c,d @@   -> c..c+d-1 are the new lines
            try:
                plus = line.split("+", 1)[1].split(" ", 1)[0]
                start, _, count = plus.partition(",")
                start_i = int(start)
                count_i = int(count) if count else 1
                lines.update(range(start_i, start_i + max(count_i, 1)))
            except (ValueError, IndexError):
                continue
    return lines


def is_relaxed(path: Path) -> bool:
    conv = load_conventions()
    relaxed = conv.get("layout", {}).get("relaxed_dirs", [])
    parts = path.parts
    return any(d in parts for d in relaxed)


def fail(messages: list[str], header: str) -> int:
    if not messages:
        return 0
    print(f"\n✗ {header}", file=sys.stderr)
    for m in messages:
        print(f"  - {m}", file=sys.stderr)
    print("", file=sys.stderr)
    return 1
