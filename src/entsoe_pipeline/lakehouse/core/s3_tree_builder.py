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

"""Core S3 directory tree builder for the ENTSO-E lakehouse.

This module provides functions to establish S3 connections to the local
SeaweedFS or cloud gateway, ensure that standard landing buckets exist,
and pre-create virtual directory hierarchies parsed from bucket schemas.
"""

from __future__ import annotations

import logging
import os

from typing import Any

import boto3

from botocore.exceptions import ClientError

from entsoe_pipeline.config.config_loader import (
    get_config,
    get_landing_bucket_schema,
)
from entsoe_pipeline.logger.exceptions import EntsoeConnectionError


def get_s3_client() -> Any:
    """Initializes and returns a boto3 S3 client using the active configuration.

    Returns:
        Any: The configured S3 client.
    """
    config = get_config()
    endpoint_url = f"http://{config.hosts.seaweedfs}:{config.ports.s3_compatible}"
    aws_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID", "test")
    aws_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "test")

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=config.region.aws_region or "us-east-1",
    )


def ensure_bucket_exists(client: Any, bucket_name: str) -> None:
    """Checks if a bucket exists in S3; if not, creates it.

    This function is idempotent and safe. It will not modify or overwrite
    an existing bucket if it already exists.

    Args:
        client: The boto3 S3 client.
        bucket_name: The name of the bucket to verify/create.

    Raises:
        EntsoeConnectionError: If connection to S3 storage fails.
    """
    logger = logging.getLogger("entsoe_pipeline")
    try:
        client.head_bucket(Bucket=bucket_name)
        logger.debug("S3 bucket %s already exists.", bucket_name)
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code in ("404", "NoSuchBucket"):
            try:
                client.create_bucket(Bucket=bucket_name)
                logger.info("S3 bucket %s successfully created.", bucket_name)
            except Exception as create_err:
                logger.exception("Failed to create S3 bucket %s", bucket_name)
                raise EntsoeConnectionError(
                    f"Failed to create S3 bucket {bucket_name}: {create_err}"
                ) from create_err
        else:
            logger.exception("Failed to check S3 bucket %s presence", bucket_name)
            raise EntsoeConnectionError(
                f"Failed to check S3 bucket {bucket_name} presence: {e}"
            ) from e
    except Exception as e:
        logger.exception("Connection to S3 compatible storage failed")
        raise EntsoeConnectionError(
            f"Connection to S3 compatible storage failed: {e}"
        ) from e


def create_directories_with_prefix(prefix: str) -> None:
    """Reads entsoe_fms_folder_schema.yml and creates folders under the specified prefix.

    Args:
        prefix (str): Prefix path (e.g., 'iop/TP_export/').

    Raises:
        FileNotFoundError: If the landing bucket schema file is missing.
        EntsoeConnectionError: If folder creation fails due to network/storage issues.
    """
    logger = logging.getLogger("entsoe_pipeline")

    folders = get_landing_bucket_schema()
    filtered_folders = [f for f in folders if f.startswith(prefix)]

    if not filtered_folders:
        logger.warning("No folders found matching prefix: %s", prefix)
        return

    config = get_config()
    bucket_name = config.buckets.s3_landing_bucket
    client = get_s3_client()

    ensure_bucket_exists(client, bucket_name)

    logger.info(
        "Starting generation of directory structure for prefix: %s. Total folders: %d",
        prefix,
        len(filtered_folders),
    )

    for folder in filtered_folders:
        key = f"{folder.strip('/')}/"
        try:
            client.put_object(Bucket=bucket_name, Key=key)
            logger.debug("Created directory path in S3: %s", key)
        except Exception as e:
            logger.exception("Failed to create directory path %s in S3", key)
            raise EntsoeConnectionError(
                f"Failed to create directory path {key} in S3: {e}"
            ) from e

    logger.info("Successfully generated S3 directory tree for prefix: %s", prefix)
