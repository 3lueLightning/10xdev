# `docs/` — documentation source

Markdown sources for the project documentation, built with
[MkDocs](https://www.mkdocs.org/) (material theme) and
[mkdocstrings](https://mkdocstrings.github.io/) for API reference generated
from docstrings.

- `task docs-serve` — preview locally with live reload.
- `task docs-build` — build the static site into `site/` (gitignored).

Add pages as `.md` files here and list them under `nav:` in `mkdocs.yml`.
