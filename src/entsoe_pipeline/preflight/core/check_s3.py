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

"""S3 storage connectivity and permission health checks."""

from __future__ import annotations

import logging

from typing import Any

logger = logging.getLogger("entsoe_pipeline.preflight.core.check_s3")


def verify_s3_readiness(client: Any, bucket_name: str) -> None:
    """Verifies that the target S3 bucket is accessible and supports read/write.

    Args:
        client: The initialized boto3 S3 client.
        bucket_name: Name of the landing zone bucket to verify.

    Raises:
        ClientError: If connection to S3 fails.
        ValueError: If written check data does not match the retrieved data.
    """
    test_key = "system_health_checks/seaweedfs_readiness.txt"
    test_data = b"ready"

    # Write temporary check file.
    client.put_object(Bucket=bucket_name, Key=test_key, Body=test_data)

    # Read temporary check file back.
    response = client.get_object(Bucket=bucket_name, Key=test_key)
    retrieved_data = response["Body"].read()

    # Clean up and delete temporary check file.
    client.delete_object(Bucket=bucket_name, Key=test_key)

    if retrieved_data != test_data:
        raise ValueError("Retrieved health check data does not match written data.")
