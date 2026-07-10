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

"""Unit tests for preflight core connectivity checks (FMS and S3)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from botocore.exceptions import ClientError

from entsoe_pipeline import get_config
from entsoe_pipeline.io.core.preflight import run_ingestion_preflight
from entsoe_pipeline.preflight.core.check_fms import verify_fms_readiness
from entsoe_pipeline.preflight.core.check_s3 import verify_s3_readiness


@patch("entsoe_pipeline.preflight.core.check_fms.create_fms_client")
def test_verify_fms_readiness(mock_create: MagicMock) -> None:
    """Verify that verify_fms_readiness instantiates the client correctly.

    Args:
        mock_create: Mock client creator.
    """
    verify_fms_readiness("IOP")
    mock_create.assert_called_once_with("IOP")


def test_verify_s3_readiness_success() -> None:
    """Verify verify_s3_readiness with successful read/write/delete ops."""
    # Arrange
    mock_client = MagicMock()
    mock_response = {"Body": MagicMock()}
    mock_response["Body"].read.return_value = b"ready"
    mock_client.get_object.return_value = mock_response

    # Act
    verify_s3_readiness(mock_client, "test-bucket")

    # Assert
    mock_client.put_object.assert_called_once_with(
        Bucket="test-bucket",
        Key="system_health_checks/seaweedfs_readiness.txt",
        Body=b"ready",
    )
    mock_client.get_object.assert_called_once_with(
        Bucket="test-bucket",
        Key="system_health_checks/seaweedfs_readiness.txt",
    )
    mock_client.delete_object.assert_called_once_with(
        Bucket="test-bucket",
        Key="system_health_checks/seaweedfs_readiness.txt",
    )


def test_verify_s3_readiness_data_mismatch() -> None:
    """Verify verify_s3_readiness raises ValueError when read data mismatches."""
    # Arrange
    mock_client = MagicMock()
    mock_response = {"Body": MagicMock()}
    mock_response["Body"].read.return_value = b"corrupted"
    mock_client.get_object.return_value = mock_response

    # Act & Assert
    with pytest.raises(ValueError, match="Retrieved health check data does not match"):
        verify_s3_readiness(mock_client, "test-bucket")


@patch("entsoe_pipeline.io.core.preflight.generate_tree_for_my_entsoe_domains")
@patch("entsoe_pipeline.io.core.preflight.get_s3_client")
@patch("entsoe_pipeline.io.core.preflight.ensure_bucket_exists")
def test_run_ingestion_preflight_success(
    mock_ensure_bucket: MagicMock,
    mock_get_client: MagicMock,
    mock_gen_tree: MagicMock,
) -> None:
    """Verify successful ingestion preflight flow.

    Args:
        mock_ensure_bucket: Mock bucket existence check.
        mock_get_client: Mock S3 client fetcher.
        mock_gen_tree: Mock folder structures generator.
    """
    # Arrange
    mock_client = MagicMock()
    mock_response = {"Body": MagicMock()}
    mock_response["Body"].read.return_value = b"ready"
    mock_client.get_object.return_value = mock_response
    mock_get_client.return_value = mock_client

    # Act
    run_ingestion_preflight()

    # Assert
    mock_gen_tree.assert_called_once()
    bucket_name = get_config().buckets.s3_landing_bucket
    mock_ensure_bucket.assert_called_once_with(mock_client, bucket_name)
    mock_client.put_object.assert_called_once()
    mock_client.get_object.assert_called_once()
    mock_client.delete_object.assert_called_once()


@patch("entsoe_pipeline.io.core.preflight.generate_tree_for_my_entsoe_domains")
@patch("entsoe_pipeline.io.core.preflight.get_s3_client")
@patch("entsoe_pipeline.io.core.preflight.ensure_bucket_exists")
def test_run_ingestion_preflight_bucket_error(
    mock_ensure_bucket: MagicMock,
    mock_get_client: MagicMock,
    mock_gen_tree: MagicMock,
) -> None:
    """Verify ingestion preflight halts execution on bucket access failures.

    Args:
        mock_ensure_bucket: Mock bucket existence check.
        mock_get_client: Mock S3 client fetcher.
        mock_gen_tree: Mock folder structures generator.
    """
    # Arrange
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_ensure_bucket.side_effect = ClientError(
        {"Error": {"Code": "NoSuchBucket", "Message": "Bucket does not exist"}},
        "HeadBucket",
    )

    # Act & Assert
    with pytest.raises(SystemExit) as exc_info:
        run_ingestion_preflight()

    assert exc_info.value.code == 1


@patch("entsoe_pipeline.io.core.preflight.generate_tree_for_my_entsoe_domains")
@patch("entsoe_pipeline.io.core.preflight.get_s3_client")
@patch("entsoe_pipeline.io.core.preflight.ensure_bucket_exists")
def test_run_ingestion_preflight_write_error(
    mock_ensure_bucket: MagicMock,
    mock_get_client: MagicMock,
    mock_gen_tree: MagicMock,
) -> None:
    """Verify ingestion preflight halts execution on write permission failures.

    Args:
        mock_ensure_bucket: Mock bucket existence check.
        mock_get_client: Mock S3 client fetcher.
        mock_gen_tree: Mock folder structures generator.
    """
    # Arrange
    mock_client = MagicMock()
    mock_client.put_object.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Write denied"}},
        "PutObject",
    )
    mock_get_client.return_value = mock_client

    # Act & Assert
    with pytest.raises(SystemExit) as exc_info:
        run_ingestion_preflight()

    assert exc_info.value.code == 1
