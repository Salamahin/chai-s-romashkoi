---
name: analyze
description: Analyze a GitHub issue — explores the codebase, produces an architecture decision with task breakdown, publishes it to the GitHub wiki, and updates the issue with a link
argument-hint: Issue number (e.g. 42)
---

# Analyze Issue

## Step 1 — Fetch issue details

```
gh issue view $ARGUMENTS --json number,title,body
```

Note the issue number and title. Derive a slug from the title: lowercase, spaces → hyphens, strip special characters.

The output file will be named: `<number>-<slug>.md`  
Example: issue 42 "Add user notifications" → `42-add-user-notifications.md`

## Step 2 — Clean workspace and switch to main

```
git stash
git checkout main
git pull --ff-only
```

If `git stash` saves nothing, proceed. If there are uncommitted changes that can't be stashed, stop and tell the user.

## Step 3 — Explore the codebase

Launch 2–3 Explore agents in parallel, each targeting a different angle relevant to the issue:

- Overall architecture and data flow through the affected area
- Existing patterns most similar to what the issue asks for
- Infrastructure / deployment constraints that may affect the approach

Ask each agent to return a list of the 5–10 most relevant files. After they return, read those files to build deep context.

## Step 4 — Produce the analysis document

Write the document to `/tmp/<number>-<slug>.md` with the following structure:

```markdown
# <Issue number>: <Issue title>

## Problem Statement
<One paragraph: what the issue is asking for and why it matters>

## Architecture Decision
<Describe the recommended approach: which components change, how data flows, key design choices, trade-offs considered>

## Affected Files / Components
<Bullet list of files or modules that will need to change>

## Implementation Tasks
- [ ] Task 1 — <short description>
- [ ] Task 2 — <short description>
…

## Open Questions
<Anything that needs clarification before or during implementation>
```

Keep it concise. Prefer bullet points over prose. Tasks should be atomic enough to be done in a single PR or commit.

## Step 5 — Publish to the GitHub wiki

```
bash scripts/publish_adr.sh /tmp/<number>-<slug>.md
```

This clones the wiki, writes to `adr/<number>-<slug>.md`, commits, pushes, and deletes the local file.

The resulting wiki page URL is:
`https://github.com/Salamahin/chai-s-romashkoi/wiki/adr/<number>-<slug>`

## Step 6 — Update the GitHub issue

Add a comment to the issue with a link to the analysis:

```
gh issue comment $ARGUMENTS --body "Analysis published: https://github.com/Salamahin/chai-s-romashkoi/wiki/adr/<number>-<slug>"
```

Then tell the user the wiki URL so they can review it.
