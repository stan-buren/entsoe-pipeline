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

"""Orchestrator to execute preflight checks for the staging (lakehouse) stage."""

from __future__ import annotations

import logging
import sys

from botocore.exceptions import ClientError

from entsoe_pipeline import get_config, resolve_active_environment
from entsoe_pipeline.lakehouse.core.s3_tree_builder import get_s3_client
from entsoe_pipeline.lakehouse.create_buckets import (
    ensure_iceberg_namespace_exists,
    ensure_s3_table_bucket_exists,
)
from entsoe_pipeline.preflight.core.check_db import verify_db_readiness
from entsoe_pipeline.preflight.core.check_fms import verify_fms_readiness
from entsoe_pipeline.preflight.core.check_s3 import verify_s3_readiness

logger = logging.getLogger("entsoe_pipeline.preflight.staging")


def run_staging_preflight() -> None:
    """Orchestrates preflight checks and lazy-init for the staging ingestion stage.

    Initializes S3 Table Bucket and Iceberg namespace (idempotent), validates
    S3 read/write permissions, database schema contract, and FMS API
    connectivity before staging ingestion takeoff.

    All initialization is idempotent — safe to call before every ingestion run.
    """
    logger.info("Running pre-flight checks for staging ingestion stage...")

    # 1. Ensure lakehouse infrastructure exists (idempotent).
    ensure_s3_table_bucket_exists()
    ensure_iceberg_namespace_exists()

    # 2. Verify S3 storage connectivity and permissions.
    config = get_config()
    lakehouse_bucket = config.buckets.s3_lakehouse_bucket
    landing_bucket = config.buckets.s3_landing_bucket
    client = get_s3_client()

    try:
        client.head_bucket(Bucket=lakehouse_bucket)
    except ClientError as e:
        logger.exception(
            "Pre-flight check failed: Lakehouse bucket '%s' does not exist. "
            "Run 'just lakehouse-init-buckets' to create all required buckets. "
            "Error: %s",
            lakehouse_bucket,
            e,
        )
        sys.exit(1)

    try:
        client.head_bucket(Bucket=landing_bucket)
    except ClientError as e:
        logger.exception(
            "Pre-flight check failed: Landing bucket '%s' does not exist. "
            "Run 'just lakehouse-init-buckets' to create all required buckets. "
            "Error: %s",
            landing_bucket,
            e,
        )
        sys.exit(1)

    try:
        verify_s3_readiness(client, landing_bucket)
    except Exception as e:
        logger.exception(
            "Pre-flight check failed: S3 read/write check failed. Error: %s",
            e,
        )
        sys.exit(1)

    # 3. Verify Database readiness and DDL contract match.
    try:
        verify_db_readiness()
    except Exception as e:
        logger.exception(
            "Pre-flight check failed: Database schema validation failed. Error: %s",
            e,
        )
        sys.exit(1)

    # 4. Verify FMS API connectivity for the active environment.
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

    logger.info("Staging ingestion pre-flight checks passed successfully.")
