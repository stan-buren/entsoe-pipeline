Agent Commit Reconnaissance Protocol
Every time you say to me, "Let's write a commit," I will sequentially execute the following commands in your terminal:

1. Analysis of Modified Files (`git status`)
bash
git status
What I look for: I check which files are in the "Changes to be committed" state (already added to the index via `git add`), which are in "Changes not staged for commit" (modified but not yet added), and which are "Untracked files" (new files).
Why: This allows me to understand the boundaries of the task and determine the specific set of files (the "Scope") for which the commit needs to be written (for example, if files in the `tests/` directory have been modified, the scope might be `(test)` or `(config)`).
2. Examination of Uncommitted Changes (`git diff`)
bash
git diff
What I look for: If files have been modified but not yet added to the index, I run this command to analyze your edits line by line.
Why: I delve into the code's logic to understand exactly what has changed (e.g., which functions were added, which conditions were altered).
3. Examination of Staged Changes (`git diff --cached`)
bash
git diff --cached
What I look for: If you have already executed `git add`, a standard `git diff` will show nothing. In this case, I invoke this command to read the line-by-line changes that are ready to be committed.
Why: I precisely identify the essence of the prepared patch in order to formulate the body of the commit message.
4. Calibration to Repository Style (`git log -n 5 --oneline`)
bash
git log -n 5 --oneline
What I look for: The last 5 commits in your repository.
Why: I observe how commits have been written in this project historically—specifically, which types were used (`feat`, `fix`, `refactor`) and what style for writing scopes is adopted by the team. This allows me to generate a commit that fits perfectly into the project's history without disrupting the overall style.