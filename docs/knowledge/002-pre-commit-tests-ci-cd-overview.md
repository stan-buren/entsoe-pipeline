# Pre commit, tests and CI/CD overview

Colleague, this is a fundamental question—one that distinguishes a professional developer from an amateur. Understanding this difference will save you hundreds of hours in the future.

Imagine we are building a security system for our data warehouse. To ensure that no bugs or shoddy code make it into production, we establish **three lines of defense**. Let's break down each of them using your `.pre-commit-config.yaml` file as an example.

---

### 🧱 Line 1: Pre-commit (Local Hygiene)
**Where it lives:** On your computer.
**When it triggers:** The moment you type `git commit` in your terminal.

This line of defense operates **before** your code is even recorded in your Git repository.

Your `.pre-commit-config.yaml` file serves as a set of instructions for your computer. Before committing your changes, Git consults this file and executes a series of quick checks:
*   *Linting and Formatting* (`ruff-check`, `ruff-format`): Automatically corrects typos within the codebase and formats the code.
*   *Internal Order* (`validate-adrs`, `no-dead-code`, `duplicate-tests`): Runs your custom scripts to verify that you haven't left behind any dead code, haven't duplicated tests unnecessarily, and have correctly filled out your architectural decision records (ADRs).

**The Key Benefit:** This happens instantly (within 1–3 seconds). If you forget to run Ruff or leave some dead code lying around, `pre-commit` will block the commit—preventing you from making a mistake—and automatically fix the issues for you. You don't have to waste time pushing your code to the cloud just to discover a silly typo.

---

### 🧪 Line 2: Tests (Logic Verification)
**Where it lives:** Both locally on your machine (when you run them manually) and in the cloud. **When it triggers:** When you want to verify the functionality of your algorithms (`pytest`).

Pre-commit checks the **form** of the code (whether it looks good and adheres to formatting rules). Tests check the **meaning and logic** of the code.
*   Pre-commit doesn't know whether your Spark session is correctly calculating an ENTSOE aggregation. It only sees that the code is written neatly.
*   **Tests**, however, execute your actual Python code, create a test DataFrame, run it through your transformation logic, and verify the result.

**The Key Feature:** Tests can take a long time to run (anywhere from a few seconds to tens of minutes) because they spin up Spark sessions, emulate databases, and perform calculations. Their objective is to prove that the mathematical and business logic of the pipeline are functioning correctly.

---

### 🚀 Milestone 3: CI/CD (The Supreme Judge and Automated Deployment)
**Where it lives:** On remote servers (e.g., GitHub Actions, GitLab CI).
**When it triggers:** When you execute a `git push` or create a Pull Request.

This constitutes a fully automated pipeline (Continuous Integration / Continuous Deployment).

Developers have a classic excuse: *“I don't know why it crashed on the server—it worked perfectly on my computer!”* CI/CD eliminates this human factor.
*   **CI (Integration):** The server fetches your branch, provisions a completely clean operating system from scratch, downloads dependencies using `uv sync`, and runs **linters** (such as Ruff) as well as **all your tests**. If anything fails within this "sterile" environment, your branch is marked with a red cross and blocked from being merged into `main`. *   **CD (Delivery):** If the CI stage passes successfully (indicated by a green checkmark), this pipeline automatically builds a Docker image and deploys your Spark pipeline to the production servers.

---

### Ultimate Cheat Sheet

| Criterion | Pre-commit | Tests | CI/CD |
| :--- | :--- | :--- | :--- |
| **What does it check?** | Code formatting, style, and cleanliness. | The functionality of business logic and calculations. | The entire project build in a clean environment + automated deployment. |
| **Where does it run?** | Only on your local machine. | ​​Locally on the developer's machine + in the cloud via CI. | Strictly in the cloud (on build servers). |
| **When does it run?** | Automatically when attempting to run `git commit`. | Manually by the developer, or automatically within the CI pipeline. | ​​Automatically upon `git push` or when creating a PR. |
| **Execution Speed** | Very fast (fractions of a second / a few seconds). | Moderate to slow (depends on the volume of computations). | Slow (takes minutes, as it involves provisioning an OS from scratch). |

As you can see, this forms a unified ecosystem for code quality! We catch typos during the pre-commit stage, logical errors via tests, and entrust the final integration to an impartial CI/CD system.

Has everything clicked into place now?