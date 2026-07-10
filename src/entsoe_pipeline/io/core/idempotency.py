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

"""Low-level database-driven idempotency and landing zone registry operations."""

from __future__ import annotations

import logging

from datetime import UTC, datetime

from sqlalchemy import create_engine, select

from entsoe_pipeline.db import build_metadata, get_db_url
from entsoe_pipeline.io.core.s3_operations import s3_object_exists

logger = logging.getLogger("entsoe_pipeline.io.core.idempotency")


def parse_iso_datetime(dt_str: str) -> datetime:
    """Parses an ISO-8601 string to a timezone-aware datetime object.

    Args:
        dt_str: ISO-8601 timestamp string (e.g. '2026-06-30T15:35:24.304Z').

    Returns:
        datetime: The parsed datetime object.
    """
    cleaned = dt_str.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        # Fallback for simpler datetime formats
        return datetime.strptime(cleaned, "%Y-%m-%d %H:%M:%S")


def check_idempotency(
    s3_key: str,
    expected_hash: str,
    bucket_name: str,
    s3_client,
) -> bool:
    """Verifies if the file has already been synced using the database registry and S3.

    Args:
        s3_key: Target object key in S3.
        expected_hash: Expected xxHash hex digest of the file metadata.
        bucket_name: Destination S3 bucket name.
        s3_client: The S3 client.

    Returns:
        bool: True if the file has already been synced, False otherwise.
    """
    engine = create_engine(get_db_url())
    db_metadata = build_metadata()
    landing_files_registry = db_metadata.tables["landing_files_registry"]

    with engine.connect() as conn:
        stmt = select(landing_files_registry.c.xxhash).where(
            landing_files_registry.c.s3_key == s3_key
        )
        row = conn.execute(stmt).fetchone()

    if not row:
        return False

    db_hash = row[0]
    return bool(
        db_hash == expected_hash
        and s3_object_exists(
            s3_key=s3_key, bucket_name=bucket_name, s3_client=s3_client
        )
    )


def register_downloaded_file(
    s3_key: str,
    file_name: str,
    file_id: str,
    file_size_bytes: int,
    last_updated_timestamp: str,
    xxhash: str,
    run_id: str,
) -> None:
    """Saves the metadata of a successfully downloaded file to the database.

    Args:
        s3_key: Destination key in S3.
        file_name: Exact name of the physical file.
        file_id: Source file UUID.
        file_size_bytes: Uncompressed file size.
        last_updated_timestamp: ISO-8601 updated watermark string.
        xxhash: calculated xxHash check value.
        run_id: Active execution task identifier.
    """
    engine = create_engine(get_db_url())
    db_metadata = build_metadata()
    landing_files_registry = db_metadata.tables["landing_files_registry"]

    last_updated_dt = parse_iso_datetime(last_updated_timestamp)

    # Convert timezone to UTC if needed
    if last_updated_dt.tzinfo is None:
        last_updated_dt = last_updated_dt.replace(tzinfo=UTC)

    with engine.begin() as conn:
        # Check if record already exists to perform upsert
        stmt = select(landing_files_registry.c.s3_key).where(
            landing_files_registry.c.s3_key == s3_key
        )
        exists = conn.execute(stmt).fetchone()

        values = {
            "s3_key": s3_key,
            "file_name": file_name,
            "file_id": file_id,
            "file_size_bytes": file_size_bytes,
            "last_updated_timestamp": last_updated_dt,
            "xxhash": xxhash,
            "downloaded_at": datetime.now(UTC),
            "run_id": run_id,
        }

        if exists:
            conn.execute(
                landing_files_registry.update()
                .where(landing_files_registry.c.s3_key == s3_key)
                .values(**values)
            )
        else:
            conn.execute(landing_files_registry.insert().values(**values))
