# `tests/` — pytest suite

Relaxed sandbox: lint, typing, size, and dependency-hygiene gates do **not**
apply here, so test code can be pragmatic. Secret scanning still runs. Mirror the
package layout (`tests/test_core.py` for `core/`) and use `conftest.py` for
shared fixtures.
