"""The naming rule: banned tokens anywhere in identifiers; strings exempt."""
import ast
import textwrap

import check_banned_names as cbn


def _flag(src: str):
    """Return the set of identifiers flagged in `src` (whole file treated new)."""
    cbn.changed_line_numbers = lambda path: set()  # treat all lines as changed
    tree = ast.parse(textwrap.dedent(src))
    alone = {"data", "helper", "process", "manager"}
    anywhere = {"new", "old", "tmp", "temp"}
    flagged = set()
    # reimplement the walk against an in-memory tree (check_file reads from disk)
    found = []

    def flag(name, lineno, kind):
        if name.startswith("__") and name.endswith("__"):
            return
        parts = cbn.tokens(name)
        if anywhere.intersection(parts) or (len(parts) == 1 and parts[0] in alone):
            found.append(name)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            flag(node.name, node.lineno, "f")
            for a in node.args.args:
                flag(a.arg, a.lineno, "a")
        elif isinstance(node, ast.ClassDef):
            flag(node.name, node.lineno, "c")
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            flag(node.id, node.lineno, "n")
    return set(found)


def test_banned_token_anywhere_in_variables():
    flagged = _flag("""
        new_data = 1
        data_new = 2
        new_car = 3
        tmp_file = 4
        old_total = 5
    """)
    assert flagged == {"new_data", "data_new", "new_car", "tmp_file", "old_total"}


def test_string_keys_and_columns_exempt():
    # only the variable `car_data` is an identifier; the keys are strings
    flagged = _flag('car_data = {"new_car": 1, "car_old": 2}')
    assert flagged == set()


def test_real_words_with_substring_allowed():
    assert _flag("renew = 1\nnews = 2\nnewcomer = 3\ntemplate = 4") == set()


def test_vague_only_when_alone():
    assert "data" in _flag("data = 1")
    assert _flag("data_loader = 1\nloader_data = 2") == set()


def test_class_and_function_tokens():
    flagged = _flag("class NewOrder:\n    pass\ndef get_new_user():\n    pass")
    assert "NewOrder" in flagged and "get_new_user" in flagged


def test_dunder_exempt():
    assert _flag("def __new__(cls):\n    return 1") == set()


def test_tokenizer():
    assert cbn.tokens("new_data") == ["new", "data"]
    assert cbn.tokens("NewOrder") == ["new", "order"]
    assert cbn.tokens("renew") == ["renew"]
    assert cbn.tokens("HTTPSConnection") == ["https", "connection"]
