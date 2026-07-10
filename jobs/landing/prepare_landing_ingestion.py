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
    ACTIVE_PHYSICAL_CATALOG_DIR,
    ACTIVE_SIZES_DIR,
    MY_ENTSOE_DOMAINS_YML,
    RunsLogger,
    resolve_active_environment,
)
from entsoe_pipeline.fms_metadata.core import (
    ingest_all_legacy_metadata,
    ingest_domain_metadata,
)
from entsoe_pipeline.fms_metadata.ingestion import (
    ingest_all_catalog_sizes,
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

    active_env = resolve_active_environment()
    logger.info("Targeting active environment: %s", active_env)

    with RunsLogger(job_name="prepare_landing_ingestion", environment=active_env):
        # 1. Generate initial active domains configuration checklist (my_entsoe_domains.yml)
        # Note: We do NOT refresh the global overview.yml here anymore.
        # overview.yml is refreshed by the heavy refresh_fms_metadata.py job.
        logger.info(
            "Step 1: Compiling active domains configuration checklist (my_entsoe_domains.yml)..."
        )
        generate_my_entsoe_domains()

        # 2. Resolve configured active domains/folders for active environments
        if not MY_ENTSOE_DOMAINS_YML.exists():
            raise FileNotFoundError(
                f"Checklist configuration file not found at: {MY_ENTSOE_DOMAINS_YML}"
            )

        with MY_ENTSOE_DOMAINS_YML.open(encoding="utf-8") as f:
            domains_data = yaml.safe_load(f) or {}

        environments = domains_data.get("environments", {})

        envs_to_prepare = []
        for env_name in environments:
            from entsoe_pipeline.io.core.config_parser import extract_active_folders

            if extract_active_folders(env_name, domains_data):
                envs_to_prepare.append(env_name)

        if not envs_to_prepare:
            envs_to_prepare = [resolve_active_environment()]

        logger.info(
            "Environments selected for metadata preparation: %s", envs_to_prepare
        )

        # 3. Clean active physical catalog directory to ensure no stale configuration
        # files from previous ingestion setup runs remain in this run path.
        if ACTIVE_PHYSICAL_CATALOG_DIR.exists():
            import shutil

            logger.info("Cleaning old active physical catalog storage...")
            shutil.rmtree(ACTIVE_PHYSICAL_CATALOG_DIR)
        ACTIVE_PHYSICAL_CATALOG_DIR.mkdir(parents=True, exist_ok=True)

        # 4. Run physical metadata crawlers for each selected environment
        logger.info("Step 2: Executing metadata crawlers for active domains/folders...")

        for env in envs_to_prepare:
            logger.info("=== Preparing metadata for environment: %s ===", env)
            env_key = next((k for k in environments if k.upper() == env.upper()), None)
            if not env_key:
                continue

            env_config = environments[env_key]
            active_folders_by_domain: dict[str, list[str]] = {}
            active_legacy_folders: list[str] = []

            root_dirs = env_config.get("root_directories", [])
            for root_dir in root_dirs:
                root_name = root_dir.get("name", "")
                if root_name == "TP_export":
                    domains_dict = root_dir.get("domains", {})
                    for dom_name, dom_val in domains_dict.items():
                        folders = []
                        if isinstance(dom_val, dict):
                            for sub_key, sub_val in dom_val.items():
                                if sub_val is True or (
                                    isinstance(sub_val, list) and len(sub_val) > 0
                                ):
                                    folders.append(sub_key)
                        elif (
                            dom_val is True
                            or (isinstance(dom_val, list) and len(dom_val) > 0)
                        ) and isinstance(dom_val, list):
                            folders.extend(dom_val)
                        if folders:
                            active_folders_by_domain[dom_name] = folders
                elif root_name == "TP_Legacy_Publications":
                    folders_dict = root_dir.get("folders", {})
                    for fold_key, fold_val in folders_dict.items():
                        if fold_val is True or (
                            isinstance(fold_val, list) and len(fold_val) > 0
                        ):
                            active_legacy_folders.append(fold_key)

            logger.info(
                "[%s] Resolved active domains & folders: %s",
                env,
                active_folders_by_domain,
            )
            logger.info(
                "[%s] Resolved active legacy folders: %s", env, active_legacy_folders
            )

            for dom, folders in active_folders_by_domain.items():
                logger.info(
                    "[%s] Executing crawler for active domain: %s (folders: %s)",
                    env,
                    dom,
                    folders,
                )
                ingest_domain_metadata(
                    domain_name=dom,
                    env=env,
                    folders=folders,
                    catalog_dir=ACTIVE_PHYSICAL_CATALOG_DIR,
                )

            if active_legacy_folders:
                logger.info(
                    "[%s] Executing crawler for active legacy publications folders...",
                    env,
                )
                ingest_all_legacy_metadata(
                    env=env,
                    folders=active_legacy_folders,
                    catalog_dir=ACTIVE_PHYSICAL_CATALOG_DIR,
                )

        # 5. Compile active hierarchical directory layout tree from active catalogs
        # 5. Compile the S3 landing bucket schema contract in database
        logger.info("Step 3: Compiling landing bucket directory schema in database...")
        build_landing_bucket_schema()

        # 7. Compile human-friendly size reports for active catalogs
        logger.info("Step 5: Compiling active catalog sizes reports...")
        if ACTIVE_SIZES_DIR.exists():
            import shutil

            logger.info("Cleaning old active sizes storage...")
            shutil.rmtree(ACTIVE_SIZES_DIR)
        ACTIVE_SIZES_DIR.mkdir(parents=True, exist_ok=True)

        ingest_all_catalog_sizes(
            physical_catalog_dir=ACTIVE_PHYSICAL_CATALOG_DIR,
            sizes_dir=ACTIVE_SIZES_DIR,
        )

        logger.info("=== INGESTION PREPARATION JOB SUCCESSFUL ===")


if __name__ == "__main__":
    main()
