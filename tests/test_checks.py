"""Tier-1 unit tests: each check's REAL check_file() against fixtures.

No git is involved. The checks that consult the diff read line numbers via
``changed_line_numbers``; here it is monkeypatched to return an empty set, which
every check treats as "the whole file is new", so all lines are in scope. That
lets us drive the actual entrypoint on a tmp_path fixture -- unlike
test_naming.py, which reimplements the AST walk and so never exercises the real
code path.

Each check gets a positive (clean input -> no findings) and a negative (one
planted violation -> flagged) case, which is the same good/bad pattern the
manual protocol in tests/manual/quality-gates.md uses.
"""

import textwrap
from pathlib import Path

import check_banned_names as cbn
import check_changed_signatures as sigs
import check_load_dotenv as dotenv
import check_module_state as mod_state
import check_sizes as sizes


def write(tmp_path: Path, name: str, src: str) -> Path:
    p = tmp_path / name
    p.write_text(textwrap.dedent(src))
    return p


def whole_file_changed(monkeypatch, module) -> None:
    """Force the check to treat every line as changed (no git needed)."""
    monkeypatch.setattr(module, "changed_line_numbers", lambda path: set())


# --------------------------------------------------------------------------- #
# check_changed_signatures
# --------------------------------------------------------------------------- #
def test_untyped_signature_flagged(tmp_path, monkeypatch):
    whole_file_changed(monkeypatch, sigs)
    p = write(tmp_path, "m.py", "def f(x):\n    return x\n")
    msgs = sigs.check_file(p)
    assert any("not typed" in m for m in msgs)
    assert any("no return type" in m for m in msgs)


def test_typed_signature_clean(tmp_path, monkeypatch):
    whole_file_changed(monkeypatch, sigs)
    p = write(tmp_path, "m.py", "def f(x: int) -> int:\n    return x\n")
    assert sigs.check_file(p) == []


def test_self_exempt_and_return_typed_clean(tmp_path, monkeypatch):
    whole_file_changed(monkeypatch, sigs)
    p = write(
        tmp_path,
        "m.py",
        """
        class C:
            def method(self) -> None:
                return None
        """,
    )
    assert sigs.check_file(p) == []


# --------------------------------------------------------------------------- #
# check_module_state
# --------------------------------------------------------------------------- #
def test_module_level_mutable_flagged(tmp_path, monkeypatch):
    whole_file_changed(monkeypatch, mod_state)
    p = write(tmp_path, "m.py", "cache = {}\n")
    assert any("module-level mutable 'cache'" in m for m in mod_state.check_file(p))


def test_const_final_and_local_mutable_ok(tmp_path, monkeypatch):
    whole_file_changed(monkeypatch, mod_state)
    p = write(
        tmp_path,
        "m.py",
        """
        from typing import Final

        REGISTRY = {}          # UPPER_CASE constant -> allowed
        SETTINGS: Final = {}   # Final-annotated -> allowed

        def f() -> None:
            local = {}         # function-local, not module state -> allowed
            local["k"] = 1
        """,
    )
    assert mod_state.check_file(p) == []


# --------------------------------------------------------------------------- #
# check_load_dotenv
# --------------------------------------------------------------------------- #
def test_getenv_outside_settings_flagged(tmp_path):
    p = write(tmp_path, "service.py", "import os\nx = os.getenv('X')\n")
    assert any("getenv" in m for m in dotenv.check_file(p, "config/settings.py"))


def test_load_dotenv_outside_settings_flagged(tmp_path):
    p = write(tmp_path, "service.py", "from dotenv import load_dotenv\nload_dotenv()\n")
    assert any("load_dotenv" in m for m in dotenv.check_file(p, "config/settings.py"))


def test_settings_module_is_exempt(tmp_path):
    settings = tmp_path / "config" / "settings.py"
    settings.parent.mkdir()
    settings.write_text("import os\nx = os.getenv('X')\n")
    assert dotenv.check_file(settings, "config/settings.py") == []


# --------------------------------------------------------------------------- #
# check_sizes
# --------------------------------------------------------------------------- #
FL = {"warn": 450, "fail": 600}
FUNC_L = {"warn": 100, "fail": 150}


def test_oversized_function_fails(tmp_path):
    body = "\n".join(f"    x{i} = {i}" for i in range(160))
    p = tmp_path / "m.py"
    p.write_text(f"def big() -> None:\n{body}\n")
    _, fails = sizes.check_file(p, FL, FUNC_L)
    assert any("big()" in f for f in fails)


def test_oversized_file_fails(tmp_path):
    p = tmp_path / "m.py"
    p.write_text("\n".join(f"x{i} = {i}" for i in range(12)) + "\n")
    _, fails = sizes.check_file(p, {"warn": 5, "fail": 10}, FUNC_L)
    assert any("lines" in f for f in fails)


def test_small_file_clean(tmp_path):
    p = write(tmp_path, "m.py", "def f() -> int:\n    return 1\n")
    warns, fails = sizes.check_file(p, FL, FUNC_L)
    assert warns == [] and fails == []


# --------------------------------------------------------------------------- #
# check_banned_names -- the REAL entrypoint (test_naming reimplements the walk)
# --------------------------------------------------------------------------- #
def test_banned_token_via_check_file(tmp_path, monkeypatch):
    whole_file_changed(monkeypatch, cbn)
    p = write(tmp_path, "m.py", "new_data = 1\n")
    assert any("new_data" in m for m in cbn.check_file(p, {"data"}, {"new"}))


def test_good_name_via_check_file(tmp_path, monkeypatch):
    whole_file_changed(monkeypatch, cbn)
    p = write(tmp_path, "m.py", "user_count = 1\n")
    assert cbn.check_file(p, {"data"}, {"new"}) == []


def test_underscore_filename_via_check_file(tmp_path, monkeypatch):
    whole_file_changed(monkeypatch, cbn)
    p = tmp_path / "_helper.py"
    p.write_text("x = 1\n")
    assert any("filename" in m for m in cbn.check_file(p, set(), set()))
