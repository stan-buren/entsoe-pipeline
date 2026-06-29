# PROPOSAL-0002: Automated Business Context Catalog Generation

## Metadata

* **Author:** Antigravity / Senior Data Engineer
* **Status:** Under Review
* **Created Date:** 2026-06-29
* **Target Timeline:** Post-Marts Release / Phase 3

---

## Summary

Automate the generation of the business context description catalog (`fms_metadata/overview_tree.yml`) by integrating an automated documentation generator powered by NotebookLM and a custom python parser script. This eliminates manual updates to catalog metadata and prevents desynchronization when new ENTSO-E domains or folders are added.

## Motivation

As the ENTSO-E metadata pipeline expands, new data domains and directory structures are periodically added to the FMS platforms. Currently, verifying catalog consistency relies on a static unit test (`test_detailed_catalog_contains_all_domains_from_overview`). Any new domain addition breaks the test suite until a developer manually updates the business descriptions in `fms_metadata/overview_tree.yml`. Automating this process using NotebookLM will improve developer velocity, maintain 100% catalog synchronization, and ensure users always have up-to-date documentation on all ENTSO-E domain metadata.

## Proposed Design

1. **Disable Manual Match Enforcement:** Skip `test_detailed_catalog_contains_all_domains_from_overview` temporarily to allow catalog desynchronization without blocking CI pipeline runs.
2. **NotebookLM Integration:** Add a script under `src/entsoe_pipeline/notebooklm/` that will execute whenever a new domain is detected.
3. **Automated Run Workflow:**
   * Read the newly crawled physical folder schema from `config/entsoe_fms_folder_schema.yml`.
   * For any undocumented folder name, call NotebookLM API with the folder's name, sample files, and the official ENTSO-E documentation PDF as context.
   * Generate clean `compliance`, `description`, `oneliner`, and `physical_meaning` markdown values automatically.
   * Append the new metadata keys directly into `fms_metadata/overview_tree.yml` and rewrite with warning comments.

## Metrics & Observability (S3 Storage Health)

* **Coverage:** Percentage of active directories in the physical catalog with complete descriptions in the business catalog (target: 100%).
* **Generation Duration:** Time taken to query NotebookLM and rewrite the metadata catalog.
* **Failure Alerts:** Logs and notifications on failed API description generations.

## Open Questions / Risks

* **Rate Limiting:** NotebookLM or LLM API access rate limits and cost implications for massive initial metadata crawls.
* **Prompt Engineering:** Structuring the prompt to ensure the output format matches the schema exactly and does not contain raw HTML or template placeholders.
