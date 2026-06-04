"""Load prompts from packaged YAML into validated pydantic models.

Prompts live as YAML *inside this package* (next to this module), so they ship
with the wheel and resolve correctly inside a container regardless of the working
directory -- loaded via importlib.resources, never a filesystem path relative to
the repo root. A typo in a prompt file fails loudly here at load time instead of
mysteriously at inference time.

If a prompt manager (Langfuse/Langsmith) is enabled in Settings, fetch from there
and fall back to these YAML files; that wiring lives in the llm/ layer.
"""

from __future__ import annotations

from importlib import resources

import yaml
from pydantic import BaseModel


class PromptConfig(BaseModel):
    name: str
    system: str
    user_template: str
    description: str = ""


def load_prompt(name: str) -> PromptConfig:
    """Load and validate a prompt by file stem (e.g. 'example')."""
    source = resources.files(__package__).joinpath(f"{name}.yaml")
    raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    return PromptConfig(**raw)
