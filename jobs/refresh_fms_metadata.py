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

"""Orchestrator script to fully crawl the ENTSO-E FMS remote directories recursively, refreshing global catalogs."""

from __future__ import annotations

import argparse
import logging

from entsoe_pipeline import (
    RunsLogger,
    get_classifier_config,
    resolve_active_environment,
)
from entsoe_pipeline.fms_metadata.core import (
    ingest_all_legacy_metadata,
    ingest_domain_metadata,
    ingest_overview_metadata,
)
from entsoe_pipeline.fms_metadata.core.fms_metadata_delta import (
    run_delta_metadata_refresh,
)
from entsoe_pipeline.fms_metadata.core.fms_metadata_freshness import (
    get_stale_domain_folders,
    get_stale_legacy_folders,
)
from entsoe_pipeline.fms_metadata.ingestion.sizes_ingest import (
    ingest_all_catalog_sizes,
)
from entsoe_pipeline.logger import setup_logging
from entsoe_pipeline.preflight import run_prepare_landing_preflight
from entsoe_pipeline.preflight.core.check_db import verify_db_readiness

logger = logging.getLogger("entsoe_pipeline.jobs.refresh_fms_metadata")


def refresh_environment_metadata(
    env: str,
    is_test: bool = False,
    is_force: bool = False,
    domain_name: str | None = None,
) -> None:
    """Fully processes recursive metadata crawling for all domains and archives in the target environment.

    Each environment creates its own FMS client with an independent ThrottledSession
    instance (separate sliding-window queue). IOP and PROD can therefore be crawled
    concurrently without interfering with each other's rate limits.

    Args:
        env: The ENTSO-E environment identifier, either 'IOP' or 'PROD'.
        is_test: True if running in test mode (skips Transmission & Balancing).
        is_force: True if all folders must be re-scanned regardless of crawled_at freshness.
        domain_name: Specific domain to crawl. If None or 'ALL', crawls all active domains.
    """
    logger.info("=" * 60)
    logger.info(" REFRESHING METADATA CATALOG FOR ENVIRONMENT: %s", env.upper())
    logger.info("=" * 60)

    # Retrieve active domains from the classifier configuration.
    config = get_classifier_config()
    domains = config.domain_order
    if is_test:
        light_domains = ["Load", "Generation", "OtherMarketInformation"]
        domains = [d for d in domains if d in light_domains]
        logger.info("Running in test mode. Selected light domains: %s", domains)

    # If a specific active domain is specified, filter for it
    target_domain = domain_name.strip() if domain_name else "ALL"
    if target_domain.lower() not in ("all", "legacy"):
        domains = [d for d in domains if d.lower() == target_domain.lower()]
        if not domains:
            logger.info(
                "Domain '%s' is not active or available in this run mode.", domain_name
            )

    if target_domain.lower() != "legacy":
        for domain in domains:
            stale_folders = get_stale_domain_folders(domain, env, is_force)
            if not stale_folders:
                logger.info(
                    "All folders in domain '%s' are fresh. Skipping crawl.", domain
                )
                continue
            ingest_domain_metadata(domain_name=domain, env=env, folders=stale_folders)

    if target_domain.lower() in ("all", "legacy"):
        if not is_test:
            # Crawl legacy archives.
            legacy_archives = ["R3_Archives", "R2_Archives", "R1_Archives_CSV_XML"]
            stale_legacy_folders = []
            for archive in legacy_archives:
                stale_legacy_folders.extend(
                    get_stale_legacy_folders(archive, env, is_force)
                )

            if stale_legacy_folders:
                ingest_all_legacy_metadata(env=env, folders=stale_legacy_folders)
            else:
                logger.info("All legacy folders are fresh. Skipping legacy crawl.")
        else:
            logger.info("Skipping legacy archives in test mode.")

    logger.info("=" * 60)
    logger.info(" ENVIRONMENT %s CRAWL COMPLETED", env.upper())
    logger.info("=" * 60)


def main() -> None:
    """Entrypoint to execute the comprehensive FMS physical metadata crawler across IOP and PROD.

    Supports phase-based execution for Kestra orchestration:
      --phase prepare   → preflight checks + overview.yml
      --phase crawl     → recursive domain crawl for a single --env
      --phase finalize  → overview_tree.yml + sizes reports
    """
    setup_logging()
    parser = argparse.ArgumentParser(
        description="Comprehensive FMS physical metadata crawler runner."
    )
    parser.add_argument(
        "--phase",
        required=True,
        choices=["prepare", "crawl", "finalize"],
        help="Pipeline phase to execute (prepare | crawl | finalize).",
    )
    parser.add_argument(
        "--env",
        choices=["IOP", "PROD"],
        help="Target environment — required for the 'crawl' phase.",
    )
    parser.add_argument(
        "--domain",
        help="Specific domain to crawl (e.g. Load, Legacy, etc.) — defaults to ALL.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-scan of all folders, ignoring the crawled_at freshness threshold.",
    )
    parser.add_argument(
        "--full-scan",
        action="store_true",
        help="Force a full recursive crawl of all FMS directories instead of an incremental check.",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode (exclude heavy domains: Transmission, Balancing).",
    )
    args = parser.parse_args()

    active_env = args.env or resolve_active_environment()
    job_name = f"refresh_fms_metadata_{args.phase}"
    if args.env:
        job_name += f"_{args.env.lower()}"
    if args.domain:
        job_name += f"_{args.domain.lower()}"

    with RunsLogger(job_name=job_name, environment=active_env):
        if args.phase == "prepare":
            run_prepare_landing_preflight()
            verify_db_readiness()  # Explicitly duplicate: visible intent in this job.
            logger.info("=== STARTING GLOBAL FMS METADATA REFRESH JOB ===")
            logger.info(
                "Step 1: Refreshing root-level overview catalog (overview.yml)..."
            )
            ingest_overview_metadata()

        elif args.phase == "crawl":
            if not args.env:
                raise ValueError(
                    "--env (IOP or PROD) is required for the 'crawl' phase."
                )
            logger.info("Step 2: Crawling %s directories...", args.env)
            is_full = args.full_scan or args.force
            if is_full:
                logger.info(
                    "Full scan enabled — performing recursive crawl of all FMS directories."
                )
            run_delta_metadata_refresh(
                args.env,
                args.test,
                is_full,
                args.domain,
                full_scan_callback=refresh_environment_metadata,
            )
            logger.info("Environment %s crawl finished successfully.", args.env)

        elif args.phase == "finalize":
            logger.info("Step 3: Rebuilding global catalog sizes reports...")
            ingest_all_catalog_sizes()
            logger.info("=== GLOBAL FMS METADATA REFRESH COMPLETED ===")


if __name__ == "__main__":
    main()
