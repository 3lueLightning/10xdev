# Manual test — quality-gates

Goal: prove the gate **passes clean code** and **catches one violation per check**,
end-to-end, in a real scaffolded sandbox with git history (so the changed-line
diff plumbing in `common.py` is exercised, not just the AST logic).

Run from the 10xdev repo root. `$QG` points at this repo's scripts.

```bash
export QG="$(git rev-parse --show-toplevel)/skills/quality-gates/scripts"
export SANDBOX="$(mktemp -d)/probe"
```

## 0. Preflight

- [ ] `uv --version` succeeds
- [ ] `task --version` succeeds

## 1. Scaffold + apply (the happy path)

```bash
cat > /tmp/answers.yaml <<'EOF'
project_name: probe
python_version: "3.13"
api: rest
git_status: "git, I have admin"
forge: github
llm_providers: anthropic
prompt_management: yaml only
EOF
uv run "$(git rev-parse --show-toplevel)/skills/project-scaffold/scripts/render.py" \
  --answers /tmp/answers.yaml --dest "$(dirname "$SANDBOX")"
cd "$SANDBOX"
git init -q && git config user.email t@t && git config user.name t
uv run "$QG/apply.py" --dest .
git add -A && git commit -qm "scaffold"
```

- [ ] `ci_pipeline/` contains the six `check_*.py` + `common.py` (not `scripts/`)
- [ ] `ruff.toml` has `target-version = "py313"`
- [ ] `.github/workflows/ci-check.yml` exists
- [ ] Re-running `uv run "$QG/apply.py" --dest .` does **not** clobber
      `.codespell-ignore.txt` (idempotency)

## 2. Clean code passes (POSITIVE)

```bash
task setup
task ci-check
```

- [ ] `task ci-check` exits 0 on the untouched scaffold

## 3. One violation per check (NEGATIVE)

For each: make the change on a **new commit/branch** so it shows as *changed*,
run just that check, confirm non-zero exit + the right message, then revert.

| Check | Inject | Expect |
|---|---|---|
| `check_changed_signatures.py --strict` | add `def f(x): return x` to a src file | flags untyped arg + missing return |
| `check_banned_names.py` | add `new_data = 1` at module level | flags banned token `new` |
| `check_banned_names.py` | rename a module fn to `_helper` | flags underscore-prefix + vague-alone |
| `check_module_state.py` | add `cache = {}` at module level | flags mutable module state |
| `check_load_dotenv.py` | add `import os; os.getenv("X")` outside settings | flags getenv outside settings |
| `check_root_scripts.py` | `touch run_me.py && git add run_me.py` | flags script at repo root |
| `check_sizes.py` | paste a 160-line function into a src file | fails on function length |

Run pattern:
```bash
# after injecting + `git add -A` (do NOT commit; staged shows as changed)
uv run python ci_pipeline/check_banned_names.py; echo "exit=$?"
git checkout -- . && git clean -fdq   # revert
```

- [ ] each check exits non-zero **only** for its own violation
- [ ] `check_changed_signatures` without `--strict` is advisory (exit 0)

## 4. Escape hatch behaves

- [ ] `git commit --no-verify` bypasses local hooks (documented, expected)
- [ ] but `task ci-check` (what CI runs) still fails → CI is the real gate

## Cleanup
```bash
rm -rf "$(dirname "$SANDBOX")"
```

---

## → How each row becomes an automated test

Every manual step above maps to pytest, in two tiers:

- **Tier 1 (fast, no git):** call `check_file()` directly on a `tmp_path`
  fixture. Empty changed-set ⇒ whole file treated as changed. Good file → `[]`,
  bad file → one message. This is the real entrypoint (unlike `test_naming`'s
  reimplemented walk).
- **Tier 2 (integration):** build a real git repo in `tmp_path`, stage a bad
  diff, run the script's `main()` via `subprocess`, assert exit code + stderr.
  This is the only tier that covers the `common.py` diff plumbing.

Section 1–2 are already partly covered by `test_apply.py`; sections 3–4 are the
gap.
