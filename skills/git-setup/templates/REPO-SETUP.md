# Repository setup — branch protection

This project uses a `main` + `dev` model. Both branches are protected; changes
land via pull request, and the `ci-check` workflow must pass before merge. This
is the **authoritative** gate — local hooks give fast feedback, but a PR cannot
merge if CI fails, regardless of what happened on anyone's machine.

If the `gh` / `glab` / `tea` CLI commands below were applied automatically, this
file is just a record. If not (e.g. no admin at setup time), hand this to whoever
owns the repo — it's a 5-minute job.

## Branch model

- `main` — production / releases. Protected. Merge only via PR from `dev`.
- `dev` — integration. Protected. Merge only via PR from feature branches.
- `feature/*` — where work happens.

## Required settings (both `main` and `dev`)

- Require a pull request before merging (≥1 approval recommended).
- Require status check **`ci-check`** to pass.
- Require branches to be up to date before merging.
- Disallow force-pushes and deletions.

## Apply via CLI

### GitHub (`gh`)
```bash
gh api -X PUT repos/{owner}/{repo}/branches/dev/protection \
  --input branch_protection/github.json
gh api -X PUT repos/{owner}/{repo}/branches/main/protection \
  --input branch_protection/github.json
```

### GitLab (`glab` / API)
```bash
glab api -X POST "projects/:id/protected_branches?name=dev&push_access_level=0&merge_access_level=30"
glab api -X POST "projects/:id/protected_branches?name=main&push_access_level=0&merge_access_level=30"
# Require pipeline success: Settings > Merge requests > "Pipelines must succeed".
```

### Bitbucket
Repository settings → Branch restrictions → add rules for `main` and `dev`:
prevent deletion, prevent force-push, require 1 approval, require successful
builds. (See `branch_protection/bitbucket.json` for the field values.)

### Gitea (`tea` / API — GitHub-compatible)
```bash
tea api -X POST repos/{owner}/{repo}/branch_protections \
  --input branch_protection/gitea.json   # repeat for main
```
