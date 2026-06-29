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

"""Unit and integration tests for the ENTSO-E dynamic ingestion job."""

from __future__ import annotations

import json

from unittest.mock import ANY, MagicMock

import pytest
import yaml

from entsoe_pipeline.io.sync import sync_active_domains


def test_sync_active_domains_success(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Tests the sync loop of active domains, verifying it processes active files.

    Follows 3A - Arrange, Act, Assert.
    """
    # -------------------------------------------------------------------------
    # 1. Arrange
    # -------------------------------------------------------------------------
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

    mock_registry_file = tmp_path / "landing_registry.json"
    if mock_registry_file.exists():
        mock_registry_file.unlink()

    monkeypatch.setattr(
        "entsoe_pipeline.io.sync.get_active_domains_config",
        lambda: mock_domains_config,
    )
    monkeypatch.setattr(
        "entsoe_pipeline.io.sync.get_landing_bucket_schema",
        lambda: ["iop/TP_export/Load/ActualTotalLoad_6.1.A_r3"],
    )
    monkeypatch.setattr(
        "entsoe_pipeline.io.sync.LANDING_REGISTRY_JSON",
        mock_registry_file,
    )

    mock_selected_file = {
        "name": "2026_04_ActualTotalLoad_6.1.A_r3.csv",
        "fileId": "mock-uuid-1234",
        "originalSize": 1024,
        "lastUpdatedTimestamp": "2026-04-15T12:00:00Z",
        "remote_folder": "ActualTotalLoad_6.1.A_r3",
    }

    mock_csv_content = b"header1;header2\nvalue1;value2"

    mock_download_file = MagicMock(return_value=mock_csv_content)
    mock_upload_s3 = MagicMock()
    mock_s3_client = MagicMock()

    mock_s3_client.head_object.side_effect = Exception("Not Found")

    monkeypatch.setattr(
        "entsoe_pipeline.io.sync.select_files_to_sync",
        lambda *_a, **_kw: [mock_selected_file],
    )
    monkeypatch.setattr(
        "entsoe_pipeline.io.sync.download_fms_file",
        mock_download_file,
    )
    monkeypatch.setattr(
        "entsoe_pipeline.io.sync.upload_file_to_s3",
        mock_upload_s3,
    )
    monkeypatch.setattr(
        "entsoe_pipeline.io.sync.get_s3_client",
        lambda: mock_s3_client,
    )
    monkeypatch.setattr(
        "entsoe_pipeline.io.sync.get_fms_client",
        lambda *_a, **_kw: MagicMock(),
    )
    monkeypatch.setattr(
        "shutil.disk_usage",
        lambda *_a: (10**12, 10**10, 10**11),
    )

    # -------------------------------------------------------------------------
    # 2. Act
    # -------------------------------------------------------------------------
    metrics = sync_active_domains("IOP", run_id="test-run-id-999")

    # -------------------------------------------------------------------------
    # 3. Assert
    # -------------------------------------------------------------------------
    assert metrics["downloaded"] == 1
    assert metrics["processed"] == 1
    assert metrics["skipped"] == 0
    assert metrics["errors"] == 0

    mock_download_file.assert_called_once_with(
        client=ANY,
        top_level_folder="TP_export",
        folder_path="ActualTotalLoad_6.1.A_r3",
        filename="2026_04_ActualTotalLoad_6.1.A_r3.csv",
    )

    mock_upload_s3.assert_called_once()
    _called_args, called_kwargs = mock_upload_s3.call_args
    expected_s3_key = (
        "iop/TP_export/Load/ActualTotalLoad_6.1.A_r3/"
        "2026_04_ActualTotalLoad_6.1.A_r3.csv"
    )
    assert called_kwargs["s3_key"] == expected_s3_key

    assert mock_registry_file.exists()
    with mock_registry_file.open("r", encoding="utf-8") as f:
        registry = json.load(f)
    data_keys = {k for k in registry if not k.startswith("_")}
    assert len(data_keys) == 1
    assert expected_s3_key in data_keys

    file_meta = registry[expected_s3_key]
    assert file_meta["file_name"] == "2026_04_ActualTotalLoad_6.1.A_r3.csv"
    assert file_meta["file_id"] == "mock-uuid-1234"
    assert file_meta["file_size_bytes"] == 1024
    assert file_meta["last_updated_timestamp"] == "2026-04-15T12:00:00Z"
    assert "xxhash" in file_meta
    assert "downloaded_at" in file_meta
    assert file_meta["run_id"] == "test-run-id-999"
