#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6", "tomlkit>=0.13"]
# ///
"""Materialise a GenAI project from the template in ONE pass.

This exists so scaffolding is a single approved action instead of dozens of
individual file writes (each of which would otherwise prompt for permission).
Given an answers file, it renders the whole tree, applies the conditional
drops (no API -> no api/; external prompt manager -> no prompts/), wires
dependencies into pyproject.toml, writes .project-conventions.yaml, and prints a
clear completion banner.

Run it with `uv run` -- the PEP 723 header above makes uv supply pyyaml and
tomlkit, so nothing needs to be pip-installed first:

    uv run render.py --answers answers.yaml --dest /path/to/parent
              [--templates DIR] [--conventions-default FILE]
    uv run render.py --print-python-default   # echo the dynamic "latest stable - 1"

Boilerplate (.gitignore, .env.example, __init__.py, settings, etc.) is always
written without asking -- it is not optional and there is nothing to decide.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from pathlib import Path

import tomlkit
import yaml

# --- provider -> distribution name -------------------------------------------
LLM_SDK = {
    "openai": "openai",
    "anthropic": "anthropic",
    "google": "google-genai",
    "gemini": "google-genai",
    "google-genai": "google-genai",
}
PROMPT_SDK = {"langfuse": "langfuse", "langsmith": "langsmith"}
EXTERNAL_PROMPT = set(PROMPT_SDK)


# --- helpers -----------------------------------------------------------------
def detect_python_default(fallback: str = "3.13") -> str:
    """Latest *stable* CPython minor known to uv, minus one (the safe default)."""
    try:
        out = subprocess.run(
            ["uv", "python", "list"], capture_output=True, text=True, timeout=20
        ).stdout
    except Exception:
        return fallback
    minors: set[tuple[int, int]] = set()
    for line in out.splitlines():
        # stable only: patch digits must be followed by '+variant' or platform '-',
        # so pre-releases like 3.15.0a8 are excluded.
        m = re.match(r"^cpython-(\d+)\.(\d+)\.(\d+)(\+\w+)?[\s-]", line.strip())
        if m:
            minors.add((int(m.group(1)), int(m.group(2))))
    if not minors:
        return fallback
    major, minor = sorted(minors)[-1]
    earlier = [mm for (MM, mm) in minors if MM == major and mm < minor]
    return f"{major}.{max(earlier)}" if earlier else fallback


def as_list(value: object) -> list[str]:
    """Normalise 'a, b' / ['a','b'] / 'none' / 'decide later' -> list[str]."""
    if value is None:
        return []
    items = value if isinstance(value, list) else str(value).split(",")
    out: list[str] = []
    for raw in items:
        token = str(raw).strip().lower()
        if token and token not in {"none", "decide later", "n/a", "-"}:
            out.append(token)
    return out


def substitute(text: str, repl: dict[str, str]) -> str:
    for key, val in repl.items():
        text = text.replace(key, val)
    return text


# --- core --------------------------------------------------------------------
def render_tree(
    templates: Path, dest: Path, pkg: str, repl: dict[str, str], *, drop: set[str]
) -> None:
    """Copy templates -> dest, substituting placeholders in paths and contents.

    `drop` holds package-relative directory names to skip (e.g. 'api', 'prompts').
    """
    for src in sorted(templates.rglob("*")):
        rel_parts = [substitute(p, {"__pkg__": pkg}) for p in src.relative_to(templates).parts]
        rel = Path(*rel_parts)
        # conditional drops: skip anything under src/<pkg>/<dropped-dir>/
        pkg_index = rel.parts.index(pkg) if pkg in rel.parts else -1
        if pkg_index >= 0 and len(rel.parts) > pkg_index + 1 and rel.parts[pkg_index + 1] in drop:
            continue
        target = dest / rel
        if src.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.write_text(substitute(src.read_text(encoding="utf-8"), repl), encoding="utf-8")
        except UnicodeDecodeError:
            shutil.copy2(src, target)  # binary (e.g. images): copy as-is


def wire_pyproject(path: Path, *, api: str, providers: list[str], prompt_mgr: str) -> None:
    doc = tomlkit.parse(path.read_text(encoding="utf-8"))
    deps = doc["project"]["dependencies"]
    declared = {re.split(r"[><=!~ \[]", str(d), maxsplit=1)[0].lower() for d in deps}

    def add(spec: str) -> None:
        if spec.split("[", 1)[0].lower() not in declared:
            deps.append(spec)
            declared.add(spec.split("[", 1)[0].lower())

    deptry_ignore: list[str] = []
    if api in {"rest", "rest+ws"}:
        add("fastapi>=0.110")
        add("uvicorn[standard]>=0.29")
        deptry_ignore.append("uvicorn")  # run via CLI, never imported
    for prov in providers:
        sdk = LLM_SDK.get(prov)
        if sdk:
            add(f"{sdk}>=0.1")
            deptry_ignore.append(sdk)  # llm/ wrappers don't import it yet
    if prompt_mgr in EXTERNAL_PROMPT:
        sdk = PROMPT_SDK[prompt_mgr]
        add(f"{sdk}>=2")
        deptry_ignore.append(sdk)

    if deptry_ignore:
        # Pre-seed the deptry ignore; quality-gates' non-destructive merge keeps it.
        tool = doc.setdefault("tool", tomlkit.table(is_super_table=True))
        deptry = tool.setdefault("deptry", tomlkit.table())
        per_rule = deptry.setdefault("per_rule_ignores", tomlkit.table())
        per_rule["DEP002"] = deptry_ignore
    path.write_text(tomlkit.dumps(doc), encoding="utf-8")


def write_conventions(
    default_file: Path, answers: dict, dest: Path, pkg: str, providers: list[str]
) -> list[str]:
    conv = yaml.safe_load(default_file.read_text(encoding="utf-8"))
    conv["project"].update(
        name=answers.get("project_name"),
        package=pkg,
        python_version=answers.get("python_version", "3.13"),
        api=answers.get("api", "rest"),
    )
    conv["git"].update(status=answers.get("git_status"), forge=answers.get("forge"))
    conv["genai"].update(
        llm_providers=providers,
        prompt_management=answers.get("prompt_management", "yaml only"),
        deployment_target=answers.get("deployment_target", "not yet"),
    )
    conv["quality"]["coverage_target"] = answers.get("coverage_target", "measure only")
    conv["naming"]["extra_banned"] = as_list(answers.get("extra_banned_names"))
    conv["layout"]["lazy_imports"] = as_list(answers.get("lazy_imports"))
    # free-text guidance for ai-project-guidance (AGENTS.md), if provided
    guidance = {k: answers[k] for k in ("domain_summary", "team_norms") if answers.get(k)}
    if guidance:
        conv["guidance"] = guidance
    # deferred = Phase-2 ids left at default
    deferred = [
        k
        for k in ("llm_providers", "prompt_management", "deployment_target", "coverage_target")
        if not answers.get(k)
        or str(answers.get(k)).strip().lower()
        in {"decide later", "not yet", "measure only", "yaml only"}
    ]
    conv["deferred"] = deferred
    (dest / ".project-conventions.yaml").write_text(
        yaml.safe_dump(conv, sort_keys=False, default_flow_style=False), encoding="utf-8"
    )
    return deferred


BANNER = r"""
   ____  _   _   _   ___ _____ ___  _   _   ___ ___    __    ____
  / _  )| | | | / | / _ \_   _/ _ \| | | | / __| __|  /  \  |  _ \
 ( (/ / | |_| || || (_) || || (_) | |_| | \__ \ _|  | () | |    /
  \____)|_____||_| \___/ |_| \___/|_____| |___/___|  \__/  |_|\_\

   project structure created  -  happy coding!
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--answers")
    ap.add_argument("--dest", help="parent directory the project folder is created in")
    ap.add_argument("--templates")
    ap.add_argument("--conventions-default", dest="conv_default")
    ap.add_argument("--print-python-default", action="store_true")
    args = ap.parse_args()

    if args.print_python_default:
        print(detect_python_default())
        return 0

    if not (args.answers and args.dest):
        ap.error("--answers and --dest are required unless --print-python-default")

    here = Path(__file__).resolve().parent.parent
    templates = Path(args.templates) if args.templates else here / "templates" / "genai"
    conv_default = (
        Path(args.conv_default) if args.conv_default else here / ".project-conventions.default.yaml"
    )

    answers = yaml.safe_load(Path(args.answers).read_text(encoding="utf-8")) or {}
    name = answers["project_name"]
    pkg = name.replace("-", "_")
    py = answers.get("python_version") or detect_python_default()
    answers["python_version"] = py
    providers = as_list(answers.get("llm_providers"))
    api = answers.get("api", "rest")
    prompt_mgr = str(answers.get("prompt_management", "yaml only")).strip().lower()

    drop: set[str] = set()
    if api == "none":
        drop.add("api")
    if prompt_mgr in EXTERNAL_PROMPT:
        drop.add("prompts")

    project_dir = Path(args.dest) / name
    repl = {"{{pkg}}": pkg, "{{project_name}}": name, "{{python_version}}": py}
    render_tree(templates, project_dir, pkg, repl, drop=drop)
    (project_dir / ".python-version").write_text(f"{py}\n", encoding="utf-8")
    wire_pyproject(
        project_dir / "pyproject.toml", api=api, providers=providers, prompt_mgr=prompt_mgr
    )
    deferred = write_conventions(conv_default, answers, project_dir, pkg, providers)

    print(BANNER)
    print(f"  package : {pkg}   python : {py}   api : {api}")
    prompts_label = f"external ({prompt_mgr})" if "prompts" in drop else "in-package YAML"
    print(f"  prompts : {prompts_label}")
    if providers:
        print(f"  llm     : {', '.join(providers)}")
    if deferred:
        print(f"  deferred (re-run to fill in): {', '.join(deferred)}")
    print(f"\n  created in: {project_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
