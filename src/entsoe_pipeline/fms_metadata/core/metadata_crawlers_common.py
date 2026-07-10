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

"""ENTSO-E FMS Metadata Crawlers Shared Common Core Helpers.

Aggregates duplicate operations (database persistence, raw FMS client requests,
observability logging, and Kestra metric emissions) used by both active domain
and legacy publication crawler engines.
"""

from __future__ import annotations

import logging

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from entsoe_pipeline import send_kestra_counter
from entsoe_pipeline.api import list_folder_raw_items
from entsoe_pipeline.fms_metadata.utils.transformer import compile_env_stats

logger = logging.getLogger("entsoe_pipeline.fms_metadata.core.metadata_crawlers_common")


def fetch_root_files_mapping(
    client: Any,
    api_counter: list[int],
    env: str,
    root_dir: str = "",
) -> dict[str, Any]:
    """Fetches root-level raw files mapping from FMS client to support file identification.

    Args:
        client: Initialized FMS API client connection.
        api_counter: A list containing a single integer to track API calls.
        env: Target active environment.
        root_dir: Optional root directory override (e.g. 'TP_Legacy_Publications').

    Returns:
        dict[str, Any]: Mapped dictionary where keys are filenames and values are FMS attributes.
    """
    try:
        root_raw_items = list_folder_raw_items(
            client, "", api_counter, root_dir=root_dir
        )
        return {item["name"]: item for item in root_raw_items}
    except Exception:
        logger.exception("Failed to fetch root files mapping for environment %s", env)
        return {}


def save_crawled_folder_metadata(
    engine: Any,
    fms_folders: Any,
    fms_files: Any,
    env: str,
    domain: str,
    folder_path: str,
    folder_meta: dict[str, Any],
    files: list[dict[str, Any]],
) -> None:
    """Persists aggregated folder metadata metrics and bulk synchronizes file details.

    Args:
        engine: Database engine connection.
        fms_folders: folders database table representation.
        fms_files: files database table representation.
        env: Active environment ('iop' or 'prod').
        domain: Domain or legacy archive name.
        folder_path: Path to the crawled folder.
        folder_meta: Dictionary containing computed count and sizes details.
        files: List of file dictionaries to synchronize.
    """
    with engine.begin() as conn:
        stmt = select(fms_folders.c.id).where(
            fms_folders.c.environment == env.lower(),
            fms_folders.c.folder_path == folder_path,
        )
        row = conn.execute(stmt).fetchone()

        if row:
            folder_id = row[0]
            conn.execute(
                fms_folders.update()
                .where(fms_folders.c.id == folder_id)
                .values(
                    item_count=folder_meta["item_count"],
                    original_bytes=folder_meta["sizes"]["original"]["bytes"],
                    compressed_bytes=folder_meta["sizes"]["compressed"]["bytes"],
                    crawled_at=datetime.now(tz=UTC),
                )
            )
        else:
            result = conn.execute(
                fms_folders.insert().values(
                    environment=env.lower(),
                    domain=domain,
                    folder_path=folder_path,
                    item_count=folder_meta["item_count"],
                    original_bytes=folder_meta["sizes"]["original"]["bytes"],
                    compressed_bytes=folder_meta["sizes"]["compressed"]["bytes"],
                    crawled_at=datetime.now(tz=UTC),
                )
            )
            folder_id = result.inserted_primary_key[0]

        # Clear out deprecated files to prevent stale values, then bulk insert new ones.
        conn.execute(fms_files.delete().where(fms_files.c.folder_id == folder_id))
        if files:
            file_vals = [
                {
                    "file_id": f["file_id"],
                    "folder_id": folder_id,
                    "name": f["name"],
                    "original_bytes": f["sizes"]["original"]["bytes"],
                    "compressed_bytes": f["sizes"]["compressed"]["bytes"],
                    "last_updated": f["last_updated"],
                    "xxhash": f["xxhash"],
                }
                for f in files
            ]
            conn.execute(fms_files.insert(), file_vals)


def finalize_crawl_session(
    logger_instance: Any,
    env: str,
    domain_name: str,
    all_env_file_details: list[dict[str, Any]],
    api_requests: int,
    title: str = "ENVIRONMENT COMPARISON SUMMARY",
) -> None:
    """Compiles crawl statistics, logs comparative reports, and triggers Kestra metrics.

    Args:
        logger_instance: Logger instance to print statements to.
        env: Active environment target.
        domain_name: Crawled domain name or archive name.
        all_env_file_details: Combined parsed details of crawled files.
        api_requests: Total count of FMS API operations.
        title: Visual report header identifier.
    """
    stats = compile_env_stats(env, all_env_file_details, api_requests)

    logger_instance.info("=" * 60)
    logger_instance.info("             %s        ", title.upper())
    logger_instance.info("=" * 60)
    logger_instance.info(
        "%-8s | %-12s | %-10s | %-10s | %-12s | %-10s",
        "Env",
        "Files Count",
        "Orig (MB)",
        "Comp (MB)",
        "Date Range",
        "API Calls",
    )
    logger_instance.info("-" * 75)

    logger_instance.info(
        "%-8s | %-12d | %-10.2f | %-10.2f | %-12s | %-10d",
        env,
        stats["file_count"],
        stats["original_mb"],
        stats["compressed_mb"],
        stats["date_range"],
        stats["api_requests"],
    )
    logger_instance.info("=" * 60)

    # Send FMS API requests metric to Kestra
    send_kestra_counter(
        name="fms_api_requests_count",
        value=stats["api_requests"],
        tags={
            "env": env.upper(),
            "domain": domain_name,
        },
    )
