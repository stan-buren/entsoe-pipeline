# Copyright 2026 Stanislav Burundukov
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Job orchestrator to ingest landing zone CSV files into transaction-safe Iceberg tables.

This script coordinates the incremental flow:
1. Resolves pending files using database change detection (xxhash matches).
2. Sets up a PySpark session.
3. Ingests files domain-by-domain, reading CSVs from S3 and executing Iceberg MERGE (Upsert).
4. Persists execution logs (SUCCESS/FAILED) to Postgres, ensuring fault isolation.
"""

from __future__ import annotations

import logging
import sys

from datetime import UTC, datetime

from entsoe_pipeline import (
    IngestionAttemptLog,
    RunsLogger,
    add_csv_to_iceberg_table,
    build_spark_session,
    commit_ingestion_attempts,
    get_incremental_files_to_ingest,
    get_namespaces_config,
    resolve_active_environment,
    setup_logging,
)
from entsoe_pipeline.preflight import run_staging_preflight

logger = logging.getLogger("entsoe_pipeline.jobs.ingest_landing_csv_to_lakehouse")


def main() -> None:
    """Main job orchestrator for Lakehouse Staging Ingestion."""
    setup_logging()
    logger.info("=== STARTING STAGING ZONE INGRESTION TO LAKEHOUSE ===")

    try:
        # 1. Run readiness preflight checks (S3 gateway & database connectivity)
        run_staging_preflight()

        # 2. Query metadata database to retrieve landing files pending load
        pending_domains = get_incremental_files_to_ingest()
        if not pending_domains:
            logger.info("No files pending integration. Lakehouse is up to date.")
            print('::{"outputs": {"processed": 0, "failed": 0}}::')
            logger.info("=== LAKEHOUSE INGESTION JOB COMPLETED SUCCESSFULLY ===")
            return

        # 3. Initialize Spark session
        logger.info("Initializing active PySpark session for Lakehouse ingestion...")
        spark = build_spark_session("Ingest_Landing_CSV_To_Lakehouse")

        active_env = resolve_active_environment()

        total_processed = 0
        total_failed = 0

        # RunsLogger context automatically handles active execution tracking
        # and generates a unique run_id that we inject into Postgres audit logs.
        with RunsLogger(
            job_name="ingest_landing_csv_to_lakehouse", environment=active_env
        ) as tracker:
            for domain, files in pending_domains.items():
                logger.info(
                    "Processing publication domain: %s (%d files pending)",
                    domain,
                    len(files),
                )

                s3_keys = [f.s3_key for f in files]
                total_raw_size_bytes = sum(f.file_size_bytes for f in files)
                ingested_at = datetime.now(tz=UTC)

                try:
                    # Step A: Load CSV files into a mapped Spark DataFrame
                    from entsoe_pipeline import read_landing_csv_dataset

                    df = read_landing_csv_dataset(spark, s3_keys, domain)

                    # Step B: Perform optimized write/merge to Apache Iceberg table
                    table_name = add_csv_to_iceberg_table(
                        spark=spark,
                        df=df,
                        fms_name=domain,
                        total_raw_size_bytes=total_raw_size_bytes,
                    )

                    # Step C: Formulate SUCCESS log payloads for database commit
                    success_logs = []
                    for f in files:
                        log_entry = IngestionAttemptLog(
                            s3_key=f.s3_key,
                            xxhash=f.xxhash,
                            iceberg_table=table_name,
                            ingested_at=ingested_at,
                            status="SUCCESS",
                            error_message=None,
                            run_id=tracker.run_id,
                        )
                        success_logs.append(log_entry)

                    commit_ingestion_attempts(success_logs)
                    total_processed += len(files)
                    logger.info(
                        "Successfully integrated domain '%s' into '%s'.",
                        domain,
                        table_name,
                    )

                except Exception as e:
                    # Dead Letter Queue (DLQ) logic: isolate errors to current domain,
                    # log failure reasons, and proceed to avoid blocking other datasets.
                    logger.exception(
                        "Failed to ingest domain '%s'. Isolating error...", domain
                    )
                    total_failed += len(files)

                    failed_logs = []
                    for f in files:
                        log_entry = IngestionAttemptLog(
                            s3_key=f.s3_key,
                            xxhash=f.xxhash,
                            iceberg_table=f"lakehouse.{get_namespaces_config().staging}.{domain.lower()}",
                            ingested_at=ingested_at,
                            status="FAILED",
                            error_message=str(e)[
                                :500
                            ],  # Truncate messages to prevent column overflows
                            run_id=tracker.run_id,
                        )
                        failed_logs.append(log_entry)

                    commit_ingestion_attempts(failed_logs)

            # Update RunsLogger runtime status metrics
            tracker.update_metrics(
                processed=total_processed,
                downloaded=0,
                skipped=total_failed,
            )

        # 4. Generate structured Kestra payload outcome metrics
        print(
            f'::{{"outputs": {{"processed": {total_processed}, '
            f'"failed": {total_failed}}}}}::'
        )
        logger.info("=== LAKEHOUSE INGESTION JOB COMPLETED SUCCESSFULLY ===")

    except Exception as e:
        logger.exception("Lakehouse ingestion job failed with a fatal error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
