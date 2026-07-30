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

"""Idempotent initialization for all SeaweedFS S3 buckets and Iceberg catalog.

Run once after ``lakehouse-up`` to ensure the required infrastructure exists:

  - S3 Table Bucket (Iceberg warehouse, via S3 Tables API on port 8333)
  - Regular S3 buckets (landing-zone, lakehouse, via boto3)
  - Iceberg namespace (REST Catalog on port 8181)

All operations use network APIs exclusively — no ``weed shell`` or
``docker exec``.  The script is safe to re-run at any time.

Usage:
    uv run python src/entsoe_pipeline/lakehouse/create_buckets.py
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from entsoe_pipeline.config.config_loader import (
    get_buckets_config,
    get_hosts_config,
    get_namespaces_config,
    get_ports_config,
)
from entsoe_pipeline.lakehouse.core.s3_tree_builder import get_s3_client

logger = logging.getLogger("entsoe_pipeline.lakehouse.create_buckets")


# ---------------------------------------------------------------------------
# 1. S3 Table Bucket (Iceberg warehouse)
# ---------------------------------------------------------------------------


def ensure_s3_table_bucket_exists() -> None:
    """Creates the S3 Table Bucket via SeaweedFS S3 Tables API.

    Uses the S3-compatible endpoint with the
    ``X-Amz-Target: S3Tables.CreateTableBucket`` header.  The table bucket is
    a specialized bucket type required by the built-in Iceberg REST Catalog —
    distinct from the regular S3 object buckets created by
    ``ensure_all_buckets_exist``.

    The bucket name is read from SSOT (``bucket.yml`` → ``s3_table_bucket``).
    Uses only Python stdlib ``urllib`` — no boto3, no Spark, no ``weed shell``.

    Idempotent: HTTP 409 (Conflict) is treated as success.
    """
    hosts = get_hosts_config()
    ports = get_ports_config()
    bucket = get_buckets_config().s3_table_bucket
    endpoint = f"http://{hosts.seaweedfs}:{ports.s3_compatible}/"
    payload = json.dumps({"name": bucket}).encode()
    req = urllib.request.Request(  # noqa: S310
        endpoint,
        data=payload,
        headers={
            "X-Amz-Target": "S3Tables.CreateTableBucket",
            "Content-Type": "application/x-amz-json-1.1",
        },
        method="POST",
    )

    logger.info("Creating S3 Table Bucket '%s' via S3 Tables API...", bucket)

    try:
        with urllib.request.urlopen(req) as response:  # noqa: S310
            logger.info(
                "S3 Table Bucket '%s' created successfully (HTTP %s).",
                bucket,
                response.status,
            )
    except urllib.error.HTTPError as e:
        if e.code == 409:
            logger.info("S3 Table Bucket '%s' already exists. Skipping.", bucket)
        else:
            logger.exception(
                "Failed to create S3 Table Bucket '%s'. HTTP %s: %s",
                bucket,
                e.code,
                e.reason,
            )
            raise


# ---------------------------------------------------------------------------
# 2. Regular S3 buckets (landing-zone, lakehouse)
# ---------------------------------------------------------------------------


def ensure_all_buckets_exist() -> None:
    """Creates all required SeaweedFS S3 buckets if they do not already exist.

    Reads bucket names from the centralized YAML configuration (SSOT) and
    calls S3 ``head_bucket`` to check existence. Safe to re-run at any time:
    existing buckets are left untouched.

    Buckets initialized:
        - ``s3_landing_bucket`` - Landing zone for raw CSV files.
        - ``s3_lakehouse_bucket`` - Iceberg REST Catalog warehouse.
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


# ---------------------------------------------------------------------------
# 3. Iceberg namespace (REST Catalog)
# ---------------------------------------------------------------------------


def ensure_iceberg_namespace_exists() -> None:
    """Creates the Iceberg REST Catalog namespace via HTTP if it does not exist.

    Calls SeaweedFS built-in Iceberg REST Catalog directly (without Spark) to
    initialize the staging namespace. Uses only Python stdlib (``urllib``) so
    no Spark session is required at infra-init time.

    The namespace maps to the Spark-level database
    ``lakehouse.{namespace}.{table}`` used by all Iceberg tables in the
    lakehouse layer.

    Both the table bucket name and the namespace name are read from SSOT
    (``bucket.yml`` and ``namespaces.yml``).  The table bucket is injected as
    the ``{prefix}`` path segment per the Iceberg REST Catalog OpenAPI spec:
    ``POST /v1/{prefix}/namespaces``.
    """
    hosts = get_hosts_config()
    ports = get_ports_config()
    table_bucket = get_buckets_config().s3_table_bucket
    namespace = get_namespaces_config().staging
    catalog_url = f"http://{hosts.iceberg_catalog}:{ports.iceberg_catalog}"
    endpoint = f"{catalog_url}/v1/{table_bucket}/namespaces"

    payload = json.dumps({"namespace": [namespace], "properties": {}}).encode()
    req = urllib.request.Request(  # noqa: S310
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as response:  # noqa: S310
            logger.info(
                "Iceberg namespace '%s' created successfully (HTTP %s).",
                namespace,
                response.status,
            )
    except urllib.error.HTTPError as e:
        if e.code == 409:
            logger.info(
                "Iceberg namespace '%s' already exists. Skipping.",
                namespace,
            )
        else:
            logger.exception(
                "Failed to create Iceberg namespace '%s'. HTTP %s: %s",
                namespace,
                e.code,
                e.reason,
            )
            raise


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from entsoe_pipeline.logger import setup_logging

    setup_logging()
    ensure_s3_table_bucket_exists()
    ensure_all_buckets_exist()
    ensure_iceberg_namespace_exists()
