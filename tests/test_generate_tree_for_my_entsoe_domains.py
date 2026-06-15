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

from entsoe_pipeline import (
    LANDING_BUCKET_SCHEMA_YML,
    get_config,
)
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

    # Load active paths from landing schema to verify matches
    with LANDING_BUCKET_SCHEMA_YML.open(encoding="utf-8") as f:
        schema_data = yaml.safe_load(f) or {}
    schema_folders = schema_data.get("folders", [])

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
