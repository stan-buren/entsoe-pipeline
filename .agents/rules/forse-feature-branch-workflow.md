---
trigger: model_decision
description: Use this when starting a new branch, when merging branch to main or when user asks about how 'Feature Branch Workflow' works
---

# Pushing code directly to main branch is forbidden

> ## NOTE:
> Direct commits to the `main` branch are strictly blocked at the repository settings level (via Branch Protection Rules).

# We are using Feature Branch Workflow (GitHub Flow) rules.

**Help** user to investigate this new area of standard working discipline in any Big Tech company (he typically made simple commits to main before)

## What Your Daily Workflow Looks Like Now

After activating this ruleset, your routine for working with the terminal and GitHub will change. Let's break down, step-by-step, the classic development cycle for a single feature (for example, writing a dbt model or a pipeline to fetch data from ENTSO-E).

### Step 1: Syncing Your Local `main` Branch

Before you start working, always pull the latest state from the cloud to avoid running into merge conflicts:

```bash
git checkout main
git pull origin main

```

### Step 2: Creating an Isolated Branch

Never write code directly in `main`. Create a feature branch instead. Use a clear, descriptive prefix (e.g., `feat/`, `fix/`, `refactor/`):

```bash
git checkout -b feat/entsoe-api-ingestion

```

### Step 3: Working on Code and Committing Changes

Write your pipeline code locally and verify that it works correctly. Record your changes using atomic commits:

```bash
git add .
git commit -m "feat: add raw data extractor for entsoe platform"

```

### Step 4: Pushing Your Feature Branch to the Cloud

Attempting to push this directly to `main` would be futile—GitHub would return a `Protected branch error`. Instead, push your changes to your specific feature branch:

```bash
git push origin feat/entsoe-api-ingestion

```

### Step 5: Creating a Pull Request (PR)

1. Navigate to your repository: [stan-buren/entsoe-pipeline](https://github.com/stan-buren/entsoe-pipeline).
2. GitHub will automatically display a banner noting: *"feat/entsoe-api-ingestion had recent pushes"* and will offer a green **Compare & pull request** button. Click it. 3. Describe what you’ve done, then check the **Files changed** tab (this serves as your personal mini-code review—double-check for any forgotten `print()` statements, debug configurations, or credentials).
4. Click **Create pull request**.

### Step 6: Merging

Since you set `Required approvals: 0`, the review status check will immediately turn green.

1. Click the arrow next to the Merge button and select **Squash and merge** (this will consolidate all your small commits from the branch into a single clean commit for `main`).
2. Click **Confirm squash and merge**.
3. GitHub will suggest deleting the branch on the remote repository (*Delete branch*)—go ahead and delete it; it is no longer needed.

### Step 7: Returning to your local `main` branch

Return to your terminal, switch back to `main`, and pull in the changes you just merged via the GitHub interface:

```bash
git checkout main
git pull origin main
# Delete the local branch, as it has already been merged into main
git branch -d feat/entsoe-api-ingestion

```