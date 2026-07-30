#!/usr/bin/env python3

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

"""Bridge: exports pipeline config from Python SSOT as JSON for Ansible.

Used by the Ansible playbook at runtime — avoids duplicating config values
that already live in config_env/*.yml and .env (loaded via PipelineConfig).

Usage:
    uv run python infra/ansible/scripts/export_config.py

Output: JSON on stdout, consumed by ansible.builtin.command + set_fact.
"""

from __future__ import annotations

import json
import os
import sys

from pathlib import Path

# Add project root to path so we can import entsoe_pipeline
_project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_project_root))

from entsoe_pipeline import (  # noqa: E402 — import after path injection
    get_buckets_config,
    get_hosts_config,
    get_ports_config,
    get_region_config,
    get_spark_config,
)


def main() -> None:
    """Export pipeline configuration from Python SSOT as JSON for Ansible."""
    hosts = get_hosts_config()
    ports = get_ports_config()
    buckets = get_buckets_config()
    region = get_region_config()
    spark_cfg = get_spark_config()

    # Secrets from .env (loaded by PipelineConfig._from_yaml via load_dotenv)
    s3_access_key = os.environ.get("AWS_ACCESS_KEY_ID", "")
    s3_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "")

    # Spark Master host — derived from connect_server in spark.yml
    # Format: sc://host:port
    spark_master_host = spark_cfg.connect_server.split("://")[1].split(":")[0]

    config = {
        # SeaweedFS S3
        "seaweedfs_host": hosts.seaweedfs,
        "s3_port": ports.s3_compatible,
        "iceberg_catalog_port": ports.iceberg_catalog,
        "s3_access_key": s3_access_key,
        "s3_secret_key": s3_secret_key,
        # Spark
        "spark_master_host": spark_master_host,
        "spark_master_port": 7077,
        "spark_connect_port": 15002,
        "spark_connect_server": spark_cfg.connect_server,
        # Buckets
        "s3_landing_bucket": buckets.s3_landing_bucket,
        "s3_lakehouse_bucket": buckets.s3_lakehouse_bucket,
        "s3_table_bucket": buckets.s3_table_bucket,
        # Region
        "aws_region": region.aws_region,
    }

    json.dump(config, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
