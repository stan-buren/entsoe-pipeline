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

"""Unit tests for landing-stage preflight checks orchestrator."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from botocore.exceptions import ClientError

from entsoe_pipeline import get_config
from entsoe_pipeline.preflight.landing import (
    run_ingest_landing_preflight,
    run_prepare_landing_preflight,
)


@patch("entsoe_pipeline.preflight.landing.verify_db_readiness")
@patch("entsoe_pipeline.preflight.landing.verify_fms_readiness")
def test_run_prepare_landing_preflight_success(
    mock_verify_fms: MagicMock,
    mock_verify_db: MagicMock,
) -> None:
    """Verify metadata preparation preflight check success."""
    run_prepare_landing_preflight()
    assert mock_verify_fms.call_count == 2
    mock_verify_fms.assert_any_call("IOP")
    mock_verify_fms.assert_any_call("PROD")
    mock_verify_db.assert_called_once()


@patch("entsoe_pipeline.preflight.landing.verify_db_readiness")
@patch("entsoe_pipeline.preflight.landing.verify_fms_readiness")
def test_run_prepare_landing_preflight_failure(
    mock_verify_fms: MagicMock,
    mock_verify_db: MagicMock,
) -> None:
    """Verify metadata preparation preflight check failure halts process."""
    mock_verify_fms.side_effect = RuntimeError("Mock FMS error")
    with pytest.raises(SystemExit) as exc_info:
        run_prepare_landing_preflight()
    assert exc_info.value.code == 1


@patch("entsoe_pipeline.preflight.landing.verify_db_readiness")
@patch("entsoe_pipeline.preflight.landing.generate_tree_for_my_entsoe_domains")
@patch("entsoe_pipeline.preflight.landing.get_s3_client")
@patch("entsoe_pipeline.preflight.landing.verify_s3_readiness")
@patch("entsoe_pipeline.preflight.landing.resolve_active_environment")
@patch("entsoe_pipeline.preflight.landing.verify_fms_readiness")
def test_run_ingest_landing_preflight_success(
    mock_fms_ready: MagicMock,
    mock_resolve_env: MagicMock,
    mock_s3_ready: MagicMock,
    mock_get_s3: MagicMock,
    mock_gen_tree: MagicMock,
    mock_verify_db: MagicMock,
) -> None:
    """Verify successful landing ingestion preflight check pipeline."""
    # Arrange
    mock_resolve_env.return_value = "IOP"
    mock_client = MagicMock()
    mock_get_s3.return_value = mock_client

    # Act
    run_ingest_landing_preflight()

    # Assert
    mock_gen_tree.assert_called_once()
    bucket_name = get_config().buckets.s3_landing_bucket
    mock_client.head_bucket.assert_any_call(Bucket=bucket_name)
    mock_s3_ready.assert_called_once_with(mock_client, bucket_name)
    mock_fms_ready.assert_called_once_with("IOP")
    mock_verify_db.assert_called_once()


@patch("entsoe_pipeline.preflight.landing.verify_db_readiness")
@patch("entsoe_pipeline.preflight.landing.generate_tree_for_my_entsoe_domains")
@patch("entsoe_pipeline.preflight.landing.get_s3_client")
@patch("entsoe_pipeline.preflight.landing.verify_s3_readiness")
@patch("entsoe_pipeline.preflight.landing.resolve_active_environment")
@patch("entsoe_pipeline.preflight.landing.verify_fms_readiness")
def test_run_ingest_landing_preflight_s3_failure(
    mock_fms_ready: MagicMock,
    mock_resolve_env: MagicMock,
    mock_s3_ready: MagicMock,
    mock_get_s3: MagicMock,
    mock_gen_tree: MagicMock,
    mock_verify_db: MagicMock,
) -> None:
    """Verify landing ingestion preflight halts execution on S3 access failure."""
    # Arrange
    mock_client = MagicMock()
    mock_get_s3.return_value = mock_client
    mock_client.head_bucket.side_effect = ClientError(
        {"Error": {"Code": "NoSuchBucket", "Message": "Bucket does not exist"}},
        "HeadBucket",
    )

    # Act & Assert
    with pytest.raises(SystemExit) as exc_info:
        run_ingest_landing_preflight()
    assert exc_info.value.code == 1
