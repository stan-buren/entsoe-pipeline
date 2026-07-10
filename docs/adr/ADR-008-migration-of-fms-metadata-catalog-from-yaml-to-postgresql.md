# ADR-008: Migration of FMS Metadata Catalog from YAML to PostgreSQL

## Metadata

**Status:** Accepted
**Version/Date:** v1.1 / 2026-07-01

## Title

Migration of FMS Metadata Catalog from YAML to PostgreSQL

## Description

Migrate the storage format of the FMS physical metadata catalog from local flat YAML files to a structured PostgreSQL database. This migration resolves memory exhaustion OOM crashes, enforces transactional ACID guarantees, ensures idempotency, and enables low-latency hierarchical directory tree lookups for downstream BI/UI interfaces.

## Context

In the previous metadata architecture (ADR-007), we separated the global metadata catalog refresh process from the landing zone ingestion. The metadata crawler recursively searched the remote FMS FTP servers and compiled metadata details (file sizes, counts, update times, hashes) into localized YAML catalog files under `fms_metadata/physical_catalog`.

As the crawlers achieved deep recursive crawls across active and historical archives:
- The IOP catalog reached 74K+ files (63 GB original data size).
- The PROD catalog exceeded 218K+ files (9.4 TB original data size), with the `Transmission` and `Balancing` domains being particularly massive.
- The Python crawling process accumulated the entire directory structure in memory as a nested dictionary, attempting to serialize it to a YAML catalog via `yaml.dump` at the end of the crawl.
- On June 30, the PROD Balancing crawl process consumed 12.4 GB of RAM and was terminated by the host system's `earlyoom` daemon, demonstrating that the sheer size of the `Balancing` domain makes YAML storage impossible.
- Parsing the resulting 92 MB `Transmission.yml` file back into Python memory takes 60–90 seconds, causing severe performance bottlenecks.
- YAML provides no transactional (ACID) safety. If a crawl is interrupted, the catalog is left in a partially written or corrupted state, forcing a complete 3-hour re-scan from scratch.
- Realizing resume-capable incremental scanning with YAML is impractical because checking folder state requires parsing massive files on every startup.

## Decision Drivers

- **Reliability & OOM Prevention:** Ingestion memory utilization must remain low and constant (O(1)) instead of scaling linearly with the file count.
- **Idempotency & Partial Updates:** Support upserting metadata entries on-the-fly in small batches, resuming aborted crawls without duplicate data.
- **Query Performance & Hierarchy:** Enable low-latency recursive directory tree traversal and filtering directly in database queries.
- **BI Compatibility:** Provide a standard SQL connection interface for downstream BI dashboards (e.g. Apache Superset, Metabase).

## Alternatives

- **A: Streaming YAML / Binary Serialization (e.g. `yaml.safe_dump_all` or msgpack)**
  - *Pros:* Keeps metadata file-based, requiring no database services.
  - *Cons:* No query interface. BI/UI dashboards would still have to parse large files. Lack of concurrent write protection.
- **B: Embedded Databases (SQLite / DuckDB)**
  - *Pros:* Embedded, zero infrastructure, supports SQL.
  - *Cons:* Single-writer locking limitations. If the IOP and PROD metadata crawler threads attempt concurrent writes, SQLite/DuckDB will throw database lock errors.
- **C: PostgreSQL**
  - *Pros:* Reuses the existing PostgreSQL database stack running for Kestra, fully ACID compliant, supports high write concurrency, and supports efficient recursive CTEs for tree traversals.
  - *Cons:* Requires keeping a database service running (already covered by docker-compose).

### Decision Framework

| Model / Option | Solution Leverage (Weight: 30%) | Concurrency & ACID (Weight: 35%) | BI Integration (Weight: 20%) | Infrastructure Complexity (Weight: 15%) | Total Score | Decision |
|---|---|---|---|---|---|---|
| **PostgreSQL** | 9 | 10 | 10 | 8 | **9.45** | ✅ **Selected** |
| SQLite | 8 | 5 | 6 | 9 | **6.70** | Rejected |
| DuckDB | 8 | 4 | 5 | 9 | **6.15** | Rejected |

## Decision

We will adopt **PostgreSQL** to host the FMS physical metadata catalog, replacing the flat YAML files under `fms_metadata/physical_catalog`.

We will implement this using the **SQLModel** library (which integrates Pydantic schemas and SQLAlchemy models) and the **psycopg** database driver. We will reuse the existing PostgreSQL instance (`kestra_postgres`) by creating a dedicated database named `entsoe_metadata`.

This decision supersedes the file-based catalog layout specified in ADR-007.

## High-Level Architecture

