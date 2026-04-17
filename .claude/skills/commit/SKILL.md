---
name: commit
description: Analyse staged and unstaged changes, stage what makes sense, write a commit message, and commit to the current branch
---

# Commit

## Step 1 — Gather context

Run these in parallel:

```
git status
git diff
git diff --cached
git log --oneline -5
```

## Step 2 — Decide what to stage

Look at unstaged changes (`git diff`). For each modified or new file:

- **Stage it** if it is part of the same logical change as what is already staged, or if it is the only change present.
- **Leave it unstaged** if it is unrelated to the staged work (e.g., a separate bug fix, unrelated refactor, or work-in-progress file).

Do NOT stage:
- `.env` files or anything that looks like secrets or credentials
- Large binary files unless clearly intentional
- Files the user would not expect to be committed (temp files, logs, etc.)

Run `git add <file>` for each file you decide to stage. Prefer adding specific files over `git add -A` or `git add .`.

If you decided to leave some files unstaged, briefly tell the user which ones and why.

## Step 3 — Write the commit message

Review all staged changes (`git diff --cached`) and the recent log for style.

**Closing reference**: parse the current branch name for a leading issue number (e.g. `025_some-slug` → `#25`). Check `git log --oneline` for the branch's commits against main:
- If this is the **first commit** on the branch (no prior commits beyond the branch point), append `Closes #NN` to the commit body.
- If commits already exist on this branch, omit the closing reference — it was already included in the first commit.

Compose a message:
- **Subject line**: imperative mood, ≤72 chars, no trailing period
- **Body** (optional): add only if the subject alone is insufficient — explain *why*, not *what*; append `Closes #NN` here when required (see above)
- Follow the style of recent commits in this repo

## Step 4 — Commit

```
git commit -m "$(cat <<'EOF'
<subject line>

<optional body>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

Report the resulting commit hash and subject to the user.
