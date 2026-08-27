"""merge_pyproject.py: adds missing [tool.*] tables without clobbering the
project's own values. This is the contract that keeps skill updates
non-destructive, so it deserves a direct test (test_apply only covers it
incidentally).
"""

import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MERGE = ROOT / "skills" / "quality-gates" / "scripts" / "merge_pyproject.py"


def test_merge_preserves_existing_and_adds_missing(tmp_path):
    target = tmp_path / "pyproject.toml"
    target.write_text('[tool.mypy]\npython_version = "3.11"\n')

    sections = tmp_path / "sections.toml"
    sections.write_text(
        '[tool.mypy]\n'
        'python_version = "3.13"\n'  # conflicts -> project's 3.11 must win
        "strict = true\n"  # missing -> should be added
        "\n[tool.bandit]\n"  # whole new section -> should be added
        'skips = ["B101"]\n'
    )

    subprocess.run(
        [sys.executable, str(MERGE), str(target), str(sections)],
        check=True,
        capture_output=True,
    )

    data = tomllib.loads(target.read_text())
    assert data["tool"]["mypy"]["python_version"] == "3.11"  # existing value kept
    assert data["tool"]["mypy"]["strict"] is True  # missing key added
    assert data["tool"]["bandit"]["skips"] == ["B101"]  # new section added
