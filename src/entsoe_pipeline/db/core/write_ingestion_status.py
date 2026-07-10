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

"""Low-level database access writes for committing lakehouse ingestion state logs."""

from __future__ import annotations

import logging

from typing import Any

from sqlalchemy import create_engine, insert

from entsoe_pipeline.db.init_entsoe_metadata_db_schema import build_metadata, get_db_url

logger = logging.getLogger("entsoe_pipeline.db.core.write_ingestion_status")


def write_ingestion_attempts_to_db(logs: list[dict[str, Any]]) -> None:
    """Inserts a batch of ingestion log entries into lakehouse_ingestion_registry.

    Args:
        logs: A list of dictionaries representing log entries to insert. Each dictionary
            must contain: 's3_key', 'xxhash', 'iceberg_table', 'ingested_at', 'status',
            'error_message', and 'run_id'.

    Raises:
        Exception: If the batch insert operation fails.
    """
    if not logs:
        logger.debug("No ingestion status logs to write.")
        return

    engine = create_engine(get_db_url())
    db_metadata = build_metadata()
    registry_table = db_metadata.tables["lakehouse_ingestion_registry"]

    stmt = insert(registry_table)

    logger.info("Writing %d ingestion attempt log entries to PostgreSQL...", len(logs))
    with engine.begin() as conn:
        conn.execute(stmt, logs)

    logger.info("Successfully persisted ingestion logs batch.")
