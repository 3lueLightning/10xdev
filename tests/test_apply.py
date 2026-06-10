"""End-to-end: apply.py installs the gate toolchain onto a rendered project."""

import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
RENDER = ROOT / "skills" / "project-scaffold" / "scripts" / "render.py"
APPLY = ROOT / "skills" / "quality-gates" / "scripts" / "apply.py"


def _scaffold_with_gates(tmp_path: Path) -> Path:
    answers = tmp_path / "answers.yaml"
    answers.write_text(
        yaml.safe_dump(
            {
                "project_name": "probe",
                "python_version": "3.13",
                "api": "rest",
                "git_status": "git, I have admin",
                "forge": "github",
                "prompt_management": "yaml only",
            }
        )
    )
    project = tmp_path / "probe"
    subprocess.run(
        [sys.executable, str(RENDER), "--answers", str(answers), "--dest", str(tmp_path)],
        check=True,
    )
    subprocess.run([sys.executable, str(APPLY), "--dest", str(project)], check=True)
    return project


def test_checks_land_in_ci_pipeline_not_scripts(tmp_path):
    p = _scaffold_with_gates(tmp_path)
    assert (p / "ci_pipeline" / "check_banned_names.py").exists()
    assert (p / "ci_pipeline" / "check_root_scripts.py").exists()
    assert (p / "ci_pipeline" / "common.py").exists()
    assert (p / "ci_pipeline" / "README.md").exists()
    # scripts/ stays the user's sandbox: only the README from the scaffold
    assert [f.name for f in (p / "scripts").iterdir()] == ["README.md"]


def test_ruff_target_aligned_and_ci_named_after_status_check(tmp_path):
    p = _scaffold_with_gates(tmp_path)
    assert 'target-version = "py313"' in (p / "ruff.toml").read_text()
    assert (p / ".github" / "workflows" / "ci-check.yml").exists()


def test_codespell_dictionary_seeded_but_never_overwritten(tmp_path):
    p = _scaffold_with_gates(tmp_path)
    dictionary = p / ".codespell-ignore.txt"
    assert dictionary.exists()
    dictionary.write_text("genai\n")
    subprocess.run([sys.executable, str(APPLY), "--dest", str(p)], check=True)
    assert dictionary.read_text() == "genai\n"


def test_tool_sections_merged_preserving_deptry_seed(tmp_path):
    p = _scaffold_with_gates(tmp_path)
    pyproject = (p / "pyproject.toml").read_text()
    assert "[tool.codespell]" in pyproject
    assert "uvicorn" in pyproject  # render's DEP002 seed survives the merge
