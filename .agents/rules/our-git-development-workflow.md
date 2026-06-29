---
trigger: manual
---

# ENTSO-E Metadata Pipeline Git Development Workflow

This document describes our Pull Request-driven development and branch management workflow. This strategy is designed to optimize development velocity, save AI token usage, and maintain a clean repository history.

---

## 1. Core Rule: Protected Main Branch
Direct commits or pushes to the `main` branch are strictly blocked by repository rules. All changes must be delivered via feature branches and Pull Requests.

---

## 2. Step-by-Step Development Lifecycle

### Step 1: Sync Your Local Main
Before starting any new feature, pull the latest changes from GitHub:
```bash
git checkout main
git pull origin main
```

### Step 2: Create a Feature Branch
Choose a branch name reflecting the changes being made. Use one of the standard prefixes:
* `feat/` (e.g., `feat/lakehouse-staging-layer`) for new capabilities or configurations.
* `fix/` (e.g., `fix/imports-whitelist`) for bug fixes.
* `refactor/` (e.g., `refactor/schema-generator-core`) for code improvements without functional changes.
* `chore/` (e.g., `chore/dependency-update`) for build files, tests, or scripts.

```bash
git checkout -b feat/lakehouse-staging-layer
```

### Step 3: Run Pre-Add Verification (Functional Tests & Coverage)
Before staging any changes, you must run the test suite and verify coverage:
1. **`just test`**: Run Pytest to ensure all functional checks pass and coverage is at or above **80%**.

### Step 4: Stage Your Changes
Once the functional test suite and coverage are completely green, stage all modifications to prepare for the commit:
```bash
git add .
```

### Step 5: Run Pre-Commit Checks & Commit
Execute style, type, and security verification checks in this exact order:
1. **`just ruff-check`**: Code style/syntax checks.
2. **`just ruff-fix`**: Automatically fix format and style errors.
3. **`just yamlfmt`**: Auto-format YAML configs (runs slightly longer).
4. **`just ty`**: Run static type analysis.
5. **`just trivy`**: Run security scanner.

If any checks fail, address the issues, stage the fixes (`git add .`), and commit. Ensure the commit references the PR ID:
```bash
git commit -m "feat: staging infrastructure and foundations (#X)"
```

### Step 6: Push the Feature Branch
Push your branch containing the squashed commit to the remote origin:
```bash
git push origin feat/staging-infrastructure-and-foundations
```

### Step 7: Create a Consolidated PR Plan
Before opening the Pull Request, compile a detailed summary of your changes under `docs/.commit_plans/PRs/DD-MM-YYYY.md` using the established format:
* **Features:** High-level additions (Docker, S3 sync, configs).
* **Refactoring:** Modular package cleanup and deleted modules.
* **Chores:** Unit/integration tests and pre-commit validator runs.
* **Verification Logs:** Successful test suite runs and manual job logs.

### Step 8: Open the Pull Request on GitHub
1. Open [stan-buren/entsoe-pipeline](https://github.com/stan-buren/entsoe-pipeline) and click **Compare & pull request** for your branch.
2. Copy and paste the contents of your Markdown PR plan (from `docs/.commit_plans/PRs/`) directly into the Pull Request description.
3. Verify that the pre-commit checks and CI actions pass successfully.

### Step 9: Squash and Merge
1. In the GitHub PR UI, select the **Squash and merge** option.
2. Ensure the merge commit message is clean and references the PR number (e.g., `feat: staging zone loading (#12)`).
3. Confirm the merge and delete the remote feature branch.

### Step 10: Local Cleanup
Switch back to your local `main` branch, pull the squashed commit, and delete your obsolete local branch:
```bash
git checkout main
git pull origin main
git branch -d feat/staging-infrastructure-and-foundations
```