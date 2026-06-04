# `core/` — business logic

The domain logic of the project: the functions and classes that do the actual
work, independent of how they are triggered (API, CLI, notebook). Keep I/O and
framework code at the edges (`api/`, `llm/`) so this stays easy to test.
