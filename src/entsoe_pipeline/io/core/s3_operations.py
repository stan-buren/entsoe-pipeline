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

"""Low-level S3 storage gateway operations."""

from __future__ import annotations

import logging

from pathlib import Path

from botocore.exceptions import ClientError

logger = logging.getLogger("entsoe_pipeline.io.core.s3_operations")


def upload_local_file_to_s3(
    local_path: Path,
    s3_key: str,
    bucket_name: str,
    s3_client,
) -> None:
    """Uploads a local file to the specified S3 bucket.

    Args:
        local_path: Path to the local file.
        s3_key: The target S3 object key.
        bucket_name: The destination S3 bucket name.
        s3_client: The boto3 S3 client instance.

    Raises:
        EntsoeConnectionError: If the upload operation fails.
    """
    logger.info("Uploading %s to s3://%s/%s", local_path, bucket_name, s3_key)
    try:
        s3_client.upload_file(Filename=str(local_path), Bucket=bucket_name, Key=s3_key)
        logger.info("Successfully uploaded %s to S3.", s3_key)
    except Exception as e:
        logger.exception("S3 upload failed for key: %s", s3_key)
        from entsoe_pipeline.logger.exceptions import EntsoeConnectionError

        raise EntsoeConnectionError(f"S3 upload failed for key {s3_key}: {e}") from e


def s3_object_exists(
    s3_key: str,
    bucket_name: str,
    s3_client,
) -> bool:
    """Checks if an object exists in the S3 bucket using a fast head request.

    Args:
        s3_key: The S3 object key.
        bucket_name: The S3 bucket name.
        s3_client: The boto3 S3 client instance.

    Returns:
        bool: True if the object exists, False otherwise.
    """
    try:
        s3_client.head_object(Bucket=bucket_name, Key=s3_key)
        return True
    except ClientError as e:
        # 404 indicates the object does not exist. Any other error is logged.
        if e.response.get("Error", {}).get("Code") != "404":
            logger.warning("Error performing head_object on S3 key '%s': %s", s3_key, e)
        return False
    except Exception as e:
        logger.warning("Unexpected error checking S3 key '%s': %s", s3_key, e)
        return False
