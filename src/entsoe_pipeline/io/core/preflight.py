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

"""Preflight checks and workspace initialization before data synchronization."""

from __future__ import annotations

import logging
import sys

from botocore.exceptions import ClientError

from entsoe_pipeline import get_config
from entsoe_pipeline.lakehouse.core.s3_tree_builder import (
    ensure_bucket_exists,
    get_s3_client,
)
from entsoe_pipeline.lakehouse.generate_tree_for_my_entsoe_domains import (
    generate_tree_for_my_entsoe_domains,
)

logger = logging.getLogger("entsoe_pipeline.io.core.preflight")


def run_ingestion_preflight() -> None:
    """Orchestrates preflight readiness checks before sync takeoff.

    Sets up the active S3 directory tree hierarchies for domains configured
    in the environment, and verifies read/write/delete operations on the
    underlying landing storage bucket. Halts pipeline execution if
    any check fails.

    Raises:
        SystemExit: If the target landing bucket is not accessible or if
            read/write/delete operations on SeaweedFS fail.
    """
    logger.info("Initializing active S3 folder structures...")
    generate_tree_for_my_entsoe_domains()

    logger.info("Running pre-flight readiness checks...")

    config = get_config()
    bucket_name = config.buckets.s3_landing_bucket
    client = get_s3_client()
    test_key = "system_health_checks/seaweedfs_readiness.txt"
    test_data = b"ready"

    # 1. Verify that the target S3 landing bucket exists and is accessible.
    try:
        ensure_bucket_exists(client, bucket_name)
    except ClientError as e:
        logger.exception(
            "Pre-flight check failed: Landing bucket is not accessible. Error: %s",
            e,
        )
        sys.exit(1)

    # 2. Perform write, read, and delete sanity checks on the S3 landing bucket.
    try:
        # Write temporary check file.
        client.put_object(Bucket=bucket_name, Key=test_key, Body=test_data)
        # Read temporary check file back.
        response = client.get_object(Bucket=bucket_name, Key=test_key)
        retrieved_data = response["Body"].read()
        # Delete temporary check file.
        client.delete_object(Bucket=bucket_name, Key=test_key)

        if retrieved_data != test_data:
            raise ValueError("Retrieved data mismatch")

    except (ClientError, ValueError) as e:
        logger.exception(
            "Pre-flight check failed: SeaweedFS read/write check failed. Error: %s",
            e,
        )
        sys.exit(1)

    logger.info("Pre-flight checks passed successfully.")
