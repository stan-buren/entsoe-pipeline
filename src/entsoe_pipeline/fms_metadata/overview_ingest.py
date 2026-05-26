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

"""ENTSO-E FMS Remote Metadata Discovery and Ingestion Module.

This script acts as the automated orchestrator to query both the Integration (IOP)
and Production (PROD) platforms, retrieve remote directory structures, classify
active folders into standardized ENTSO-E data domains, and persist the results
cleanly into the central `overview.yml` file.
"""

from __future__ import annotations

import logging

from typing import Any

import yaml

from entsoe_pipeline.api import create_fms_client, ls_fms
from entsoe_pipeline.config.paths import OVERVIEW_YML
from entsoe_pipeline.logger import setup_logging

logger = logging.getLogger("entsoe_pipeline.fms_metadata.overview_ingest")


# =============================================================================
# DOMAIN SCHEMA CONSTANTS
# =============================================================================

_DOMAIN_ORDER = [
    "Load",
    "Generation",
    "Transmission",
    "Balancing",
    "Market",
    "Outages",
    "Operations",
    "OtherMarketInformation",
]


# =============================================================================
# DOMAIN CLASSIFICATION LOGIC
# =============================================================================


def classify_folder(folder_name: str) -> str:
    """Classifies an ENTSO-E active folder name into its specific analytical domain.

    Utilizes descriptive pattern matching on the folder name string to assign
    the folder to one of the 8 core ENTSO-E data domains.

    Args:
        folder_name: Remote FMS directory name (e.g. 'ActualTotalLoad_6.1.A_r3').

    Returns:
        str: The assigned domain name (e.g. 'Load', 'Transmission').
    """
    name_lower = folder_name.lower()

    # 1. Outages (takes precedence to avoid classification collisions)
    if "unavailability" in name_lower or "outage" in name_lower:
        return "Outages"

    # 2. Load
    if "load" in name_lower or "forecastmargin" in name_lower:
        return "Load"

    # 3. Generation
    if any(
        term in name_lower
        for term in [
            "generation",
            "fillingrate",
            "hydrostorage",
            "productionandgeneration",
        ]
    ):
        return "Generation"

    # 4. Balancing (exclude operational activation features)
    if any(
        term in name_lower
        for term in [
            "balancing",
            "imbalance",
            "nettedandexchanged",
            "bidavailability",
            "procuredbalancing",
            "mfrr",
            "afrr",
        ]
    ):
        if "marginalprice" in name_lower or "activationoptimisation" in name_lower:
            return "Operations"
        return "Balancing"

    # 5. Operations (SOGL grid limits, countertrading, redispatching)
    if any(
        term in name_lower
        for term in [
            "redispatching",
            "countertrading",
            "algorithm",
            "methodology",
            "methodologies",
            "annualreport",
            "criteriaapplication",
            "sogl",
            "fallback",
            "elasticdemand",
            "frequencycontainment",
            "permanentallocation",
        ]
    ):
        return "Operations"

    # 6. Market (auctions, prices, structural projects)
    if any(
        term in name_lower
        for term in [
            "auction",
            "congestionmanagement",
            "price",
            "prices",
            "dismantling",
        ]
    ):
        return "Market"

    # 7. Transmission (capacities, physical flows, net positions, schedules)
    if any(
        term in name_lower
        for term in [
            "transfercapacities",
            "physicalflows",
            "schedule",
            "schedules",
            "flowbased",
            "implicitallocations",
            "nominated",
            "crossbordercapacity",
            "transmissionassets",
            "distributionfactors",
            "useoftransfercapacity",
        ]
    ):
        return "Transmission"

    # Special context checks for 'capacity'
    if "capacity" in name_lower:
        if "generation" in name_lower or "production" in name_lower:
            return "Generation"
        return "Transmission"

    # 8. Fallback Default
    logger.debug("Folder '%s' fell back to 'OtherMarketInformation'", folder_name)
    return "OtherMarketInformation"


# =============================================================================
# METADATA EXTRACTION & WRITER CORE
# =============================================================================


def fetch_environment_metadata(env_name: str) -> dict[str, Any]:
    """Connects to the requested platform and crawls remote directory structures.

    Args:
        env_name: The platform environment target name ('IOP' or 'PROD').

    Returns:
        Dict[str, Any]: Structured metadata dictionaries for active and legacy areas.
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

    # 3. Classify and group active folders
    grouped_domains: dict[str, list[str]] = {domain: [] for domain in _DOMAIN_ORDER}
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


class IndentedSafeDumper(yaml.SafeDumper):
    """Custom YAML SafeDumper that forces indentation for sequence (list) items.

    Ensures that sequence items (prefixed by '-') are indented relative to their
    parent mapping keys, improving overall human readability and aligning
    with standard IDE auto-formatting configurations.
    """

    def increase_indent(
        self,
        flow: bool = False,
        indentless: bool = False,  # noqa: ARG002
    ) -> Any:
        """Forces indentless sequences to be indented."""
        return super().increase_indent(flow, indentless=False)


def ingest_fms_metadata() -> None:
    """Orchestrates FMS metadata collection from IOP and PROD, updating overview.yml."""
    logger.info("=== STARTING ENTSO-E FMS METADATA DISCOVERY ===")

    # Crawl both Integration (IOP) and Production (PROD) platforms
    iop_metadata = fetch_environment_metadata("IOP")
    prod_metadata = fetch_environment_metadata("PROD")

    # Combine into standard overview schema
    overview_data = {
        "environments": {
            "IOP": iop_metadata,
            "Prod": prod_metadata,
        }
    }

    # Write out to the SSOT file location in beautiful block YAML format
    logger.info("Writing structured metadata to: %s", OVERVIEW_YML)
    with OVERVIEW_YML.open("w", encoding="utf-8") as f:
        yaml.dump(
            overview_data,
            f,
            Dumper=IndentedSafeDumper,
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
            indent=2,
        )

    logger.info("=== METADATA INGESTION SUCCESSFULLY COMPLETED ===")


# =============================================================================
# SCRIPT RUNNER ENTRYPOINT
# =============================================================================

if __name__ == "__main__":
    # Configure logging for the pipeline environment prior to execution
    setup_logging(level=logging.INFO, use_json=False)
    try:
        ingest_fms_metadata()
    except Exception:
        logger.exception("Metadata ingestion aborted due to fatal error")
        raise
