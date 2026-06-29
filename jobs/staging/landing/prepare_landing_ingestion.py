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

"""Orchestrator script to refresh metadata catalogs and generate configurations before landing zone ingestion."""

from __future__ import annotations

import logging

import yaml

from entsoe_pipeline import (
    MY_ENTSOE_DOMAINS_YML,
    resolve_active_environment,
)
from entsoe_pipeline.fms_metadata.ingestion import (
    ingest_all_legacy_metadata,
    ingest_balancing_metadata,
    ingest_fms_metadata,
    ingest_fms_overview_tree,
    ingest_generation_metadata,
    ingest_load_metadata,
    ingest_market_metadata,
    ingest_operations_metadata,
    ingest_other_market_information_metadata,
    ingest_outages_metadata,
    ingest_transmission_metadata,
)
from entsoe_pipeline.fms_metadata.ingestion.landing_bucket_schema import (
    build_landing_bucket_schema,
)
from entsoe_pipeline.fms_metadata.ingestion.my_entsoe_domains import (
    generate_my_entsoe_domains,
)
from entsoe_pipeline.logger import setup_logging
from entsoe_pipeline.preflight import run_prepare_landing_preflight

logger = logging.getLogger("entsoe_pipeline.jobs.prepare_landing_ingestion")


def main() -> None:
    """Prepares metadata and active configurations for the configured deployment environment."""
    setup_logging()
    run_prepare_landing_preflight()
    logger.info("=== STARTING INGESTION PREPARATION JOB ===")

    # 1. Refresh global overview catalog (discovers directories & files list)
    logger.info("Step 1: Refreshing global overview metadata catalog (overview.yml)...")
    ingest_fms_metadata()

    # 2. Generate initial active domains configuration checklist (my_entsoe_domains.yml)
    logger.info(
        "Step 2: Compiling active domains configuration checklist (my_entsoe_domains.yml)..."
    )
    generate_my_entsoe_domains()

    # 4. Resolve configured active domains for active environment
    if not MY_ENTSOE_DOMAINS_YML.exists():
        raise FileNotFoundError(
            f"Checklist configuration file not found at: {MY_ENTSOE_DOMAINS_YML}"
        )

    with MY_ENTSOE_DOMAINS_YML.open(encoding="utf-8") as f:
        domains_data = yaml.safe_load(f) or {}

    active_env = resolve_active_environment()
    logger.info("Targeting active environment: %s", active_env)

    environments = domains_data.get("environments", {})
    # Case-insensitive environment lookup
    env_key = next((k for k in environments if k.upper() == active_env.upper()), None)

    active_domains: set[str] = set()
    active_legacy = False

    if env_key:
        env_config = environments[env_key]
        root_dirs = env_config.get("root_directories", [])
        for root_dir in root_dirs:
            root_name = root_dir.get("name", "")
            if root_name == "TP_export":
                domains_dict = root_dir.get("domains", {})
                for dom_name, dom_val in domains_dict.items():
                    is_active = False
                    if isinstance(dom_val, dict):
                        for sub_val in dom_val.values():
                            if sub_val is True or (
                                isinstance(sub_val, list) and len(sub_val) > 0
                            ):
                                is_active = True
                                break
                    elif dom_val is True or (
                        isinstance(dom_val, list) and len(dom_val) > 0
                    ):
                        is_active = True

                    if is_active:
                        active_domains.add(dom_name)
            elif root_name == "TP_Legacy_Publications":
                folders_dict = root_dir.get("folders", {})
                for fold_val in folders_dict.values():
                    if fold_val is True or (
                        isinstance(fold_val, list) and len(fold_val) > 0
                    ):
                        active_legacy = True
                        break

    logger.info("Resolved active domains: %s", list(active_domains))
    logger.info("Resolved active legacy: %s", active_legacy)

    # 5. Run physical metadata crawlers ONLY for active domains
    logger.info("Step 4: Executing metadata crawlers for active domains/folders...")
    domain_ingest_mappers = {
        "load": ingest_load_metadata,
        "generation": ingest_generation_metadata,
        "transmission": ingest_transmission_metadata,
        "balancing": ingest_balancing_metadata,
        "market": ingest_market_metadata,
        "operations": ingest_operations_metadata,
        "outages": ingest_outages_metadata,
        "othermarketinformation": ingest_other_market_information_metadata,
    }

    for dom in active_domains:
        normalized_key = dom.lower().replace("_", "")
        ingest_func = domain_ingest_mappers.get(normalized_key)
        if ingest_func:
            logger.info("Executing crawler for active domain: %s", dom)
            ingest_func(active_env)
        else:
            logger.warning("No crawler mapping found for active domain: %s", dom)

    if active_legacy:
        logger.info("Executing crawler for legacy publications folders...")
        ingest_all_legacy_metadata(active_env)

    # 6. Compile hierarchical directory layout tree from updated physical catalog
    logger.info("Step 5: Compiling global layout tree catalog (overview_tree.yml)...")
    ingest_fms_overview_tree()

    # 7. Compile the S3 landing bucket schema contract
    logger.info(
        "Step 6: Compiling landing bucket directory schema (entsoe_fms_folder_schema.yml)..."
    )
    build_landing_bucket_schema()

    logger.info("=== INGESTION PREPARATION JOB SUCCESSFUL ===")


if __name__ == "__main__":
    main()
