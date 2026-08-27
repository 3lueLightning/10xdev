"""Legacy module the team wrote before any tooling existed.

Deliberately packs several unrelated violations into one small file so the
retrofit fixture surfaces them all in a single `task ci-check` run:
module-level mutable state, a banned name token, os.getenv() outside the
settings module, an untyped signature, and an underscore-prefixed /
vague-alone helper name.
"""

import os

cache = {}
new_value = 1


def process(x):
    os.getenv("SOME_KEY")
    cache["x"] = x
    return x


def _helper():
    return 1
