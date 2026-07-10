# ADR-010: Dynamic Schema Inference Fallback for Unmapped Business Publications

## Metadata

**Status:** Accepted
**Version/Date:** v1.0 / 2026-07-08

## Title

Dynamic Schema Inference Fallback for Unmapped Business Publications and Legacy Domains

## Description

We will implement an automated schema inference fallback (using Spark's `inferSchema`) for business publications and legacy archives that lack structural definition details (i.e. `columns: []`) in the central `entsoe_fms_schemas.yml` configuration registry.

## Context

The ENTSO-E File Management System (FMS) contains active and legacy directories that lack official HTML/Zendesk documentation from ENTSO-E (for example, older `_r3` releases whose documentation was replaced by `_r3.1`, or legacy `_r1` and `_r2` archives). 

Our crawler registers these publications with empty columns (`columns: []`). Under a strict schema enforcement model, attempting to create Iceberg tables for these publications results in database DDL compilation errors (empty column list syntax errors). Without a fallback, data engineers would have to manually inspect and code schemas for dozens of legacy endpoints, causing severe bottlenecks.

## Decision Drivers

- **Time-to-Market:** Need to load historical archives without writing hundreds of manual overrides.
- **Fail-Safe Processing:** Isolated pipeline failures must not block unrelated data domains.
- **Dynamic Schema Adaptability:** The system must gracefully accept undocumented files while logging warnings.

## Alternatives

- **Option A (Strict Schema Enforcement):** Manually map all missing columns in `entsoe_fms_schemas.yml`.
  - *Pros:* High data quality guarantees, exact type casting.
  - *Cons:* Extremely high manual maintenance overhead, blocks ingestion on new releases.
- **Option B (Dynamic Schema Inference Fallback):** Automatically trigger Spark schema auto-inference when `columns: []` is encountered.
  - *Pros:* Low maintenance, high extensibility, immediate data load capabilities.
  - *Cons:* Spark auto-inference may mistype float columns or timestamp formats, increasing downstream validation risk.

### Decision Framework

| Model / Option                            | Time-to-Market (Weight: 40%) | Maintainability (Weight: 30%) | Schema Accuracy (Weight: 30%) | Total Score | Decision       |
| ----------------------------------------- | ---------------------------- | ----------------------------- | ----------------------------- | ----------- | -------------- |
| **Option B (Dynamic Inference Fallback)** | 9/10 (3.6)                   | 9/10 (2.7)                    | 6/10 (1.8)                    | **8.1/10**  | ✅ **Selected** |
| Option A (Strict Schema Enforcement)      | 2/10 (0.8)                   | 4/10 (1.2)                    | 9/10 (2.7)                    | 4.7/10      | Rejected       |

## Decision

We will adopt **Option B (Dynamic Schema Inference Fallback)** to address unmapped legacy schemas. This involves using Spark's native **inferSchema** parameter dynamically when column list definitions are missing. This decision does not supersede any previous ADRs.

## High-Level Architecture

We inject a fallback check within the Spark dataset loader. If a publication schema config does not contain defined columns, we bypass strict DDL generation and ask Spark to read the source file metadata headers dynamically.

```
[Landing Zone CSV] ──► [Empty Schema Checker] ──► (Yes) ──► [Spark inferSchema] ──► [Sanitize snake_case] ──► [Iceberg Table]
```

## Related Requirements

### Functional Requirements

- **FR-1:** Ingestion must process files with empty schemas in `entsoe_fms_schemas.yml`.
- **FR-2:** Target Iceberg tables must be created with dynamically inferred columns.

### Non-Functional Requirements

- **NFR-1:** **(Data Reliability)** The fallback schema must prevent manual schema overrides where configuration is missing.
- **NFR-2:** **(Maintainability)** The config must be fully separated from PySpark script logic.
- **NFR-3:** **(Extensibility)** Schema migrations must occur without rebuilding the target tables.

### Performance Requirements

- **PR-1:** Dynamic schema auto-inference must occur only once per table initialization to minimize metadata retrieval costs.
- **PR-2:** Memory footprint of Spark schema parsing must fit within standard executor allocations.

### Integration Requirements

- **IR-1:** The system must natively connect to the target catalog (e.g. REST catalog).
- **IR-2:** Schema results must conform to Apache Iceberg metadata validation standards.

## Related Decisions

- **ADR-001** (Centralized YAML Configuration): Configuration schemas remain the Single Source of Truth (SSOT).
- **ADR-009** (FMS Metadata Catalog Matching): Discovery uses early binding mapping.

## Design

### Architecture Overview

When Spark receives files to ingest:
1. It verifies the target table presence.
2. If absent and the contract schema has columns, it creates a table using mapped Spark columns.
3. If absent and the contract schema is empty, it reads the header row with `inferSchema=True`, maps column names to lower_snake_case, and creates the Iceberg table dynamically.

### Implementation Details

In `src/entsoe_pipeline/spark/landing_csv_reader.py`:

```python
    # Target columns fallback to Spark schema inference if config list is empty
```

### Configuration

**In `config/lakehouse_parquet_codec.yml`:**
No custom configurations are required; the fallback is dynamically resolved in Python code.

## Testing

**In `tests/test_landing_csv_reader.py`:**

```python
def test_schema_inference_fallback():
    # Verify that a domain with columns: [] correctly infers schema from a raw CSV file
    pass
```

## Consequences

### Positive Outcomes

- Reduces technical debt by eliminating manual schema evolution scripts.
- Unlocks loading of legacy archives immediately.
- Simplifies multi-environment deployments by abstracting catalog connections via environment-specific profiles.

### Negative Consequences / Trade-offs

- Introduces strict schema enforcement, which may break downstream jobs if upstream changes are not backward compatible.
- Spark auto-inference may mistype float columns or timestamp formats.

### Ongoing Maintenance & Considerations

- Audit catalog connection secrets rotation frequency.
- Track partition pruning efficiency in Spark UI to prevent full table scans.

### Dependencies

- **Infrastructure**: `SeaweedFS`, `PostgreSQL`.
- **Data Frameworks**: `Apache Iceberg >= 1.11.0`, `PySpark >= 4.1.1`.
- **Removed**: None.

## References

- [Apache Iceberg Documentation](https://iceberg.apache.org/) - Detailed specifications for table maintenance.
- [Parquet File Format Specifications](https://parquet.apache.org/) - Technical insights into metadata.

## Changelog

- **v1.0 (2026-07-08)**: Initial version defining dynamic schema inference fallback rules.
