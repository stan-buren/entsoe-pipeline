# The WIP Commit Technique: Safe Testing and Preparation for a Perfect Merge

As your senior colleague, I’d like to introduce you to a powerful practice we call the **WIP (Work In Progress) Commit Technique**. When you are working on a large or complex task, you often encounter situations where you need to run tests and linters against an intermediate state of your code—without cluttering your Git history with "junk" commits like `fix tests`, `fix syntax`, or `format code`.

This technique allows you to leverage local tests, pre-commit hooks, and CI/CD pipelines as automated Quality Gates, ultimately guaranteeing a clean and elegant commit history.

---

## Why Is This Necessary?

1. **Clean Commit History (Git Hygiene)**. Your final Pull Request (PR) will consist solely of atomic, complete changes that adhere to standards such as Conventional Commits and ADRs.
2. **Rapid Feedback**. You can run tests or trigger pre-commit hooks to validate all files currently staged in your index by temporarily committing them.
3. **Safety**. All your changes are logged within Git. Even if you accidentally delete a file or perform a destructive operation, you can easily recover your work using `git reflog`.

---

## Step-by-Step: How to Use the WIP Technique

### Step 1. Preparing Changes for a Temporary Commit
First, add all the necessary files to your staging area (the index).
> **Important Repository Rule:** Avoid using wildcard commands like `git add .`. Instead, add specific directories or individual files.

```bash
git add src/entsoe_pipeline/config/
git add tests/
```

### Step 2. Creating a WIP Commit
Create a temporary commit. The content of the commit message doesn't strictly matter, though it is common practice to use a prefix like `wip:` or `tmp:` to ensure you don't accidentally push this temporary commit to the remote repository later. ```bash
git commit -m "wip: temporary staging for testing"
```

*If you only need to test infrastructure-related items (e.g., CI/CD triggers) without modifying any files, you can create an empty commit:*
```bash
git commit --allow-empty -m "wip: trigger CI/CD pipeline"
```

### Step 3. Run Checks and Fix Errors
Now that your working copy is committed in a WIP commit, run your tests and linters:

```bash
# Run tests using our command (see justfile)
just test

# If you are using pre-commit hooks locally
# (e.g., for Ruff style checks or ADR linting)
pre-commit run --all-files
```

If the tests or linters fail with errors:
1. Apply the necessary fixes directly to your code.
2. Add the modified files to the staging area: `git add <file_path>`.
3. "Append" the fixes to your temporary commit using the `--amend` flag (this prevents the creation of new, separate commits):
```bash
git commit --amend --no-edit
```
4. Repeat this cycle until all tests pass successfully (`100% green`).

### Step 4. Soft Resetting the WIP Commit (Git Reset)
Once your code is fully ready—tests are passing and linters are silent—it is time to get rid of the temporary commit. To do this, we perform a **soft reset** to the commit that immediately *preceded* our WIP commit.

```bash
git reset --soft HEAD~1
```

**Why use `--soft` specifically?**
* The `--soft` flag leaves all your changes untouched in your working directory and automatically keeps them in a **Staged** state (added to the index). * You return to the exact state you started from, but now your code is guaranteed to be working and verified.

*(If you want to return files to the working directory but remove them from the staging area, use `git reset HEAD~1` without any flags).*

### Step 5. Final Separation and a Proper Commit
Now your staging area contains clean, verified changes. Split them into logical groups and commit them according to the Conventional Commits guidelines:

1. Remove any extraneous items from the staging area if you need to split them up:
```bash
git restore --staged <file_path>
```
2. Create granular commits with clear descriptions:
```bash
git commit -m "feat(config): unify path management and paths loader"
```
3. Repeat this process until your entire working directory is clean.

---

## The Golden Rules of the WIP Technique

* **Never push WIP commits to the `main` or `master` branch.** WIP commits are permissible only within your personal feature branches (`feat/`).
* **Don't forget to `reset`.** Before merging a branch, the entire commit history must be brought up to Enterprise standards.
* **Use `git reflog`.** If you accidentally performed a hard reset (`git reset --hard`) instead of a soft one and lost your WIP changes, don't panic. The `git reflog` command will show you the hash of your WIP commit, allowing you to restore it using `git reset --hard <commit-hash>`.