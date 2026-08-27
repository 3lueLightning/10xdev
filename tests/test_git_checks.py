"""Tier-2 integration: run the checks against a REAL git repo via subprocess.

This is the only tier that exercises common.py's git plumbing -- base_ref(),
changed_python_files() and changed_line_numbers() -- which every check depends
on and which the Tier-1 tests deliberately stub out. Running each script as a
subprocess (cwd = the temp repo) mirrors exactly how the hooks invoke them in a
user's project: `python ci_pipeline/<check>.py` with the script's own directory
on sys.path so `from common import ...` resolves.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "quality-gates" / "scripts"


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def make_repo(tmp_path: Path) -> Path:
    git(tmp_path, "init")
    git(tmp_path, "config", "user.email", "t@t")
    git(tmp_path, "config", "user.name", "t")
    return tmp_path


def run_check(repo: Path, script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        cwd=repo,
        capture_output=True,
        text=True,
    )


# --------------------------------------------------------------------------- #
# check_root_scripts -- purely git-driven (ls-files / staged)
# --------------------------------------------------------------------------- #
def test_root_script_is_flagged(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "run_me.py").write_text("print('hi')\n")
    git(repo, "add", "run_me.py")
    result = run_check(repo, "check_root_scripts.py")
    assert result.returncode == 1
    assert "run_me.py" in result.stderr


def test_no_root_script_is_clean(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "README.md").write_text("# hi\n")
    git(repo, "add", "README.md")
    result = run_check(repo, "check_root_scripts.py")
    assert result.returncode == 0


# --------------------------------------------------------------------------- #
# changed-lines behaviour: the crown jewel of common.py. A pre-existing untyped
# function must NOT block; a newly-added one MUST. This proves base_ref() and
# changed_line_numbers() actually scope findings to the diff.
# --------------------------------------------------------------------------- #
def test_changed_signatures_only_flags_new_code(tmp_path):
    repo = make_repo(tmp_path)
    src = repo / "src"
    src.mkdir()

    # Baseline on `dev`: a pre-existing untyped function (must be tolerated).
    (src / "existing_mod.py").write_text("def existing(a):\n    return a\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-m", "baseline")
    git(repo, "branch", "-M", "dev")

    # Feature branch: add a NEW untyped function (must be flagged).
    git(repo, "checkout", "-q", "-b", "feature")
    (src / "added_mod.py").write_text("def added(b):\n    return b\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-m", "feature")

    result = run_check(repo, "check_changed_signatures.py", "--strict")
    assert result.returncode == 1
    assert "added" in result.stderr
    assert "existing" not in result.stderr  # untouched pre-existing code is not gated
