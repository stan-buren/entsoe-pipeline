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
and structured catalog creation for Release 1, 2, and 3 publications.
"""

from __future__ import annotations

import logging

from entsoe_pipeline import PHYSICAL_CATALOG_DIR, get_classifier_config, get_config
from entsoe_pipeline.api import (
    create_fms_client,
    list_folder_raw_items,
    list_folder_raw_items_recursive,
)
from entsoe_pipeline.fms_metadata.core.generation_data import get_generation_timestamp
from entsoe_pipeline.fms_metadata.utils.overview_parser import (
    get_legacy_archive_folders,
)
from entsoe_pipeline.fms_metadata.utils.serializer import save_yaml_catalog
from entsoe_pipeline.fms_metadata.utils.transformer import (
    compile_env_stats,
    compile_folder_metadata,
    map_raw_fms_item,
)

logger = logging.getLogger("entsoe_pipeline.fms_metadata.core.legacy")


def ingest_legacy_metadata(archive_name: str) -> None:
    """Orchestrates FMS metadata gathering for a specified historical archive in the active environment.

    Args:
        archive_name: The legacy archive key (e.g. 'R3_Archives', 'R2_Archives').
    """
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
            "Legacy archive rule '%s' not found in classifier config", archive_name
        )
        return

    env = get_config().active_environment

    logger.info("-" * 60)
    logger.info("PROCESSING LEGACY ENVIRONMENT: %s", env)
    logger.info("-" * 60)

    # Retrieve specific archive folders matching the classifier specifications
    try:
        folders = get_legacy_archive_folders(archive_name, env)
    except Exception:
        logger.exception(
            "Failed to retrieve legacy folders for %s on env %s",
            archive_name,
            env,
        )
        return

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
        root_raw_items = list_folder_raw_items(
            client, "", api_counter, root_dir="TP_Legacy_Publications"
        )
        root_files_by_name = {item["name"]: item for item in root_raw_items}
    except Exception:
        logger.exception("Failed to fetch root items for environment %s", env)
        root_files_by_name = {}

    for folder in folders:
        logger.info("Processing legacy folder: %s", folder)
        try:
            if folder.endswith(".csv"):
                # Root-level legacy file. Retrieve pre-fetched metadata.
                raw_item = root_files_by_name.get(folder)
                if raw_item:
                    files = [map_raw_fms_item(raw_item)]
                else:
                    logger.warning(
                        "Root legacy file '%s' not found on env %s",
                        folder,
                        env,
                    )
                    files = []
            else:
                # Regular directory. Crawl FMS items recursively via Layer 2 API
                raw_items = list_folder_raw_items_recursive(
                    client, folder, api_counter, root_dir="TP_Legacy_Publications"
                )
                files = [map_raw_fms_item(item) for item in raw_items]
        except Exception:
            logger.exception(
                "Error crawling legacy folder %s on environment %s", folder, env
            )
            continue

        # Aggregate physical stats dynamically via Layer 3 aggregates compiler
        domain_metadata[folder] = compile_folder_metadata(
            folder, files, root_dir="TP_Legacy_Publications"
        )
        all_env_file_details.extend(files)

    # Output to target legacy catalog subdirectory
    output_path = (
        PHYSICAL_CATALOG_DIR
        / env.lower()
        / "TP_Legacy_Publications"
        / f"{archive_name}.yml"
    )
    logger.info("Persisting legacy %s metadata to: %s", env, output_path)

    current_time_utc = get_generation_timestamp()
    payload = {
        "generated_at": current_time_utc,
        "total_api_requests": api_counter[0],
        "folders": domain_metadata,
    }

    save_yaml_catalog(output_path, payload)

    stats = compile_env_stats(
        env, all_env_file_details, api_counter[0]
    )

    # Print high-level comparative report
    logger.info("=" * 60)
    logger.info("         LEGACY COMPARISON SUMMARY    ")
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
