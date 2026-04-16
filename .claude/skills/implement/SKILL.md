---
name: implement
description: Implement a GitHub issue — reads the issue and its wiki ADR, creates a feature branch, dispatches changes to the appropriate subagents, then runs backend, frontend, and e2e tests. Does not commit anything.
argument-hint: Issue number (e.g. 19)
---

# Implement Issue

## Step 1 — Fetch issue details

```
gh issue view $ARGUMENTS --json number,title,body
```

Note the issue number and title. Derive a slug from the title: lowercase, spaces → hyphens, strip special characters.

The zero-padded issue code is `NNN` (three digits, e.g. issue 19 → `019`).

Branch name: `NNN_slug` (e.g. `019_fix-auth-redirect-403`).

## Step 2 — Read the ADR

Clone the wiki into `.wiki/` and read the analysis:

```
git clone git@github.com:Salamahin/chai-s-romashkoi.wiki.git .wiki
cat .wiki/adr/NNN-slug.md
rm -rf .wiki
```

If no matching ADR exists, stop and tell the user — implementation requires prior analysis.

## Step 3 — Prepare the branch

```
git stash
git checkout main
git pull --ff-only
git checkout -b NNN_slug
```

If `git stash` saves changes, warn the user which files were stashed.

## Step 4 — Implement

Read the ADR's task list. For each task, dispatch to the appropriate subagent:

- Backend changes (Python, `backend/`) → `python_developer`
- Frontend changes (TypeScript/Svelte, `frontend/`) → `frontend_developer`
- Infrastructure changes (Terraform, `deploy/`) → `infrastructure_engineer`

Launch independent tasks in parallel. Pass each subagent:
- The full ADR content
- The specific tasks assigned to it
- The constraint: **do not commit anything**

Wait for all subagents to finish before proceeding.

## Step 5 — Run tests

Run all three test suites. Run backend and frontend checks in parallel, then e2e:

**Backend (parallel with frontend):**
```
cd backend && uv run pytest && uv run ruff check . && uv run mypy .
```

**Frontend (parallel with backend):**
```
cd frontend && npx svelte-check --tsconfig tsconfig.json
```

**E2E (after both pass):**
```
bash scripts/e2e.sh
```

## Step 6 — Report

Tell the user:
- Which files were changed (from `git diff --name-only`)
- Test results (pass / fail with output on failure)
- That nothing has been committed — they can review with `git diff` and commit when ready
