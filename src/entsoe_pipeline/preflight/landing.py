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

"""Orchestrator script to execute preflight checks for landing stage jobs."""

from __future__ import annotations

import logging
import sys

from botocore.exceptions import ClientError

from entsoe_pipeline import get_config, resolve_active_environment
from entsoe_pipeline.lakehouse.core.s3_tree_builder import (
    ensure_bucket_exists,
    get_s3_client,
)
from entsoe_pipeline.lakehouse.generate_tree_for_my_entsoe_domains import (
    generate_tree_for_my_entsoe_domains,
)
from entsoe_pipeline.preflight.core.check_fms import verify_fms_readiness
from entsoe_pipeline.preflight.core.check_s3 import verify_s3_readiness

logger = logging.getLogger("entsoe_pipeline.preflight.landing")


def run_prepare_landing_preflight() -> None:
    """Orchestrates preflight checks for the metadata preparation stage.

    Validates that we can authenticate against both IOP and PROD Keycloak
    endpoints before starting the crawler process.
    """
    logger.info("Running pre-flight checks for metadata preparation stage...")

    # 1. Verify IOP FMS connectivity.
    try:
        verify_fms_readiness("IOP")
    except Exception as e:
        logger.exception(
            "Pre-flight check failed: FMS IOP authentication failed. Error: %s",
            e,
        )
        sys.exit(1)

    # 2. Verify PROD FMS connectivity.
    try:
        verify_fms_readiness("PROD")
    except Exception as e:
        logger.exception(
            "Pre-flight check failed: FMS PROD authentication failed. Error: %s",
            e,
        )
        sys.exit(1)

    logger.info("Metadata preparation pre-flight checks passed successfully.")


def run_ingest_landing_preflight() -> None:
    """Orchestrates preflight checks for the landing ingestion stage.

    Initializes on-demand S3 structures, validates S3 read/write permissions,
    and validates active environment FMS API connection before sync takeoff.
    """
    logger.info("Running pre-flight checks for landing ingestion stage...")

    # 1. Initialize active S3 folder structures (on-demand tree creation).
    logger.info("Initializing active S3 folder structures...")
    generate_tree_for_my_entsoe_domains()

    # 2. Verify S3 storage connectivity and permissions.
    config = get_config()
    bucket_name = config.buckets.s3_landing_bucket
    client = get_s3_client()

    try:
        ensure_bucket_exists(client, bucket_name)
    except ClientError as e:
        logger.exception(
            "Pre-flight check failed: Landing bucket is not accessible. Error: %s",
            e,
        )
        sys.exit(1)

    try:
        verify_s3_readiness(client, bucket_name)
    except Exception as e:
        logger.exception(
            "Pre-flight check failed: SeaweedFS read/write check failed. Error: %s",
            e,
        )
        sys.exit(1)

    # 3. Verify FMS API connectivity for the active environment.
    active_env = resolve_active_environment()
    try:
        verify_fms_readiness(active_env)
    except Exception as e:
        logger.exception(
            "Pre-flight check failed: FMS %s authentication failed. Error: %s",
            active_env,
            e,
        )
        sys.exit(1)

    logger.info("Landing ingestion pre-flight checks passed successfully.")
