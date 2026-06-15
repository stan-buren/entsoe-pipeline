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

"""Orchestrates generation of active domain directory trees in S3 landing bucket."""

from __future__ import annotations

import logging

from typing import Any

import yaml

from entsoe_pipeline import (
    LANDING_BUCKET_SCHEMA_YML,
    MY_ENTSOE_DOMAINS_YML,
    get_config,
    setup_logging,
)
from entsoe_pipeline.lakehouse.core.s3_tree_builder import (
    ensure_bucket_exists,
    get_s3_client,
)

logger = logging.getLogger("entsoe_pipeline.lakehouse")


def get_active_folders(config_data: dict[str, Any]) -> set[tuple[str, str]]:
    """Extracts a set of (env_lowercase, folder_name) that are active.

    Active folders are those set to True or containing a list of files.
    """
    active = set()
    environments = config_data.get("environments", {})
    for env_name, env_data in environments.items():
        env_lowercase = env_name.lower()
        root_dirs = env_data.get("root_directories", [])
        for rdir in root_dirs:
            domains = rdir.get("domains", {})
            for folders in domains.values():
                for folder, val in folders.items():
                    if val is not False:
                        active.add((env_lowercase, folder))
            folders = rdir.get("folders", {})
            for folder, val in folders.items():
                if val is not False:
                    active.add((env_lowercase, folder))
    return active


def generate_tree_for_my_entsoe_domains() -> None:
    """Loads active domains config and generates matching virtual S3 directories."""
    logger.info("=== STARTING ON-DEMAND S3 TREE GENERATION ===")

    if not MY_ENTSOE_DOMAINS_YML.exists():
        raise FileNotFoundError(
            f"Active domains selection configuration not found at: {MY_ENTSOE_DOMAINS_YML}. "
            "Please run my_entsoe_domains ingestion first."
        )

    with MY_ENTSOE_DOMAINS_YML.open(encoding="utf-8") as f:
        config_data = yaml.safe_load(f) or {}

    active_folders = get_active_folders(config_data)
    logger.info("Detected %d active folders across environments.", len(active_folders))

    if not LANDING_BUCKET_SCHEMA_YML.exists():
        raise FileNotFoundError(
            f"Landing bucket schema contract not found at: {LANDING_BUCKET_SCHEMA_YML}"
        )

    with LANDING_BUCKET_SCHEMA_YML.open(encoding="utf-8") as f:
        schema_data = yaml.safe_load(f) or {}
    schema_folders = schema_data.get("folders", [])

    # Filter schema paths matching active folders for each environment
    target_folders = []
    for path in schema_folders:
        segments = path.split("/")
        if not segments:
            continue
        env_lowercase = segments[0]
        for active_env, active_folder in active_folders:
            if env_lowercase == active_env and active_folder in segments:
                target_folders.append(path)
                break

    # Establish S3 client and ensure bucket exists
    config = get_config()
    bucket_name = config.buckets.s3_landing_bucket
    client = get_s3_client()
    ensure_bucket_exists(client, bucket_name)

    logger.info(
        "Initializing S3 folders. Total matched directories to create: %d",
        len(target_folders),
    )

    for folder in target_folders:
        key = f"{folder.strip('/')}/"
        try:
            client.put_object(Bucket=bucket_name, Key=key)
            logger.debug("Created directory path in S3: %s", key)
        except Exception as e:
            logger.exception("Failed to create directory path %s in S3", key)
            from entsoe_pipeline.logger.exceptions import EntsoeConnectionError

            raise EntsoeConnectionError(
                f"Failed to create directory path {key} in S3: {e}"
            ) from e

    logger.info("=== ON-DEMAND S3 TREE GENERATION COMPLETED ===")


if __name__ == "__main__":
    setup_logging()
    generate_tree_for_my_entsoe_domains()
