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

"""ENTSO-E FMS Domain-specific Metadata Ingestion Engine.

Orchestrates deep metadata gathering, physical size calculations, and catalog
persistence into the PostgreSQL database for specific data domains (e.g. Load).
"""

from __future__ import annotations

import logging

from typing import TYPE_CHECKING

from sqlalchemy import create_engine

from entsoe_pipeline import resolve_active_environment
from entsoe_pipeline.api import create_fms_client
from entsoe_pipeline.db import build_metadata, get_db_url
from entsoe_pipeline.fms_metadata.core.metadata_crawlers_common import (
    fetch_root_files_mapping,
    finalize_crawl_session,
    save_crawled_folder_metadata,
)
from entsoe_pipeline.fms_metadata.utils import crawl_metadata_folder
from entsoe_pipeline.fms_metadata.utils.overview_parser import get_domain_folders
from entsoe_pipeline.fms_metadata.utils.transformer import (
    compile_folder_metadata,
)

if TYPE_CHECKING:
    from pathlib import Path

# Setup scoped logger strictly to our package namespace to prevent polluting root.
logger = logging.getLogger("entsoe_pipeline.fms_metadata.core.domain_metadata_crawler")


def ingest_domain_metadata(
    domain_name: str,
    env: str | None = None,
    folders: list[str] | None = None,
    catalog_dir: Path | None = None,
) -> None:
    """Orchestrates metadata gathering for any specified FMS domain in the active environment.

    Crawls directories sequentially on FMS and persists folder stats and file Details
    atomically per folder to PostgreSQL.

    Args:
        domain_name: The target ENTSO-E data domain (e.g. 'Load', 'Market').
        env: Optional environment name. If None, resolves dynamically.
        folders: Optional pre-filtered list of folders to process.
        catalog_dir: Optional custom catalog storage directory (unused, kept for API parity).
    """
    del catalog_dir  # Unused parameter kept for compatibility with callers.
    logger.info(
        "=== STARTING %s METADATA EXPLORATION ===",
        domain_name.upper(),
    )

    if env is None:
        env = resolve_active_environment()

    logger.info("-" * 60)
    logger.info("PROCESSING ENVIRONMENT: %s", env)
    logger.info("-" * 60)

    # Retrieve domain folders dynamically from overview.yml SSOT if not specified.
    if folders is None:
        try:
            folders = get_domain_folders(domain_name, env)
        except Exception:
            logger.exception(
                "Failed to retrieve domain folders for %s on env %s",
                domain_name,
                env,
            )
            return

    # Track FMS requests count for watermarking audits.
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

    # Fetch root raw items once to dynamically catalog root-level files (like CSVs).
    root_files_by_name = fetch_root_files_mapping(
        client, api_counter, env, root_dir="TP_export"
    )

    for folder in folders:
        logger.info("Processing folder: %s", folder)
        try:
            files = crawl_metadata_folder(
                client=client,
                folder=folder,
                root_files_by_name=root_files_by_name,
                api_counter=api_counter,
                env=env,
                root_dir="TP_export",
            )
        except Exception:
            logger.exception("Error crawling folder %s on environment %s", folder, env)
            continue

        # Aggregate physical stats dynamically via aggregates compiler.
        folder_meta = compile_folder_metadata(folder, files)
        folder_path = folder_meta["folder_path"]
        all_env_file_details.extend(files)

        # Upsert folder metadata and bulk sync associated file details.
        save_crawled_folder_metadata(
            engine=engine,
            fms_folders=fms_folders,
            fms_files=fms_files,
            env=env,
            domain=domain_name,
            folder_path=folder_path,
            folder_meta=folder_meta,
            files=files,
        )

    # Compile environmental statistics, print high-level comparative report, and send metrics.
    finalize_crawl_session(
        logger_instance=logger,
        env=env,
        domain_name=domain_name,
        all_env_file_details=all_env_file_details,
        api_requests=api_counter[0],
        title="ENVIRONMENT COMPARISON SUMMARY",
    )
