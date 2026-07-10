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

"""Integration and unit tests for on-demand S3 directory generation."""

from __future__ import annotations

import sys

from dataclasses import replace

import pytest
import yaml

from entsoe_pipeline import get_config
from entsoe_pipeline.lakehouse.core.s3_tree_builder import get_s3_client
from entsoe_pipeline.lakehouse.generate_tree_for_my_entsoe_domains import (
    generate_tree_for_my_entsoe_domains,
)


def test_generate_tree_for_my_entsoe_domains(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """Verifies S3 folders are created on-demand according to active config checklist."""
    # 1. Arrange: Create mock active domains config
    mock_domains_config = {
        "environments": {
            "IOP": {
                "root_directories": [
                    {
                        "name": "TP_export",
                        "domains": {
                            "Load": {
                                "ActualTotalLoad_6.1.A_r3": [
                                    "2026_04_ActualTotalLoad_6.1.A_r3.csv"
                                ],
                                "DayAheadTotalLoadForecast_6.1.B_r3": False,
                            }
                        },
                    }
                ]
            }
        }
    }

    mock_config_file = tmp_path / "mock_my_entsoe_domains.yml"
    with mock_config_file.open("w", encoding="utf-8") as f:
        yaml.dump(mock_domains_config, f)

    gt_module = sys.modules[
        "entsoe_pipeline.lakehouse.generate_tree_for_my_entsoe_domains"
    ]
    monkeypatch.setattr(
        gt_module,
        "MY_ENTSOE_DOMAINS_YML",
        mock_config_file,
    )

    # Mock get_landing_bucket_schema instead of creating files
    schema_folders = [
        "iop/TP_export/Load/ActualTotalLoad_6.1.A_r3",
        "iop/TP_export/Load/DayAheadTotalLoadForecast_6.1.B_r3",
    ]
    monkeypatch.setattr(
        gt_module,
        "get_landing_bucket_schema",
        lambda: schema_folders,
    )

    # Isolate S3 landing bucket per parallel worker to prevent concurrency collisions
    config = get_config()
    worker_id = sys.modules["os"].environ.get("PYTEST_XDIST_TESTRUNNER", "gw0")
    unique_bucket_name = f"test-landing-bucket-{worker_id}"

    new_buckets = replace(config.buckets, s3_landing_bucket=unique_bucket_name)
    new_config = replace(config, buckets=new_buckets)

    monkeypatch.setattr(
        gt_module,
        "get_config",
        lambda: new_config,
    )
    monkeypatch.setattr(
        "entsoe_pipeline.lakehouse.core.s3_tree_builder.get_config",
        lambda: new_config,
    )
    monkeypatch.setattr(
        sys.modules[__name__],
        "get_config",
        lambda: new_config,
    )

    # Clean existing S3 directories in the landing bucket to verify fresh creation
    config = get_config()
    bucket_name = config.buckets.s3_landing_bucket
    client = get_s3_client()

    try:
        client.head_bucket(Bucket=bucket_name)
        objects = client.list_objects_v2(Bucket=bucket_name)
        if "Contents" in objects:
            for obj in objects["Contents"]:
                client.delete_object(Bucket=bucket_name, Key=obj["Key"])
    except Exception:
        # Bucket does not exist or connection failed
        pass

    # 2. Act
    generate_tree_for_my_entsoe_domains()

    # 3. Assert
    objects = client.list_objects_v2(Bucket=bucket_name)
    keys = [obj["Key"] for obj in objects.get("Contents", [])]

    active_paths = [
        f"{p.strip('/')}/"
        for p in schema_folders
        if p.startswith("iop/TP_export/Load/ActualTotalLoad_6.1.A_r3")
    ]
    inactive_paths = [
        f"{p.strip('/')}/"
        for p in schema_folders
        if p.startswith("iop/TP_export/Load/DayAheadTotalLoadForecast_6.1.B_r3")
    ]

    assert len(active_paths) > 0, (
        "No active paths found in schema for test verification"
    )
    for path in active_paths:
        assert path in keys, f"Expected active directory key '{path}' to exist in S3"

    for path in inactive_paths:
        assert path not in keys, (
            f"Expected inactive directory key '{path}' to be absent from S3"
        )


@pytest.mark.unit
def test_generate_tree_for_my_entsoe_domains_s3_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """Verifies that EntsoeConnectionError is raised if S3 creation fails."""
    # 1. Arrange
    mock_domains_config = {
        "environments": {
            "IOP": {
                "root_directories": [
                    {
                        "name": "TP_export",
                        "domains": {
                            "Load": {
                                "ActualTotalLoad_6.1.A_r3": [
                                    "2026_04_ActualTotalLoad_6.1.A_r3.csv"
                                ],
                            }
                        },
                    }
                ]
            }
        }
    }

    mock_config_file = tmp_path / "mock_my_entsoe_domains_err.yml"
    with mock_config_file.open("w", encoding="utf-8") as f:
        yaml.dump(mock_domains_config, f)

    gt_module = sys.modules[
        "entsoe_pipeline.lakehouse.generate_tree_for_my_entsoe_domains"
    ]
    monkeypatch.setattr(gt_module, "MY_ENTSOE_DOMAINS_YML", mock_config_file)
    monkeypatch.setattr(
        gt_module,
        "get_landing_bucket_schema",
        lambda: ["iop/TP_export/Load/ActualTotalLoad_6.1.A_r3"],
    )

    # Mock S3 client to raise an exception on put_object
    from unittest.mock import MagicMock

    mock_client = MagicMock()
    mock_client.put_object.side_effect = Exception("S3 write failure")
    monkeypatch.setattr(gt_module, "get_s3_client", lambda: mock_client)

    # 2. Act & 3. Assert
    from entsoe_pipeline.logger.exceptions import EntsoeConnectionError

    with pytest.raises(EntsoeConnectionError, match="Failed to create directory path"):
        generate_tree_for_my_entsoe_domains()
