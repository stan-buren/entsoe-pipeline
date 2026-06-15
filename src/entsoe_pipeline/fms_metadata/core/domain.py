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
generation for specific data domains (e.g. Load, Market) across environments.
"""

from __future__ import annotations

import logging

from entsoe_pipeline import PHYSICAL_CATALOG_DIR, get_config
from entsoe_pipeline.api import create_fms_client, list_folder_raw_items
from entsoe_pipeline.fms_metadata.utils.overview_parser import get_domain_folders
from entsoe_pipeline.fms_metadata.utils.serializer import save_fms_catalog
from entsoe_pipeline.fms_metadata.utils.transformer import (
    compile_env_stats,
    compile_folder_metadata,
    map_raw_fms_item,
)

# Setup scoped logger strictly to our package namespace to prevent polluting root
logger = logging.getLogger("entsoe_pipeline.fms_metadata.core.domain")


def ingest_domain_metadata(domain_name: str) -> None:
    """Orchestrates metadata gathering for any specified FMS domain in the active environment.

    Args:
        domain_name: The target ENTSO-E data domain (e.g. 'Load', 'Market').
    """
    logger.info(
        "=== STARTING %s METADATA EXPLORATION ===",
        domain_name.upper(),
    )

    env = get_config().active_environment

    logger.info("-" * 60)
    logger.info("PROCESSING ENVIRONMENT: %s", env)
    logger.info("-" * 60)

    # Retrieve domain folders dynamically from overview.yml SSOT
    try:
        folders = get_domain_folders(domain_name, env)
    except Exception:
        logger.exception(
            "Failed to retrieve domain folders for %s on env %s",
            domain_name,
            env,
        )
        return

    # Track FMS requests count for watermarking audits
    api_counter = [0]

    try:
        client = create_fms_client(env)
    except Exception:
        logger.exception("Failed to initialize FMS client for environment %s", env)
        return

    domain_metadata = {}
    all_env_file_details = []

    # Fetch root raw items once to dynamically catalog root-level files (like CSVs)
    try:
        root_raw_items = list_folder_raw_items(client, "", api_counter)
        root_files_by_name = {item["name"]: item for item in root_raw_items}
    except Exception:
        logger.exception("Failed to fetch root items for environment %s", env)
        root_files_by_name = {}

    for folder in folders:
        logger.info("Processing folder: %s", folder)
        try:
            if folder.endswith(".csv"):
                # Root file. Retrieve its pre-fetched metadata dict.
                raw_item = root_files_by_name.get(folder)
                if raw_item:
                    files = [map_raw_fms_item(raw_item)]
                else:
                    logger.warning(
                        "Root file '%s' not found in root items on env %s",
                        folder,
                        env,
                    )
                    files = []
            else:
                # Regular directory. Crawl FMS items via Layer 2 API
                raw_items = list_folder_raw_items(client, folder, api_counter)
                files = [map_raw_fms_item(item) for item in raw_items]
        except Exception:
            logger.exception("Error crawling folder %s on environment %s", folder, env)
            continue

        # Aggregate physical stats dynamically via Layer 3 aggregates compiler
        domain_metadata[folder] = compile_folder_metadata(folder, files)
        all_env_file_details.extend(files)

    # Serialize results cleanly to the correct subdirectory conforming to paths SSOT
    output_path = (
        PHYSICAL_CATALOG_DIR / env.lower() / "TP_export" / f"{domain_name}.yml"
    )
    logger.info("Persisting %s metadata to: %s", env, output_path)

    # Save catalog gracefully using our common serialization helper
    save_fms_catalog(output_path, api_counter[0], domain_metadata)

    # Compile environmental statistics for comparative summaries
    stats = compile_env_stats(env, all_env_file_details, api_counter[0])

    # Print high-level comparative report
    logger.info("=" * 60)
    logger.info("             ENVIRONMENT COMPARISON SUMMARY        ")
    logger.info("=" * 60)
    logger.info(
        "%-8s | %-12s | %-10s | %-10s | %-12s | %-10s",
        "Env",
        "Files Count",
        "Orig (MB)",
        "Comp (MB)",
        "Date Range",
        "API Calls",
    )
    logger.info("-" * 75)

    logger.info(
        "%-8s | %-12d | %-10.2f | %-10.2f | %-12s | %-10d",
        env,
        stats["file_count"],
        stats["original_mb"],
        stats["compressed_mb"],
        stats["date_range"],
        stats["api_requests"],
    )
    logger.info("=" * 60)
