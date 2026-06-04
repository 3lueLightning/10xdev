# `prompts/` — prompt definitions

Prompts are versioned YAML files **inside the package** (so they ship in the
wheel and resolve inside a container) plus `loader.py`, which validates each file
into a `PromptConfig` via `importlib.resources`. A malformed prompt fails loudly
at load time, not mid-inference.

Add a prompt: drop `my_prompt.yaml` here, then `load_prompt("my_prompt")`.
If you adopt a prompt manager (Langfuse/Langsmith) later, fetch there and fall
back to these files from the `llm/` layer.
