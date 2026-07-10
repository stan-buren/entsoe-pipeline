# ADR-007: Separation of Global FMS Metadata Refresher from Active Landing Ingestion

## Metadata

**Status:** Proposed
**Version/Date:** v1.0 / 2026-06-29

## Title

Separation of Global FMS Metadata Refresher from Active Landing Ingestion

## Description

Define the architectural boundary between crawling the complete physical FMS metadata catalog (a heavy, long-running discovery task) and preparing the landing zone schemas for specific active data domains (a lightweight production task).

## Context

1. **Recursive Crawling Correctness:** A flat FMS crawler (non-recursive) failed to discover files nested deep within monthly/daily subfolders in active domains (like `OfferedTransferCapacitiesContinuousEvolution_11.1_r3`), leading to incorrect physical size reports (e.g. 0.0 MB) and data loss. Implementing recursive listing solved this but increased the number of API calls significantly.
2. **API Request Overhead:** Crawling the entire FMS remote file system recursively (across test, prod, and legacy publication folders) requires thousands of requests. Due to client-side rate limits (95 requests/minute), a complete recursive crawl takes between 1.5 to 3 hours.
3. **Operational Decoupling:** 
   - **Exploration & Schema Mapping:** Developers and analysts need a complete, updated physical map of FMS (`overview.yml`, `overview_tree.yml`) to understand available datasets, schemas, and historical data weights. This is an exploration task.
   - **Production Data Ingestion:** The hourly ingestion pipeline (`ingest_my_entsoe_domains.py`) only needs a preflight schema contract (`entsoe_fms_folder_schema.yml`) of the subset of *active* domains configured for the current environment. This is a runtime execution task.
   - Running the entire global crawler before every data ingestion job is computationally wasteful, rate-limit starving, and introduces a huge bottleneck to production SLAs.

## Decision Drivers

- Reduce the execution time and API call overhead of the staging landing preparation job.
- Retain complete and accurate recursive metadata discovery for FMS platform exploration.
- Prevent API rate-limit starvation on production FMS servers.
- Maintain a clean separation between development/exploration artifacts and active production schema registries.

## Alternatives

- **Alternative A (Keep Unified Heavy Job):** Run the complete recursive crawl on every preparation run. This guarantees the latest schema but increases prep runtime to 2+ hours, making hourly ingestion impossible.
- **Alternative B (Selective Ingestion In-Place):** Keep the logic in the same job, but add environment flags to skip legacy crawls. This leaves the code coupled and still relatively slow if even one heavy domain (like transmission capacities) is active.
- **Alternative C (Decouple Global Discovery from Active Prep):** Extract the global FMS crawling process into an independent orchestrator script (`jobs/refresh_fms_metadata.py`) run weekly/monthly. Restrict the active ETL preparation job (`prepare_landing_ingestion.py`) to process only the active domains configuration checklist (`my_entsoe_domains.yml`).

### Decision Framework

| Model / Option | Solution Leverage (Weight: 30%) | Application Value (Weight: 40%) | Maintenance (Weight: 30%) | Total Score | Decision |
|---|---|---|---|---|---|
| **Decouple Global Discovery (Selected)** | 9/10 | 9/10 | 9/10 | **9.0** | ✅ **Selected** |
| Selective Ingestion In-Place | 6/10 | 5/10 | 6/10 | 5.6 | Rejected |
| Keep Unified Heavy Job | 2/10 | 3/10 | 5/10 | 3.3 | Rejected |

## Decision

We will adopt the **Decouple Global Discovery from Active Prep** approach.

1. **Extract Global Refresher:** Extract the full-tree recursive crawling of FMS directories into a dedicated, heavy-duty utility job at `jobs/refresh_fms_metadata.py`. This job will run asynchronously (e.g. once a week/month) to update the global exploration catalogs (`fms_metadata/overview.yml`, `fms_metadata/overview_tree.yml`) in Git.
2. **Restrict Active Prep:** The standard orchestrator `prepare_landing_ingestion.py` will only crawl and process the specific active domains selected in `my_entsoe_domains.yml`. It will no longer execute the global `ingest_fms_metadata` step.
3. **Isolate Active Metadata Storage:** Active metadata slices required to construct the S3 landing schema contract will be written to a dedicated `.data/fms_metadata/` directory, leaving the root `fms_metadata/` directory reserved exclusively for global developer/analyst catalogs.

## High-Level Architecture

```mermaid
graph TD
    subgraph Heavy Discovery (Periodic / Monthly)
        Crawler_Heavy[jobs/refresh_fms_metadata.py] -->|Recursive Crawl| FMS_All[All FMS Directories]
        FMS_All -->|Compile & Commit| Git_Doc[fms_metadata/overview_tree.yml]
    end
    
    subgraph Active Production Ingestion (Hourly)
        Checklist[.data/my_entsoe_domains.yml] -->|Reads Active Domains| Prep_Job[prepare_landing_ingestion.py]
        Prep_Job -->|Lightweight Crawl| FMS_Active[Active Domains Only]
        FMS_Active -->|Compile Schema| Schema_Registry[.data/fms_metadata/schema_contract.yml]
        Schema_Registry -->|Validation & Execution| Ingest_Job[ingest_my_entsoe_domains.py]
    end
```

