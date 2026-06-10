---
name: git-setup
description: Configure git branch model and protection for a project when the user has admin rights on the remote. Creates the remote repository via the gh / glab / tea CLI when none exists yet, sets up a main + dev branch model, applies branch-protection rules (require PR, require the ci-check status check, no force-push/deletion), leaves the user checked out on dev so work never lands on main directly, and always writes .repo-config/REPO-SETUP.md as a manual handoff fallback. Supports GitHub, GitLab, Bitbucket, and Gitea. Use when the user wants to set up branch protection, enforce pull-request workflows, configure main/dev branches, require CI to pass before merge, create the project's remote repo, or "lock down the repo". Called by project-scaffold only when the user confirms admin rights; also runnable standalone. Never creates accounts or changes permissions the user lacks rights for.
---

# Git Setup

Configure the branch model and protection rules for a repository — including
creating the remote repository when the user has the rights and none exists
yet. Run this only when the user has admin rights on the remote (or can
configure it). If they don't, skip — `project-scaffold` already sets up
everything *local* (hooks, CI workflow files), and protection can be applied
later by someone with admin.

## What this enforces

A `main` + `dev` model where both branches are protected and changes land via
PR, with the `ci-check` workflow required to pass. CI is the authoritative gate:
local hooks are fast feedback, but a PR cannot merge if `ci-check` fails.

**The end state must make "accidentally pushed straight to main" impossible:**
the remote exists, protection is applied, and the working copy is left on `dev`.

## Workflow

### 1. Detect state

- `git rev-parse --show-toplevel` to confirm a repo (run `git init` if the user
  is starting fresh and wants local git now).
- `git remote -v` to read the remote and infer the forge (github.com,
  gitlab.com/self-hosted, bitbucket.org, or a Gitea host). If unclear, ask, or
  read `git.forge` from `.project-conventions.yaml`.
- Check the forge CLI is authenticated (`gh auth status` / `glab auth status` /
  `tea login list`). If it isn't, tell the user how to authenticate (e.g.
  `gh auth login`) and offer to continue once they have — don't silently fall
  through to the handoff doc while the user believes the repo is being created.

### 2. Create the remote repository (when none exists)

If the user said they have admin and there is **no remote yet**, don't stop at
local branches — create the repo with the forge CLI. Ask one question first:
**private or public** (default private). For GitHub:

```bash
gh repo create <project-name> --private --source=. --remote=origin
```

(GitLab: `glab repo create`; Gitea: `tea repo create`. Bitbucket has no
first-party CLI — write the handoff doc and tell the user explicitly the repo
was NOT created.)

Make sure at least one commit exists first (`git add -A && git commit` the
scaffold if needed) so branches can be pushed.

### 3. Create the branch model

Ensure `main` and `dev` exist and reach the remote:

```bash
git rev-parse --verify main  || git branch -M main
git rev-parse --verify dev   || git branch dev
git push -u origin main dev   # if a remote exists
```

Feature work happens on `feature/*` branches off `dev`.

### 4. Apply protection

If the CLI is authenticated, apply protection to **both** `main` and `dev`
using the payload in `templates/branch_protection/<forge>.json`. The commands
are in `templates/REPO-SETUP.md`. Require the `ci-check` status check, require
a PR with at least one approval, and disallow force-push and deletion.

**Never** do anything that needs rights the user lacks. Changing access controls
or sharing settings is out of scope — this skill only configures branch
protection and the branch model. If a command fails on permissions, stop and
fall back to the handoff doc.

### 5. Leave the working copy on `dev`

```bash
git checkout dev
```

Always end here, even when protection could not be applied — it's the local
half of "nothing lands on main directly". From now on, pushes go to `dev` (or a
`feature/*` branch); `main` only moves by PR. If the user later asks you to
push and the current branch is `main`, switch to `dev` or a feature branch
first and say why — never push work directly to `main`.

### 6. Always write the handoff doc

Copy `templates/REPO-SETUP.md` to `.repo-config/REPO-SETUP.md` (and the
`branch_protection/` payloads alongside it, i.e.
`.repo-config/branch_protection/<forge>.json`). Substitute `{owner}`/`{repo}`
where you can. This folder is repository *configuration*, deliberately kept out
of `docs/` (which belongs to the MkDocs site). The doc is the deliverable
whether or not the CLI applied the rules — it lets a repo owner finish the job
in five minutes, or serves as a record if it's already done. Commit it (on
`dev`).

### 7. Report

Tell the user: whether the remote repo was created (and its URL), which
branches exist, whether protection was applied automatically or needs the
hand-off in `.repo-config/REPO-SETUP.md`, and that they are now on `dev` —
all pushes go there or to feature branches, and `main` only moves by PR.

## Boundaries

- Do not create accounts or authorize password-based access — direct the user to
  do those themselves.
- SSO/OAuth login flows for an existing account may be completed only with the
  user's explicit go-ahead in the chat.
- One repo per project; this skill assumes a single remote.
