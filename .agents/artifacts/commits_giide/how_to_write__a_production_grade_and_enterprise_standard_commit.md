# The Enterprise Standard for Production-Grade Git Commits

To write a production-grade and enterprise-standard commit, you must adhere to a strict set of structural rules. In my 15 years of engineering data platforms, I have seen unstructured commit histories become maintenance nightmares, making it impossible to audit changes, automate deployments, or debug pipeline regressions. A well-cared-for commit log transforms Git from a simple backup tool into a powerful analytical instrument for `git blame`, `revert`, and `rebase`. 

As a Junior Data Engineer, you must follow these explicit instructions to ensure your commits are machine-readable, human-readable, and fundamentally sound. 

### 1. Adopt the Conventional Commits Specification
You must prefix every commit subject with a specific type token followed by a colon and a space. The format is `<type>[optional scope]: <description>`.

**Instructions:**
*   Use `feat:` when introducing a new feature to the data pipeline or codebase (correlates with a MINOR release in Semantic Versioning).
*   Use `fix:` when patching a bug in your code (correlates with a PATCH release).
*   Use other standard types such as `build:`, `chore:`, `ci:`, `docs:`, `style:`, `refactor:`, `perf:`, or `test:` when the change does not impact the production data logic directly.
*   If your commit introduces a breaking change (e.g., dropping a table column used downstream), append a `!` before the colon (e.g., `feat(api)!: remove user_id`) or include a `BREAKING CHANGE:` footer.

**Why?**
The Conventional Commits specification is a lightweight convention that creates an explicit commit history. By standardizing your commit types, we can automatically generate CHANGELOGs, automatically determine semantic version bumps, and seamlessly trigger CI/CD build and publish processes. 

### 2. Separate the Subject from the Body with a Blank Line
You must always leave a single blank line between your short subject line and the multi-paragraph body of the commit.

**Why?**
Git parses commit messages based on this blank line. The text up to the first blank line is treated as the commit title. Tools like `git log --oneline` or `git shortlog` rely on this separation to print out just the subject line for concision. If you fail to include the blank line, Git and other CI tools will mash the subject and body together, breaking formatting and automated parsing.

### 3. Limit the Subject Line to 50 Characters
Your subject line should ideally be 50 characters or less, and it must never exceed a hard limit of 72 characters. 

**Why?**
This forces you to think critically and concisely about the exact nature of your change. Furthermore, GitHub's user interface will automatically truncate any subject line longer than 72 characters with an ellipsis. If you are having a hard time keeping the subject under 50 characters, it usually means you are committing too many changes at once and need to break them apart.

### 4. Capitalize the Subject and Omit the Trailing Period
You must begin all subject lines with a capital letter and you must not end the subject line with a period.

**Why?**
Space is incredibly precious when you are restricted to 50 characters, making trailing punctuation a waste of characters. Capitalization enforces a professional, sentence-like standard across the entire engineering team.

### 5. Use the Imperative Mood in the Subject Line
You must write your subject line in the imperative mood, meaning it should read as a command or instruction (e.g., "Refactor subsystem X", not "Refactored subsystem X"). 

A foolproof rule to ensure you are writing in the imperative mood is that your subject line must smoothly complete this sentence: *"If applied, this commit will <your subject line here>"*.

**Why?**
You must match Git's internal conventions. Whenever Git creates a commit on your behalf (such as when using `git merge` or `git revert`), it automatically uses the imperative mood. By adopting this standard, your manual commits will blend seamlessly with Git's automated commits, maintaining a unified historical log.

### 6. Wrap the Body at 72 Characters
When writing the body of your commit, you must manually insert line breaks so that no line of text exceeds 72 characters.

**Why?**
Unlike word processors, Git never wraps text automatically. By wrapping your text at 72 characters, you ensure that Git has plenty of room to indent the text in terminal outputs while keeping everything under the standard 80-character terminal limit overall.

### 7. Explain *What* and *Why*, Not *How*
The body of your commit must describe the context of the change: the way things worked before, what was wrong with that, the way they work now, and the reason you chose to solve it this way. You must not describe *how* you implemented the change line-by-line.

**Why?**
The code diff already tells the reviewer *how* the change was made; explaining it in the commit message is redundant. However, the code cannot explain the business logic or the historical context behind the change. As noted by open-source maintainer Peter Hutterer:

> "Re-establishing the context of a piece of code is wasteful. We can't avoid it completely, so our efforts should go to reducing it [as much] as possible. Commit messages can do exactly that and as a result, a commit message shows whether a developer is a good collaborator."

### 8. Reference Architecture Decision Records (ADRs) in the Footer
Since we do not use Jira, you must use the footer of your commit to link your code changes to our Architecture Decision Records (ADRs). The footer must begin one blank line after the body.

**Instructions:**
*   Use a footer token like `ADR: <ADR-Identifier>` or `Ref: ADR-<Number>`.
*   Example: `ADR: 0012-use-iceberg-tables`

**Why?**
ADRs document the context, the concern we were facing, the options considered, and the final architectural decision. When debugging a pipeline two years from now, a data engineer will need to know *why* a specific transformation pattern was chosen. Tying the commit directly to the ADR provides the exact technical and strategic rationale for the code without cluttering the commit body itself. 

### 9. Enforce Atomic Commits
You must keep your commits atomic. Keep commits focused on a single, specific change, and avoid mixing unrelated changes in the same commit.

**Why?**
If you bundle a pipeline performance fix, a documentation update, and a schema change into one commit, rolling back a failure becomes a nightmare. If the schema change breaks production, reverting the commit will also revert your performance fix and documentation. Atomic commits ensure that every logical change can be tracked, reviewed, and reverted independently. 

### Example of a Perfect Enterprise Commit:

```text
feat(ingestion): implement CDC parsing for Iceberg tables

This replaces the full-table daily snapshot process with a Change Data
Capture (CDC) streaming approach. The previous snapshot method caused
severe read locks on the upstream operational database, leading to
latency spikes during business hours.

By parsing the binlogs directly, we reduce upstream load by 85% and
decrease our data freshness lag from 24 hours to 5 minutes. The pipeline
now handles `INSERT`, `UPDATE`, and `DELETE` events natively.

ADR: 0015-move-to-cdc-streaming
```