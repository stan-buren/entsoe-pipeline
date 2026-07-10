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

"""Low-level database access queries for incremental file delta detection."""

from __future__ import annotations

import logging

from collections.abc import Sequence

from sqlalchemy import Row, create_engine, text

from entsoe_pipeline.db.init_entsoe_metadata_db_schema import get_db_url

logger = logging.getLogger(
    "entsoe_pipeline.db.core.query_for_landing_files_pending_integration"
)


def fetch_incremental_files_from_db() -> Sequence[Row[tuple[str, str, int]]]:
    """Queries PostgreSQL database for landing files pending integration.

    Executes an anti-join query between the landing_files_registry (source)
    and lakehouse_ingestion_registry (destination) using window functions.
    Isolates files that have never been processed, files whose latest attempt failed,
    or files whose xxhash checksum has changed since the last ingestion.

    Returns:
        Sequence[Row[tuple[str, str, int]]]: A sequence of rows containing
        (s3_key, xxhash, file_size_bytes) from the landing files registry.
    """
    engine = create_engine(get_db_url())

    query = text("""
        WITH latest_ingestion AS (
            SELECT
                s3_key,
                xxhash,
                status,
                ROW_NUMBER() OVER (PARTITION BY s3_key ORDER BY ingested_at DESC) as rn
            FROM lakehouse_ingestion_registry
        )
        SELECT
            lfr.s3_key,
            lfr.xxhash,
            lfr.file_size_bytes
        FROM landing_files_registry lfr
        LEFT JOIN latest_ingestion li
            ON lfr.s3_key = li.s3_key AND li.rn = 1
        WHERE
            li.s3_key IS NULL
            OR li.status = 'FAILED'
            OR lfr.xxhash != li.xxhash
    """)

    logger.info("Executing incremental landing files anti-join query...")
    with engine.connect() as conn:
        result = conn.execute(query).fetchall()

    logger.info("Query completed. Retrieved %d files pending ingestion.", len(result))
    return result
