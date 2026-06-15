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

"""Integration test verifying that the SeaweedFS S3-compatible storage is ready."""

from __future__ import annotations

import pytest

from botocore.exceptions import ClientError

from entsoe_pipeline.config.config_loader import get_config
from entsoe_pipeline.lakehouse.core.s3_tree_builder import (
    ensure_bucket_exists,
    get_s3_client,
)


def test_seaweedfs_readiness() -> None:
    """Verifies that SeaweedFS S3-compatible API is responsive and writable.

    This test follows the Arrange-Act-Assert (3A) pattern:
    - Arrange: Instantiate S3 client, define test bucket and key,
      and ensure the bucket exists.
    - Act: Put a temporary test object, retrieve it, and then delete it.
    - Assert: Check that retrieval content is correct and deletion
      completes without error.
    """
    # Arrange
    config = get_config()
    bucket_name = config.buckets.s3_landing_bucket
    client = get_s3_client()
    test_key = "system_health_checks/seaweedfs_readiness.txt"
    test_data = b"ready"

    # Ensure the landing bucket is created
    ensure_bucket_exists(client, bucket_name)

    try:
        # Act
        # 1. Put the temporary object
        client.put_object(Bucket=bucket_name, Key=test_key, Body=test_data)

        # 2. Retrieve the object
        response = client.get_object(Bucket=bucket_name, Key=test_key)
        retrieved_data = response["Body"].read()

        # 3. Clean up (delete) the object
        client.delete_object(Bucket=bucket_name, Key=test_key)
    except ClientError as e:
        pytest.fail(f"SeaweedFS connection or operation failed: {e}")

    # Assert
    assert retrieved_data == test_data, "Retrieved data does not match written data"
