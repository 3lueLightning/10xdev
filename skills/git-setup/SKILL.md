---
name: git-setup
description: Configure git branch model and protection for a project when the user has admin rights on the remote. Sets up a main + dev branch model, applies branch-protection rules (require PR, require the ci-check status check, no force-push/deletion) via the gh / glab / tea CLI when available, and always writes docs/REPO-SETUP.md as a manual handoff fallback. Supports GitHub, GitLab, Bitbucket, and Gitea. Use when the user wants to set up branch protection, enforce pull-request workflows, configure main/dev branches, require CI to pass before merge, or "lock down the repo". Called by project-scaffold only when the user confirms admin rights; also runnable standalone. Never creates accounts or changes permissions the user lacks rights for.
---

# Git Setup

Configure the branch model and protection rules for a repository. Run this only
when the user has admin rights on the remote (or can configure it). If they
don't, skip — `project-scaffold` already sets up everything *local* (hooks, CI
workflow files), and protection can be applied later by someone with admin.

## What this enforces

A `main` + `dev` model where both branches are protected and changes land via
PR, with the `ci-check` workflow required to pass. CI is the authoritative gate:
local hooks are fast feedback, but a PR cannot merge if `ci-check` fails.

## Workflow

### 1. Detect state

- `git rev-parse --show-toplevel` to confirm a repo (run `git init` if the user
  is starting fresh and wants local git now).
- `git remote -v` to read the remote and infer the forge (github.com,
  gitlab.com/self-hosted, bitbucket.org, or a Gitea host). If unclear, ask, or
  read `git.forge` from `.project-conventions.yaml`.
- Confirm the user actually has admin on this remote before attempting changes.
  If they're unsure, proceed only as far as creating branches + writing the
  handoff doc.

### 2. Create the branch model

Ensure `main` and `dev` exist:

```bash
git rev-parse --verify main  || git branch -M main
git rev-parse --verify dev   || git branch dev
git push -u origin main dev   # if a remote exists
```

Feature work happens on `feature/*` branches off `dev`.

### 3. Apply protection (if a CLI is authenticated)

Check for the forge's CLI and that it's authenticated:

- GitHub → `gh auth status`
- GitLab → `glab auth status`
- Gitea → `tea login list`
- Bitbucket → no first-party CLI; go straight to the handoff doc.

If authenticated, apply protection to **both** `main` and `dev` using the payload
in `templates/branch_protection/<forge>.json`. The commands are in
`templates/REPO-SETUP.md`. Require the `ci-check` status check, require a PR with
at least one approval, and disallow force-push and deletion.

**Never** do anything that needs rights the user lacks. Changing access controls
or sharing settings is out of scope — this skill only configures branch
protection and the branch model. If a command fails on permissions, stop and
fall back to the handoff doc.

### 4. Always write the handoff doc

Copy `templates/REPO-SETUP.md` to `docs/REPO-SETUP.md` (and the
`branch_protection/` payloads alongside it). Substitute `{owner}`/`{repo}` where
you can. This is the deliverable whether or not the CLI applied the rules — it
lets a repo owner finish the job in five minutes, or serves as a record if it's
already done. Commit it.

### 5. Report

Tell the user which branches exist, whether protection was applied
automatically or needs a hand-off, and where `docs/REPO-SETUP.md` is.

## Boundaries

- Do not create accounts or authorize password-based access — direct the user to
  do those themselves.
- SSO/OAuth login flows for an existing account may be completed only with the
  user's explicit go-ahead in the chat.
- One repo per project; this skill assumes a single remote.
