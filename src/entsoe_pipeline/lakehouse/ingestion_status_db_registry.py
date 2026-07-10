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

"""High-level repository metadata state manager for Lakehouse ingestion logging.

This module provides high-level functions to log and record individual file
ingestion states (SUCCESS or FAILED) directly back to the relational catalog.
"""

from __future__ import annotations

import logging

from dataclasses import asdict, dataclass
from datetime import datetime

from entsoe_pipeline.db import write_ingestion_attempts_to_db

logger = logging.getLogger("entsoe_pipeline.lakehouse.ingestion_status_db_registry")


@dataclass(frozen=True)
class IngestionAttemptLog:
    """Represents a single ingestion outcome to be written to database registry.

    Attributes:
        s3_key: S3 object key that was processed.
        xxhash: Digest fingerprint of the processed file.
        iceberg_table: Destination Iceberg table name.
        ingested_at: Timestamp when processing was executed.
        status: Attempt outcome status ('SUCCESS' or 'FAILED').
        error_message: Optional traceback or reason for failure.
        run_id: Execution run identifier.
    """

    s3_key: str
    xxhash: str
    iceberg_table: str
    ingested_at: datetime
    status: str
    error_message: str | None
    run_id: str


def commit_ingestion_attempts(attempts: list[IngestionAttemptLog]) -> None:
    """Persists a list of ingestion attempt log outcomes.

    Accepts typed domain dataclasses, transforms them into low-level raw dictionaries,
    and delegates the transactional batch insert to the core database subsystem.

    Args:
        attempts: List of IngestionAttemptLog domain dataclasses.
    """
    if not attempts:
        logger.debug("No ingestion attempt logs to commit.")
        return

    logger.info("Mapping %d high-level log entities to db payload...", len(attempts))
    payload = [asdict(attempt) for attempt in attempts]

    try:
        write_ingestion_attempts_to_db(payload)
    except Exception:
        logger.exception(
            "Failed to write ingestion status updates to Postgres database."
        )
        raise
