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

"""ENTSO-E FMS Legacy Publications Ingestion Engine.

Orchestrates FMS historical archive metadata discovery, paginated file crawls,
and structured catalog persistence into the PostgreSQL database.
"""

from __future__ import annotations

import logging

from typing import TYPE_CHECKING

from sqlalchemy import create_engine

from entsoe_pipeline import get_classifier_config, resolve_active_environment
from entsoe_pipeline.api import create_fms_client
from entsoe_pipeline.db import build_metadata, get_db_url
from entsoe_pipeline.fms_metadata.core.metadata_crawlers_common import (
    fetch_root_files_mapping,
    finalize_crawl_session,
    save_crawled_folder_metadata,
)
from entsoe_pipeline.fms_metadata.utils import crawl_metadata_folder
from entsoe_pipeline.fms_metadata.utils.overview_parser import (
    get_legacy_archive_folders,
)
from entsoe_pipeline.fms_metadata.utils.transformer import (
    compile_folder_metadata,
)

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger("entsoe_pipeline.fms_metadata.core.legacy")


def ingest_legacy_metadata(
    archive_name: str,
    env: str | None = None,
    folders: list[str] | None = None,
    catalog_dir: Path | None = None,
) -> None:
    """Orchestrates FMS metadata gathering for a specified historical archive.

    Crawls legacy folders sequentially and persists folder stats and file details
    atomically per folder to PostgreSQL.

    Args:
        archive_name: The legacy archive key (e.g. 'R3_Archives', 'R2_Archives').
        env: Optional environment name. If None, resolves dynamically.
        folders: Optional pre-filtered list of legacy folders to process.
        catalog_dir: Optional custom catalog storage directory (unused, kept for API parity).
    """
    del catalog_dir  # Unused parameter kept for compatibility with callers.
    logger.info(
        "=== STARTING HISTORICAL %s METADATA EXPLORATION ===",
        archive_name.upper(),
    )

    config = get_classifier_config()
    rule = next(
        (r for r in config.legacy_rules if r.archive.lower() == archive_name.lower()),
        None,
    )
    if not rule:
        logger.error(
            "Legacy archive rule '%s' not found in classifier config",
            archive_name,
        )
        return

    if env is None:
        env = resolve_active_environment()

    logger.info("-" * 60)
    logger.info("PROCESSING LEGACY ENVIRONMENT: %s", env)
    logger.info("-" * 60)

    # Retrieve specific archive folders matching the classifier specifications.
    try:
        archive_folders = get_legacy_archive_folders(archive_name, env)
    except Exception:
        logger.exception(
            "Failed to retrieve legacy folders for %s on env %s",
            archive_name,
            env,
        )
        return

    if folders is None:
        folders = archive_folders
    else:
        # Intersect with the active checklist folders.
        folders = [f for f in folders if f in archive_folders]

    if not folders:
        logger.info("No active legacy folders to process for archive: %s", archive_name)
        return

    api_counter = [0]

    try:
        client = create_fms_client(env)
    except Exception:
        logger.exception("Failed to initialize FMS client for environment %s", env)
        return

    # Initialize dynamic database connection and schema tables.
    engine = create_engine(get_db_url())
    metadata = build_metadata()
    fms_folders = metadata.tables["fms_folders"]
    fms_files = metadata.tables["fms_files"]

    all_env_file_details = []

    # Fetch root raw items once to catalog root-level files.
    root_files_by_name = fetch_root_files_mapping(
        client, api_counter, env, root_dir="TP_Legacy_Publications"
    )

    for folder in folders:
        logger.info("Processing legacy folder: %s", folder)
        try:
            files = crawl_metadata_folder(
                client=client,
                folder=folder,
                root_files_by_name=root_files_by_name,
                api_counter=api_counter,
                env=env,
                root_dir="TP_Legacy_Publications",
            )
        except Exception:
            logger.exception(
                "Error crawling legacy folder %s on environment %s",
                folder,
                env,
            )
            continue

        # Aggregate physical stats dynamically via aggregates compiler.
        folder_meta = compile_folder_metadata(
            folder, files, root_dir="TP_Legacy_Publications"
        )
        folder_path = folder_meta["folder_path"]
        all_env_file_details.extend(files)

        # Upsert folder metadata and bulk sync associated file details.
        save_crawled_folder_metadata(
            engine=engine,
            fms_folders=fms_folders,
            fms_files=fms_files,
            env=env,
            domain=archive_name,
            folder_path=folder_path,
            folder_meta=folder_meta,
            files=files,
        )

    # Compile legacy crawl stats, print comparison report, and send metrics to Kestra.
    finalize_crawl_session(
        logger_instance=logger,
        env=env,
        domain_name=archive_name,
        all_env_file_details=all_env_file_details,
        api_requests=api_counter[0],
        title="LEGACY COMPARISON SUMMARY",
    )


def ingest_all_legacy_metadata(
    env: str | None = None,
    folders: list[str] | None = None,
    catalog_dir: Path | None = None,
) -> None:
    """Orchestrates metadata gathering for all three historical legacy releases.

    Args:
        env: Optional environment name override.
        folders: Optional pre-filtered list of legacy folders to process.
        catalog_dir: Optional custom catalog storage directory.
    """
    logger.info("Initializing metadata gathering for FMS Legacy Archives...")

    logger.info("Gathering Release 3 Archives (R3) metadata...")
    ingest_legacy_metadata("R3_Archives", env, folders, catalog_dir)

    logger.info("Gathering Release 2 Archives (R2) metadata...")
    ingest_legacy_metadata("R2_Archives", env, folders, catalog_dir)

    logger.info("Gathering Release 1 Archives (R1 CSV/XML) metadata...")
    ingest_legacy_metadata("R1_Archives_CSV_XML", env, folders, catalog_dir)

    logger.info("=== LEGACY METADATA INGESTION SUCCESSFULLY COMPLETED ===")
