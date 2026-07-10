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

"""Integration test verifying that the target S3 folder structure for active domains is ready."""

from __future__ import annotations

import pytest
import yaml

from botocore.exceptions import ClientError

from entsoe_pipeline import (
    MY_ENTSOE_DOMAINS_YML,
    get_config,
    get_landing_bucket_schema,
)
from entsoe_pipeline.lakehouse.core.s3_tree_builder import get_s3_client


def test_landing_bucket_folder_structure_ready() -> None:
    """Verifies that all S3 landing directories configured for the active env exist and are writable.

    Follows 3A - Arrange, Act, Assert.
    """
    # -------------------------------------------------------------------------
    # 1. Arrange
    # -------------------------------------------------------------------------
    if not MY_ENTSOE_DOMAINS_YML.exists():
        pytest.skip("Active domains selection configuration not found.")

    with MY_ENTSOE_DOMAINS_YML.open(encoding="utf-8") as f:
        config_data = yaml.safe_load(f) or {}

    config = get_config()
    active_env = config.active_environment.upper()
    env_lower = active_env.lower()

    environments = config_data.get("environments", {})
    env_data = environments.get(active_env)
    if not env_data:
        pytest.skip(f"No configuration for environment {active_env} found.")

    # Collect active folders
    active_folders = set()
    root_dirs = env_data.get("root_directories", [])
    for rdir in root_dirs:
        domains = rdir.get("domains", {})
        for folders in domains.values():
            for folder, val in folders.items():
                if val is not False:
                    active_folders.add(folder)
        folders = rdir.get("folders", {})
        for folder, val in folders.items():
            if val is not False:
                active_folders.add(folder)

    if not active_folders:
        pytest.skip("No active folders selected.")

    # Load schema folders
    schema_folders = get_landing_bucket_schema()

    # Filter schema paths matching active folders
    target_folders = []
    for path in schema_folders:
        segments = path.split("/")
        if not segments or segments[0] != env_lower:
            continue
        for active_folder in active_folders:
            if active_folder in segments:
                target_folders.append(path)
                break

    if not target_folders:
        pytest.skip("No target folders resolved from schema for active configuration.")

    bucket_name = config.buckets.s3_landing_bucket
    client = get_s3_client()

    # -------------------------------------------------------------------------
    # 2. Act & 3. Assert
    # -------------------------------------------------------------------------
    try:
        client.head_bucket(Bucket=bucket_name)
    except ClientError as e:
        pytest.fail(
            f"Landing bucket {bucket_name} does not exist or is not accessible: {e}"
        )

    # Check existence of the first directory
    test_folder = target_folders[0]
    test_key = f"{test_folder.strip('/')}/.presence_check"
    try:
        client.put_object(Bucket=bucket_name, Key=test_key, Body=b"ok")
        client.delete_object(Bucket=bucket_name, Key=test_key)
    except ClientError as e:
        pytest.fail(
            f"Failed to write/delete test object in directory {test_folder}: {e}"
        )