```mermaid
graph TD
    A[FMS FTP Server] -->|Page-by-page Crawl| B[Python Metadata Crawler]
    B -->|Batch Upserts| C[(PostgreSQL: entsoe_metadata)]
    C -->|Recursive CTE Query| D[UI Directory Tree]
    C -->|Standard SQL SQL| E[BI Dashboards]
```

## Related Requirements

### Functional Requirements

- **FR-1:** The system must record detailed stats (names, sizes, update dates, hashes) of every FMS file.
- **FR-2:** The database must model the parent-child relationships of the FMS directory tree.

### Non-Functional Requirements

- **NFR-1 (ACID Reliability):** Ingestion updates must be transactional to prevent dirty metadata states.
- **NFR-2 (Idempotency):** The system must use upserts (`ON CONFLICT`) to ensure safe reruns.

### Performance Requirements

- **PR-1 (RAM Efficiency):** Ingestion RAM utilization must not exceed 200 MB, even when crawling millions of files.

### Integration Requirements

- **IR-1:** The database must support concurrent connections from multiple crawlers and UI backends.

## Related Decisions

- **ADR-007 (Separation of Metadata Refresh from Ingestion):** Replaces the YAML file serialization stage of the metadata refresh job with direct database writing.

## Design

### Architecture Overview

We define two tables: `fms_folders` and `fms_files` in a parent-child relationship.

### Implementation Details

```python
# Model definitions using SQLModel
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship

class FMSFolder(SQLModel, table=True):
    __tablename__ = "fms_folders"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    environment: str = Field(index=True)  # 'iop' or 'prod'
    domain: str = Field(index=True)       # 'Balancing', 'Transmission', etc.
    folder_path: str = Field(index=True)
    parent_id: Optional[int] = Field(default=None, foreign_key="fms_folders.id")
    item_count: int = 0
    original_bytes: int = 0
    compressed_bytes: int = 0
    crawled_at: Optional[datetime] = Field(default=None)  # UTC timestamp of last crawl

class FMSFile(SQLModel, table=True):
    __tablename__ = "fms_files"
    
    file_id: str = Field(primary_key=True)  # UUID from FMS
    folder_id: int = Field(foreign_key="fms_folders.id")
    name: str = Field(index=True)
    original_bytes: int
    compressed_bytes: int
    last_updated: str
    xxhash: str
```

### Configuration

We configure database credentials via our env-specific YAML configs using paths defined in the config loader.

```yaml
database:
  url: "postgresql://kestra:password@localhost:5432/entsoe_metadata"
```

## Testing

We will implement database interaction tests using `pytest` and a running test PostgreSQL container or mock sessions.

```python
# Skeleton test logic
import pytest
from sqlmodel import Session, SQLModel, create_engine

def test_metadata_idempotent_upsert():
    # Arrange: Setup SQLite memory engine for fast unit tests
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    
    # Act: Perform double insert of same metadata
    # Assert: Count is 1, size is updated
    pass
```

## Consequences

### Positive Outcomes

- Permanently resolves memory OOM issues by writing data in small streaming batches.
- Avoids data corruption via SQL transaction boundaries (ACID).
- Drastically reduces query latency for dashboard reporting (from 90s to milliseconds).
- Enables efficient resume-capable incremental crawling (idempotency). By checking the `crawled_at` timestamp in the database, the crawler can skip fresh folders in milliseconds. This is governed by the `config/fms_crawler.yml` configuration (e.g. `freshness.max_age_days: 3`). Attempting this with flat YAML files was impossible due to the high parsing overhead.
- Simplifies the ingestion code by eliminating multiple identical script entry points (dry refactoring).

### Negative Consequences / Trade-offs

- Introduces database schema migration overhead (requires using Alembic or raw DDL migrations).
- Requires a running PostgreSQL instance (satisfied by our current docker setup).

### Ongoing Maintenance & Considerations

- Monitor indexing performance on query paths (e.g. indices on `folder_path` and `environment`).
- Clean up historical catalog entries if needed to keep the table sizes optimized.

### Dependencies

- **Infrastructure:** `PostgreSQL >= 16`
- **Data Frameworks:** `SQLModel >= 0.0.22`, `psycopg >= 3.1.0`

## References

- [SQLModel Documentation](https://sqlmodel.tiangolo.com/) - Integrated database model definitions
- [PostgreSQL WITH RECURSIVE](https://www.postgresql.org/docs/current/queries-with.html) - Documentation on CTE hierarchical traversals

## Changelog

- **v1.1 (2026-07-01):** Updated to document database-backed folder freshness tracking (`crawled_at`) and the `fms_crawler.yml` freshness config enabling low-overhead resume-capable scans.
- **v1.0 (2026-06-30):** Initial proposed draft migration from file-based YAML catalogs to PostgreSQL.
