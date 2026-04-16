---
name: feature
description: Create a GitHub issue for a new feature — prompts for description, rephrases it, and updates the issue
argument-hint: Optional initial feature idea
---

# Feature Issue Creator

You are helping the user capture a new feature idea as a GitHub issue.

## Step 1 — Create a draft issue

Create a GitHub issue with a placeholder title and body using `gh issue create`:

```
gh issue create --title "feat: [draft]" --body "Draft — description pending"
```

Note the issue URL and number from the output.

## Step 2 — Ask for description

Tell the user the issue was created and ask them to describe the feature in their own words. If `$ARGUMENTS` is non-empty, use that as their description and skip asking.

> "Issue created. What should this feature do? Describe it in your own words (even rough notes are fine)."

Wait for the user's response before proceeding.

## Step 3 — Rephrase and extract the main idea

From what the user said, extract:
- **Title**: a short, clear imperative sentence (≤60 chars, no "feat:" prefix)
- **Summary**: 1–2 sentences stating the core idea in plain language
- **Why**: the motivation or user need this addresses (1 sentence)
- **Acceptance criteria**: 2–5 bullet points describing what "done" looks like

Show these to the user and ask for confirmation or corrections before updating.

> "Here's how I'd frame this feature — let me know if anything needs adjusting:
> …"

Wait for approval.

## Step 4 — Update the issue

Once the user confirms, update the issue using `gh issue edit`:

```
gh issue edit <number> --title "<title>" --body "<formatted body>"
```

Format the body as:

```markdown
## Summary
<1–2 sentence summary>

## Why
<motivation>

## Acceptance Criteria
- <criterion 1>
- <criterion 2>
…
```

Then tell the user the issue URL so they can view it.
