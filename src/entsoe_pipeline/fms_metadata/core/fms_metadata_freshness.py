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

"""ENTSO-E FMS Metadata Freshness and Resume-Capable Filtering Logic.

Responsible for retrieving folder listings and filtering out folders that
were successfully crawled within the configured freshness threshold.
"""

from __future__ import annotations

import logging

from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, select

from entsoe_pipeline import get_crawler_config
from entsoe_pipeline.db import build_metadata, get_db_url
from entsoe_pipeline.fms_metadata.utils.overview_parser import (
    get_domain_folders,
    get_legacy_archive_folders,
)

logger = logging.getLogger("entsoe_pipeline.fms_metadata.core.fms_metadata_freshness")


def get_stale_domain_folders(
    domain_name: str, env: str, is_force: bool = False
) -> list[str]:
    """Retrieves list of stale folders for a specific active domain that need crawling.

    Args:
        domain_name: Target ENTSO-E data domain (e.g. 'Load').
        env: Platform environment ('IOP' or 'PROD').
        is_force: If True, ignores freshness check and returns all folders.

    Returns:
        list[str]: Filtered list of folders to crawl.
    """
    folders = get_domain_folders(domain_name, env)
    return filter_fresh_folders(env, folders, is_force)


def get_stale_legacy_folders(
    archive_name: str, env: str, is_force: bool = False
) -> list[str]:
    """Retrieves list of stale folders for a legacy archive that need crawling.

    Args:
        archive_name: Target legacy archive name (e.g. 'R3_Archives').
        env: Platform environment ('IOP' or 'PROD').
        is_force: If True, ignores freshness check and returns all folders.

    Returns:
        list[str]: Filtered list of legacy folders to crawl.
    """
    folders = get_legacy_archive_folders(archive_name, env)
    return filter_fresh_folders(env, folders, is_force)


def filter_fresh_folders(
    env: str, folders: list[str], is_force: bool = False
) -> list[str]:
    """Filters out folders that have been scanned recently and are still fresh.

    Args:
        env: Target platform environment ('IOP' or 'PROD').
        folders: List of folder paths to check.
        is_force: If True, skips freshness check and returns all folders.

    Returns:
        list[str]: Filtered list of folders that need to be crawled.
    """
    if not folders:
        return []

    if is_force:
        return folders

    # Load freshness threshold from config.
    crawler_cfg = get_crawler_config()
    max_age_days = int(crawler_cfg.get("freshness", {}).get("max_age_days", 3))

    if max_age_days <= 0:
        logger.info(
            "Freshness check disabled (max_age_days <= 0). Re-scanning all folders."
        )
        return folders

    freshness_cutoff = datetime.now(tz=UTC) - timedelta(days=max_age_days)

    engine = create_engine(get_db_url())
    metadata = build_metadata()
    fms_folders = metadata.tables["fms_folders"]

    stale_folders = []
    for folder in folders:
        with engine.connect() as conn:
            stmt = select(fms_folders.c.crawled_at).where(
                fms_folders.c.environment == env.lower(),
                fms_folders.c.folder_path.contains(folder),
            )
            row = conn.execute(stmt).fetchone()

        if row and row[0] is not None:
            crawled_at = row[0]
            if crawled_at.tzinfo is None:
                crawled_at = crawled_at.replace(tzinfo=UTC)
            if crawled_at > freshness_cutoff:
                logger.info(
                    "Skipping fresh folder '%s' (crawled_at=%s, threshold=%s days).",
                    folder,
                    crawled_at.strftime("%Y-%m-%d %H:%M UTC"),
                    max_age_days,
                )
                continue

        stale_folders.append(folder)

    return stale_folders
