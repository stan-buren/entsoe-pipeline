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

"""ENTSO-E FMS Metadata Unified Ingestion CLI Module.

Acts as the centralized application executor for metadata collection across
all analytical domains (Load, Generation, Balancing, etc.) and historical archives
declared in the classifier configuration files.
"""

from __future__ import annotations

import argparse
import logging

from entsoe_pipeline import (
    get_classifier_config,
    resolve_active_environment,
    setup_logging,
)
from entsoe_pipeline.fms_metadata.core import (
    ingest_all_legacy_metadata,
    ingest_domain_metadata,
)
from entsoe_pipeline.fms_metadata.core.fms_metadata_freshness import (
    get_stale_domain_folders,
    get_stale_legacy_folders,
)

logger = logging.getLogger("entsoe_pipeline.fms_metadata.ingestion.fms_metadata_ingest")


def ingest_metadata(
    domain: str, env: str | None = None, is_test: bool = False, is_force: bool = False
) -> None:
    """Orchestrates FMS metadata gathering for a target domain or archive.

    Resolves folder listings and filters out fresh folders at the orchestrator level
    before executing the crawling engines.

    Args:
        domain: The specific domain to ingest (e.g. 'Load', 'Legacy', or 'ALL').
        env: Optional environment override ('IOP' or 'PROD').
        is_test: True if running in test mode (skips Transmission & Balancing).
        is_force: True to bypass freshness checks and re-scan all folders.

    Raises:
        ValueError: If the specified domain is not found in the configuration
            or if trying to crawl a heavy domain in test mode.
    """
    if env is None:
        env = resolve_active_environment()

    target_env = env.upper()
    logger.info("Initializing metadata collection for env: %s", target_env)

    # Load active domains dynamically from configuration.
    config = get_classifier_config()
    active_domains = config.domain_order

    light_domains = ["Load", "Generation", "OtherMarketInformation"]

    target_domain = domain.strip()
    if target_domain.lower() == "all":
        # Ingest active domains (only light ones if in test mode).
        for dom in active_domains:
            if is_test and dom not in light_domains:
                logger.info("Skipping domain '%s' in test mode.", dom)
                continue

            stale_folders = get_stale_domain_folders(dom, target_env, is_force)
            if not stale_folders:
                logger.info(
                    "All folders in domain '%s' are fresh. Skipping crawl.", dom
                )
                continue

            ingest_domain_metadata(
                domain_name=dom, env=target_env, folders=stale_folders
            )

        if not is_test:
            legacy_archives = ["R3_Archives", "R2_Archives", "R1_Archives_CSV_XML"]
            stale_legacy_folders = []
            for archive in legacy_archives:
                stale_legacy_folders.extend(
                    get_stale_legacy_folders(archive, target_env, is_force)
                )

            if stale_legacy_folders:
                ingest_all_legacy_metadata(env=target_env, folders=stale_legacy_folders)
            else:
                logger.info("All legacy folders are fresh. Skipping legacy crawl.")

    elif target_domain.lower() == "legacy":
        if is_test:
            logger.info("Skipping legacy archives in test mode.")
            return

        legacy_archives = ["R3_Archives", "R2_Archives", "R1_Archives_CSV_XML"]
        stale_legacy_folders = []
        for archive in legacy_archives:
            stale_legacy_folders.extend(
                get_stale_legacy_folders(archive, target_env, is_force)
            )

        if stale_legacy_folders:
            ingest_all_legacy_metadata(env=target_env, folders=stale_legacy_folders)
        else:
            logger.info("All legacy folders are fresh. Skipping legacy crawl.")

    else:
        # Resolve domains case-insensitively from the configuration registry.
        matched_dom = next(
            (d for d in active_domains if d.lower() == target_domain.lower()),
            None,
        )
        if not matched_dom:
            raise ValueError(
                f"Unknown domain: '{domain}'. Must be one of: {active_domains} "
                "or 'Legacy', 'ALL'."
            )
        if is_test and matched_dom not in light_domains:
            raise ValueError(
                f"Cannot ingest domain '{matched_dom}' in test mode. "
                f"Allowed test domains: {light_domains}"
            )

        stale_folders = get_stale_domain_folders(matched_dom, target_env, is_force)
        if not stale_folders:
            logger.info(
                "All folders in domain '%s' are fresh. Skipping crawl.", matched_dom
            )
            return

        ingest_domain_metadata(
            domain_name=matched_dom, env=target_env, folders=stale_folders
        )


def main() -> None:
    """Main command line entrypoint for metadata ingestion."""
    setup_logging()
    parser = argparse.ArgumentParser(
        description="Consolidated ENTSO-E FMS Metadata Ingestion runner."
    )
    parser.add_argument(
        "--domain",
        required=True,
        help="Target domain to crawl (e.g. Load, Balancing, Legacy, ALL).",
    )
    parser.add_argument(
        "--env",
        choices=["IOP", "PROD"],
        help="Environment override (if omitted, resolved from environment config).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-scan of all folders, ignoring crawled_at freshness checks.",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode (exclude heavy domains: Transmission, Balancing).",
    )

    args = parser.parse_args()

    try:
        ingest_metadata(
            domain=args.domain, env=args.env, is_test=args.test, is_force=args.force
        )
    except Exception:
        logger.exception("Metadata ingestion job failed.")
        raise


if __name__ == "__main__":
    main()
