# PROPOSAL-0001: Adaptive Iceberg Compression Tiering & S3 Health Dashboard

## Metadata

* **Author:** Donald Trump & Antigravity
* **Status:** Draft
* **Created Date:** 2026-06-29
* **Target Timeline:** Long-Term (Post-Marts, BI Integration, and Pipeline stabilization - "Cherry on the Cake")

---

## Summary

Implements a smart, automated S3 storage manager that dynamically optimizes S3 disk footprint by adjusting Apache Iceberg/Parquet compression algorithms and levels (ranging from ZSTD 3 to ZSTD 20) based on data access frequency, and introduces an S3 Storage Health Dashboard to monitor system health.

## Motivation

1. **Storage Cost Efficiency:** Columnar data (Parquet) gets significantly smaller at high ZSTD levels, but compression/decompression costs CPU cycles. Decompressing cold historical data at high ZSTD levels is cheap (reads are fast), but writing hot data with high compression eats substantial CPU.
2. **Dynamic Adaptation:** Hot active tables (last 7-30 days) should stay at low ZSTD levels (e.g., Level 3) for fast write throughput and minimal CPU overhead. Cold data (inactive for 30+ days) should be compacted and compressed heavily (e.g., Level 20) to free up storage.
3. **Observability:** Developers need a central panel to track S3 health, detect accumulated temporary files/garbage, and monitor compression ratios.

## Proposed Design

### 1. Dynamic Compaction Manager
We will implement an automated maintenance job (run via Spark/Iceberg metadata queries or Kestra schedule):
- **Hot Tier:** Data modified in the last 7 days. Compression: `zstd` (Level 3).
- **Warm Tier:** Data older than 7 days, but queried in the last month. Compression: `zstd` (Level 7).
- **Cold Tier:** Data older than 30 days, not queried. Compression: `zstd` (Level 15).
- **Archive Tier:** Data older than 90 days, no queries. Compression: `zstd` (Level 20).

An Iceberg action will be run periodically to optimize files:
```python
# Conceptual compaction call
spark.actions().rewriteDataFiles(table_name) \
    .option("compression-codec", "zstd") \
    .option("compression-level", "20") \
    .execute()
```

### 2. S3 Storage Health Dashboard
A Grafana/Prometheus dashboard connected to SeaweedFS/Iceberg catalogs monitoring:
- **Storage Savings:** Total bytes saved vs raw CSV.
- **Tiers Distribution:** Disk space breakdown by hot, warm, cold, and archive tiers.
- **Access Patterns:** S3 GET/PUT call frequencies per domain/endpoint over the past month.
- **ETL Performance:** Average CPU processing time per write.
- **Garbage & Orphan Files:** Space occupied by abandoned write tasks or temporary files.

## Metrics & Observability (S3 Storage Health)

- **Metrics to collect:**
  - `seaweedfs_storage_used_bytes`
  - `iceberg_table_files_count`
  - `spark_compaction_cpu_seconds`
  - `s3_api_calls_total{method="GET", table="..."}`

## Open Questions / Risks

- **Log Collection:** How do we track query history in the REST catalog/SeaweedFS to determine cold vs hot status? (We might need REST catalog server audit logs or Spark query listener hooks).
- **Compaction Costs:** The rewrite/compaction job itself consumes CPU. We must verify that the saved disk storage outweighs the CPU cost of rewriting files.
