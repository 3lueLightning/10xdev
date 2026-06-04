# `src/` — source layout marker

This directory is **not** a Python package and is never imported. It exists so
the importable package (`{{pkg}}/`) is *not* on `sys.path` just by virtue of
sitting in the repo root. That forces your tests and notebooks to import the
**installed** package (`uv sync` installs it editable), which is what runs in
production — so "works locally but missing from the wheel" bugs surface
immediately instead of in prod.

Do not put modules directly in `src/`. All code lives in `src/{{pkg}}/`.
Why the repeated name? `{{project_name}}/` (outer) is the *project* — pyproject,
tests, CI, notebooks, things that ship around the code. `src/{{pkg}}/` (inner)
is the *package* — the code that is imported and packaged. They are different
things that happen to share a name.