## Related Requirements

### Functional Requirements

- **FR-1:** `refresh_fms_metadata.py` must support full recursive FMS crawler loops for all active and legacy publication paths.
- **FR-2:** `prepare_landing_ingestion.py` must query the active domains checklist to build a restricted list of target directories, bypassing any inactive branches.

### Non-Functional Requirements

- **NFR-1:** **(Maintainability)** Production crawler configurations must reside in declarative configuration folders, separate from Python ETL logic.
- **NFR-2:** **(Decoupling)** Production ingestion runs must not depend on or modify the global documentation catalogs in `fms_metadata/`.

### Performance Requirements

- **PR-1:** The hourly landing preparation job must run in under 2 minutes when running standard active domain checklists.
- **PR-2:** The FMS API client-side rate limits must be strictly throttled to 95 requests per minute to prevent temporary platform IP bans.

### Integration Requirements

- **IR-1:** The active preparation job must resolve active credentials dynamically using environment resolvers.
- **IR-2:** Schema compilation results must comply with the central S3 landing bucket schema registry specifications.

## Related Decisions

- **ADR-001** (Centralized YAML Config): Environment URLs and credential keys are resolved from env configurations.
- **ADR-002** (Centralized Path SSOT): Path constants for active FMS metadata storage in `.data/` will be defined centrally.
- **ADR-006** (IOP Sandbox): Limits the exposure of test sandbox credentials.

## Design

### Architecture Overview

By isolating the heavy global refresh task from the active ingestion preparation, we protect the production data flows from API rate limits and minimize latency. The active pipeline relies on a clean, trimmed schema contract generated dynamically from the specific domains that are currently being ingested.

### Implementation Details

**In `jobs/staging/landing/prepare_landing_ingestion.py`:**

```python
def main() -> None:
    active_env = resolve_active_environment()
    with RunsLogger(job_name="prepare_landing_ingestion", environment=active_env):
        generate_my_entsoe_domains()
        # Resolve active_folders_by_domain and active_legacy_folders from MY_ENTSOE_DOMAINS_YML
        # Run crawlers only for active folders pointing to ACTIVE_PHYSICAL_CATALOG_DIR
        for dom, folders in active_folders_by_domain.items():
            ingest_func(env=active_env, folders=folders, catalog_dir=ACTIVE_PHYSICAL_CATALOG_DIR)
        
        # Compile active tree and active sizes
        ingest_overview_tree_metadata(ACTIVE_PHYSICAL_CATALOG_DIR, ACTIVE_OVERVIEW_TREE_YML)
        build_landing_bucket_schema(ACTIVE_OVERVIEW_TREE_YML, LANDING_BUCKET_SCHEMA_YML)
        ingest_all_catalog_sizes(ACTIVE_PHYSICAL_CATALOG_DIR, ACTIVE_SIZES_DIR)
```

### Configuration

**In `config/paths.yml`:**

```yaml
# Active FMS metadata directory paths inside the workspace
ACTIVE_FMS_METADATA_DIR: ".data/fms_metadata"
ACTIVE_PHYSICAL_CATALOG_DIR: ".data/fms_metadata/physical_catalog"
ACTIVE_SIZES_DIR: ".data/fms_metadata/sizes"
ACTIVE_OVERVIEW_TREE_YML: ".data/fms_metadata/overview_tree.yml"
```

## Testing

**Verification Commands:**

```bash
# Path verification and dynamic schema loader test
uv run python -m pytest tests/test_paths.py
```

## Consequences

### Positive Outcomes

- Reduces landing preparation job latency from hours to seconds for targeted ingestion.
- Eliminates redundant API calls and rate-limiting issues on the production ENTSO-E servers.
- Preserves full-catalog historical documentation mapping for team onboarding.
- Ensures staging lakehouse pipelines do not ingest unneeded domain telemetry.

### Negative Consequences / Trade-offs

- Running the global crawler requires manual triggering or separate orchestration scheduler DAGs.
- Active schemas are calculated incrementally, which might lead to outdated schema files if a new domain is activated without running preparation first.

### Ongoing Maintenance & Considerations

- Audit the rate-limit limits periodically to optimize FMS client concurrency.
- Schedule the `refresh_fms_metadata.py` job as a cron task in the orchestration environment.

### Dependencies

- **Infrastructure**: `SeaweedFS`, `Docker`.
- **Data Frameworks**: `PySpark >= 4.0.0`, `requests >= 2.31.0`.

## References

- [ENTSO-E Transparency Platform File Directory User Guide](https://transparency.entsoe.eu/) - Official guide to FMS layout
- **ADR-002: Centralized Path SSOT** - Regarding data path configuration lifecycle management

## Changelog

- **v1.0 (2026-06-29)**: Initial proposed version describing the separation of FMS metadata refresh from active landing ingestion.
