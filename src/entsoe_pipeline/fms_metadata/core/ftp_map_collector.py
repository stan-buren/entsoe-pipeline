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

"""ENTSO-E FMS Remote Metadata Discovery and Ingestion Engine.

Handles FMS global overview metadata collection across platforms (IOP and PROD)
by crawling active and legacy directories, grouping folders by domain,
and persisting the overview.yml catalog.
"""

from __future__ import annotations

import logging

from typing import Any

from entsoe_pipeline import OVERVIEW_YML, get_classifier_config
from entsoe_pipeline.api import create_fms_client, ls_fms
from entsoe_pipeline.fms_metadata.core.domain_classifier import classify_folder
from entsoe_pipeline.fms_metadata.utils.serializer import save_yaml_catalog
from entsoe_pipeline.logger.core.generated_at import (
    get_generated_at_timestamp as get_generation_timestamp,
)

# Setup scoped logger strictly to our package namespace to prevent polluting root
logger = logging.getLogger("entsoe_pipeline.fms_metadata.core.ftp_map_collector")


def fetch_environment_metadata(env_name: str) -> dict[str, Any]:
    """Connects to the requested platform and crawls remote directory structures.

    Args:
        env_name: The platform environment target name ('IOP' or 'PROD').

    Returns:
        Structured metadata dictionaries for active and legacy areas.
    """
    logger.info("Connecting to ENTSO-E FMS environment: %s", env_name)
    client = create_fms_client(env_name)

    # 1. Fetch Active Directories (/TP_export/)
    logger.info("Crawling active folders in /TP_export/ for %s...", env_name)
    active_folders = ls_fms(client, "/TP_export/")

    # 2. Fetch Legacy Publications (/TP_Legacy_Publications/)
    logger.info(
        "Crawling legacy folders in /TP_Legacy_Publications/ for %s...",
        env_name,
    )
    legacy_folders = ls_fms(client, "/TP_Legacy_Publications/")

    grouped_domains: dict[str, list[str]] = {
        domain: [] for domain in get_classifier_config().domain_order
    }
    for folder in active_folders:
        domain = classify_folder(folder)
        grouped_domains[domain].append(folder)

    # Sort each domain's folders alphabetically
    for folders in grouped_domains.values():
        folders.sort()

    # Format into root_directories list conforming to overview.yml layout
    return {
        "description": (
            "ENTSO-E Production Platform"
            if env_name == "PROD"
            else "ENTSO-E Integration/Test Platform"
        ),
        "root_directories": [
            {
                "name": "TP_export",
                "description": "Active publications folder",
                "item_count": len(active_folders),
                "domains": grouped_domains,
            },
            {
                "name": "TP_Legacy_Publications",
                "description": "Legacy publications folder",
                "item_count": len(legacy_folders),
                "folders": sorted(legacy_folders),
            },
        ],
    }


def ingest_overview_metadata() -> None:
    """Orchestrates FMS metadata collection from IOP and PROD, updating overview.yml."""
    logger.info("=== STARTING ENTSO-E FMS METADATA DISCOVERY ===")

    # Crawl both Integration (IOP) and Production (PROD) platforms
    iop_metadata = fetch_environment_metadata("IOP")
    prod_metadata = fetch_environment_metadata("PROD")

    # Combine into standard overview schema
    overview_data = {
        "generated_at": get_generation_timestamp(),
        "environments": {
            "IOP": iop_metadata,
            "Prod": prod_metadata,
        },
    }

    # Write out to the SSOT file location in beautiful block YAML format
    logger.info("Writing structured metadata to: %s", OVERVIEW_YML)
    save_yaml_catalog(OVERVIEW_YML, overview_data)

    # --- Metadata Drift Detection ---
    logger.info("Performing metadata drift detection check...")
    config = get_classifier_config()

    # 1. Collect all active folders discovered on FTP across both platforms
    all_active_folders = set()
    for root_dir in iop_metadata.get("root_directories", []):
        if root_dir.get("name") == "TP_export":
            for domain_folders in root_dir.get("domains", {}).values():
                all_active_folders.update(domain_folders)
    for root_dir in prod_metadata.get("root_directories", []):
        if root_dir.get("name") == "TP_export":
            for domain_folders in root_dir.get("domains", {}).values():
                all_active_folders.update(domain_folders)

    # 2. Identify undocumented folders (FMS-only, missing from classifier config)
    undocumented_folders = []
    matched_fms_names = set()
    for folder in sorted(all_active_folders):
        folder_lower = folder.lower()
        matched = False
        for domain, items in config.domains.items():
            for key, item in items.items():
                fms_prefix = item.fms_name.lower()
                if folder_lower.startswith(fms_prefix):
                    matched = True
                    matched_fms_names.add(item.fms_name)
                    break
            if matched:
                break
        if not matched:
            undocumented_folders.append(folder)

    # 3. Identify unseen publications (Zendesk-only, missing from FMS directories)
    unseen_publications = []
    for domain, items in config.domains.items():
        for key, item in items.items():
            if item.fms_name not in matched_fms_names:
                unseen_publications.append(
                    {
                        "domain": domain,
                        "key": key,
                        "name": item.name,
                        "fms_name": item.fms_name,
                    }
                )

    # Save drift detection outputs using paths SSOT
    from entsoe_pipeline.config.paths import ACTIVE_FMS_METADATA_DIR

    ACTIVE_FMS_METADATA_DIR.mkdir(parents=True, exist_ok=True)

    undocumented_file = ACTIVE_FMS_METADATA_DIR / "undocumented_folders.yml"
    unseen_file = ACTIVE_FMS_METADATA_DIR / "unseen_publications.yml"

    logger.info("Saving undocumented folders drift report to: %s", undocumented_file)
    save_yaml_catalog(
        undocumented_file,
        {
            "generated_at": get_generation_timestamp(),
            "item_count": len(undocumented_folders),
            "folders": undocumented_folders,
        },
    )

    logger.info("Saving unseen publications drift report to: %s", unseen_file)
    save_yaml_catalog(
        unseen_file,
        {
            "generated_at": get_generation_timestamp(),
            "item_count": len(unseen_publications),
            "publications": unseen_publications,
        },
    )

    logger.info("=== METADATA INGESTION SUCCESSFULLY COMPLETED ===")
