# ADR-005: Pull Request-Driven Git Commit Workflow

## Metadata

**Status:** Accepted
**Version/Date:** v1.0 / 2026-06-29

## Title

Pull Request-Driven Git Commit Workflow for Ingestion Pipeline Development

## Description

Adopt a Pull Request (PR)-driven development workflow where detailed context, rationale, and directory-level modifications are documented comprehensively in a single consolidated PR description rather than verbose, granular git commits.

## Context

During the bootstrapping phase of this educational ENTSO-E pipeline, the overhead of writing atomic, detailed git commits for every minor file change is high. Verbose commit messaging consumes substantial developer time and drains AI API token budgets during pair programming sessions. Since the repository is in an early stage (zero stars, single-developer environment), optimizing development velocity and time-to-market is the primary objective. We need a compromise that preserves historical documentation without slowing down active development.

## Decision Drivers

- **Developer Velocity:** Speed up time-to-market by reducing friction in the commit lifecycle.
- **API Token Conservation:** Prevent excessive token consumption by avoiding frequent prompts to generate atomic commit messages.
- **Centralized Documentation:** Maintain clean, comprehensive change summaries at the PR level.

## Alternatives

- **Option A (Atomic Verbose Commits):** Write highly detailed, multi-line messages for every single commit. (High overhead, slows down development).
- **Option B (Empty/Unstructured Commits):** Write vague or empty commit messages without any centralized documentation. (Creates high technical debt, untraceable changes).
- **Option C (PR-Driven Consolidation):** Use pragmatic commit messages on feature branches, but compile a highly detailed description of all changes in the final PR when merging to main. (Selected: optimizes velocity while keeping documentation high).

### Decision Framework

| Model / Option         | Developer Velocity (Weight: 40%) | Token Conservation (Weight: 30%) | Granular Traceability (Weight: 30%) | Total Score | Decision      |
| ---------------------- | -------------------------------- | -------------------------------- | ----------------------------------- | ----------- | ------------- |
| **Option C (PR-Driven)**| 9/10 (3.6)                       | 9/10 (2.7)                       | 6/10 (1.8)                          | **8.1**     | ✅ **Selected** |
| Option A (Atomic)      | 4/10 (1.6)                       | 3/10 (0.9)                       | 9/10 (2.7)                          | 5.2         | Rejected      |
| Option B (Empty)       | 8/10 (3.2)                       | 9/10 (2.7)                       | 2/10 (0.6)                          | 6.5         | Rejected      |

## Decision

We will adopt **Option C (PR-Driven Consolidation)**. Developers will work on feature branches (following standard branch workflows). Feature branch commits can use concise, practical summaries. When the feature branch is complete, a single, comprehensive Pull Request will be created. The PR description will contain a complete summary of all changes, files modified, and test verification logs. When merging, the merge commit will reference this PR (e.g. `feat: staging schemas generator (#12)`), establishing a clean history.

## High-Level Architecture

```
Feature Branch (Concise Commits) 
  --> [Commit 1: Setup schema caster] 
  --> [Commit 2: Setup table identifier] 
  --> [Create Pull Request #12: Consolidated Staging Transformation Plan & Logs]
  --> [Merge PR into main -> Single Merge Commit referencing PR #12]
```

## Related Requirements

### Functional Requirements

- **FR-1:** Developers must be able to commit changes quickly without writing multi-line explanations for every commit.
- **FR-2:** The merge process must link to a PR that hosts the comprehensive description.

### Non-Functional Requirements

- **NFR-1 (Maintainability):** The main branch history must remain clean, highlighting high-level feature merges.
- **NFR-2 (Usability):** Code reviews must contain exhaustive checklists of changes.

### Performance Requirements

- **PR-1:** Commit submission overhead must not exceed 5 seconds per commit.

### Integration Requirements

- **IR-1:** The GitHub/GitLab repository must enforce pull request usage for main branch merges.

## Related Decisions

- **ADR-001 (Centralized YAML Configuration):** Ensures configurations are decoupled from scripts, reducing the size of code changes.
- **ADR-002 (Centralized Path SSOT):** Minimizes file paths changes across codebases, reducing git conflicts during merges.

## Design

### Architecture Overview

Git branch policy will restrict direct pushes to the `main` branch. All developments must go through feature branches and pull requests.

### Implementation Details

A standard PR template will be established in the repository to guide PR creation:

```markdown
## Summary of Changes
- Refactored `spark/core/iseberg_schema_generator.py` to parse files internally.
- Created `jobs/staging/lakehouse/generate_iceberg_schemas.py` job executor.

## Verification
- Run `just generate-schemas` (output: successful logs).
- Run `uv run pytest tests/` (all passed).
```

### Configuration

Branch protection rules will require a reviewed PR prior to merging to `main`.

## Testing

Verification of this workflow will be managed during pull request reviews. The automated pre-commit hooks (like `validate_adrs.py` and `validate_proposals.py`) will run in CI to verify document structures.

## Consequences

### Positive Outcomes

- **Token Efficiency:** Minimizes AI context/token usage for commit generation.
- **Velocity:** Speeds up code delivery.
- **Documentation Quality:** Detailed PR descriptions are easier to read than multiple scattered git commits.

### Negative Consequences / Trade-offs

- Granular git blame logs on lines of code will point to individual concise commits, requiring developers to trace back to the merge PR to understand specific details.

### Ongoing Maintenance & Considerations

- Ensure PRs are squash-merged or merge commits are properly referenced so history remains readable.

### Dependencies

- **Infrastructure**: Git version control, GitHub repository policies.

## References

- [GitHub Flow Guide](https://docs.github.com/) - Pull request-based development workflows.

## Changelog

- **v1.0 (2026-06-29)**: Initial version defining PR-driven commit workflow.
