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

"""Idempotent initialization script for all required SeaweedFS S3 buckets.

Run this script once before starting any pipeline jobs to ensure
the required bucket infrastructure exists in SeaweedFS:
  - landing-zone: raw CSV files from the FMS API (immutable archive).
  - lakehouse:    Iceberg REST Catalog warehouse for transactional tables.

Usage:
    uv run python src/entsoe_pipeline/lakehouse/сreate_buckets.py
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from entsoe_pipeline.config.config_loader import (
    get_buckets_config,
    get_hosts_config,
    get_ports_config,
)
from entsoe_pipeline.lakehouse.core.s3_tree_builder import get_s3_client

logger = logging.getLogger("entsoe_pipeline.lakehouse.create_buckets")

# Iceberg namespace to initialize inside the lakehouse catalog
_ICEBERG_NAMESPACE = "db"


def ensure_all_buckets_exist() -> None:
    """Creates all required SeaweedFS S3 buckets if they do not already exist.

    Reads bucket names from the centralized YAML configuration (SSOT) and
    calls S3 ``head_bucket`` to check existence. Safe to re-run at any time:
    existing buckets are left untouched.

    Buckets initialized:
        - ``s3_landing_bucket`` – Landing zone for raw CSV files.
        - ``s3_lakehouse_bucket`` – Iceberg REST Catalog warehouse.
    """
    buckets = get_buckets_config()
    client = get_s3_client()

    buckets_to_init = [
        buckets.s3_landing_bucket,
        buckets.s3_lakehouse_bucket,
    ]

    for bucket_name in buckets_to_init:
        try:
            client.head_bucket(Bucket=bucket_name)
            logger.info("S3 bucket '%s' already exists. Skipping.", bucket_name)
        except client.exceptions.ClientError:
            logger.info("S3 bucket '%s' not found. Creating...", bucket_name)
            client.create_bucket(Bucket=bucket_name)
            logger.info("S3 bucket '%s' successfully created.", bucket_name)

    logger.info(
        "Bucket initialization complete. Buckets: %s",
        ", ".join(buckets_to_init),
    )


def ensure_iceberg_namespace_exists() -> None:
    """Creates the Iceberg REST Catalog namespace via HTTP if it does not exist.

    Calls SeaweedFS built-in Iceberg REST Catalog directly (without Spark) to
    initialize the ``db`` namespace. Uses only Python stdlib (``urllib``) so no
    Spark session is required at infra-init time.

    The namespace maps to the Spark-level database ``lakehouse.db`` used by all
    Iceberg tables in the lakehouse layer.
    """
    hosts = get_hosts_config()
    ports = get_ports_config()
    catalog_url = f"http://{hosts.iceberg_catalog}:{ports.iceberg_catalog}"
    endpoint = f"{catalog_url}/v1/namespaces"

    payload = json.dumps({"namespace": [_ICEBERG_NAMESPACE], "properties": {}}).encode()
    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as response:
            logger.info(
                "Iceberg namespace '%s' created successfully (HTTP %s).",
                _ICEBERG_NAMESPACE,
                response.status,
            )
    except urllib.error.HTTPError as e:
        if e.code == 409:
            logger.info(
                "Iceberg namespace '%s' already exists. Skipping.",
                _ICEBERG_NAMESPACE,
            )
        else:
            logger.exception(
                "Failed to create Iceberg namespace '%s'. HTTP %s: %s",
                _ICEBERG_NAMESPACE,
                e.code,
                e.reason,
            )
            raise


if __name__ == "__main__":
    from entsoe_pipeline.logger import setup_logging

    setup_logging()
    ensure_all_buckets_exist()
    ensure_iceberg_namespace_exists()
