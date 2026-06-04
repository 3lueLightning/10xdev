"""End-to-end: render.py produces a correct tree for several answer sets."""
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
RENDER = ROOT / "skills" / "project-scaffold" / "scripts" / "render.py"


def _render(tmp_path, answers: dict) -> Path:
    a = tmp_path / "answers.yaml"
    a.write_text(yaml.safe_dump(answers))
    subprocess.run([sys.executable, str(RENDER), "--answers", str(a),
                    "--dest", str(tmp_path)], check=True)
    return tmp_path / answers["project_name"]


def test_no_placeholder_leftovers_and_single_package(tmp_path):
    p = _render(tmp_path, {"project_name": "trip-planner", "python_version": "3.12",
                           "api": "rest", "prompt_management": "yaml only"})
    # the import package is named, deh-yphenated, exactly once under src/
    assert (p / "src" / "trip_planner").is_dir()
    assert not list(p.rglob("*__pkg__*"))
    for f in p.rglob("*"):
        if f.is_file():
            assert "{{" not in f.read_text(errors="ignore"), f


def test_no_invalid_path_chars(tmp_path):
    p = _render(tmp_path, {"project_name": "doc-ai", "python_version": "3.12",
                           "api": "none", "prompt_management": "yaml only"})
    assert not [x for x in p.rglob("*") if "{" in x.name or "}" in x.name]


def test_prompts_inside_package(tmp_path):
    p = _render(tmp_path, {"project_name": "alpha", "python_version": "3.12",
                           "api": "rest", "prompt_management": "yaml only"})
    assert (p / "src" / "alpha" / "prompts" / "example.yaml").exists()
    assert not (p / "prompts").exists()  # no root-level prompts


def test_api_none_drops_api(tmp_path):
    p = _render(tmp_path, {"project_name": "beta", "python_version": "3.12",
                           "api": "none", "prompt_management": "yaml only"})
    assert not (p / "src" / "beta" / "api").exists()
    assert "fastapi" not in (p / "pyproject.toml").read_text()


def test_langfuse_drops_prompts_adds_sdk(tmp_path):
    p = _render(tmp_path, {"project_name": "gamma", "python_version": "3.12",
                           "api": "rest", "prompt_management": "langfuse",
                           "llm_providers": "openai, google"})
    assert not (p / "src" / "gamma" / "prompts").exists()
    txt = (p / "pyproject.toml").read_text()
    assert "langfuse" in txt and "google-genai" in txt and "openai" in txt


def test_readme_in_every_dir(tmp_path):
    p = _render(tmp_path, {"project_name": "delta", "python_version": "3.12",
                           "api": "rest", "prompt_management": "yaml only"})
    for d in (p, p / "src", p / "src" / "delta", p / "src" / "delta" / "config",
              p / "tests", p / "notebooks"):
        assert (d / "README.md").exists(), d


def test_python_version_pinned(tmp_path):
    p = _render(tmp_path, {"project_name": "epsilon", "python_version": "3.12",
                           "api": "none", "prompt_management": "yaml only"})
    assert (p / ".python-version").read_text().strip() == "3.12"
    assert ">=3.12" in (p / "pyproject.toml").read_text()


def test_conventions_written(tmp_path):
    p = _render(tmp_path, {"project_name": "zeta", "python_version": "3.12",
                           "api": "rest", "prompt_management": "yaml only",
                           "llm_providers": "anthropic"})
    conv = yaml.safe_load((p / ".project-conventions.yaml").read_text())
    assert conv["project"]["package"] == "zeta"
    assert conv["genai"]["llm_providers"] == ["anthropic"]
    assert conv["naming"]["banned_tokens"] == ["new", "old", "tmp", "temp"]
