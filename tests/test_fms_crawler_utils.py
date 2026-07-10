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

"""Unit tests for FMS crawler utilities."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from entsoe_pipeline.fms_metadata.utils.crawler import crawl_metadata_folder


@pytest.mark.unit
def test_crawl_metadata_folder_root_file_exists() -> None:
    """Verify root file metadata is resolved from pre-fetched dict."""
    # Arrange
    client = MagicMock()
    folder = "2026_05_Load.csv"
    root_files_by_name = {
        "2026_05_Load.csv": {
            "name": "2026_05_Load.csv",
            "fileId": "uuid-1",
            "originalSize": 200,
            "size": 100,
            "lastUpdatedTimestamp": "2026-05-28T12:00:00Z",
        }
    }
    api_counter = [0]

    # Act
    results = crawl_metadata_folder(
        client=client,
        folder=folder,
        root_files_by_name=root_files_by_name,
        api_counter=api_counter,
        env="iop",
    )

    # Assert
    assert len(results) == 1
    assert results[0]["name"] == "2026_05_Load.csv"
    assert results[0]["sizes"]["original"]["bytes"] == 200


@pytest.mark.unit
def test_crawl_metadata_folder_root_file_missing(caplog) -> None:
    """Verify warning is logged and empty list returned if root file is missing."""
    # Arrange
    client = MagicMock()
    folder = "2026_05_Load.csv"
    root_files_by_name = {}
    api_counter = [0]

    # Act
    results = crawl_metadata_folder(
        client=client,
        folder=folder,
        root_files_by_name=root_files_by_name,
        api_counter=api_counter,
        env="iop",
    )

    # Assert
    assert results == []
    assert "Root file '2026_05_Load.csv' not found in root items" in caplog.text


@pytest.mark.unit
@patch("entsoe_pipeline.fms_metadata.utils.crawler.list_folder_raw_items_recursive")
def test_crawl_metadata_folder_directory(mock_list_recursive: MagicMock) -> None:
    """Verify recursive directory crawling fetches and maps items."""
    # Arrange
    client = MagicMock()
    folder = "ActualTotalLoad_r3"
    root_files_by_name = {}
    api_counter = [0]

    mock_list_recursive.return_value = [
        {
            "name": "nested_file.csv",
            "fileId": "uuid-2",
            "originalSize": 300,
            "size": 150,
            "lastUpdatedTimestamp": "2026-05-28T12:00:00Z",
        }
    ]

    # Act
    results = crawl_metadata_folder(
        client=client,
        folder=folder,
        root_files_by_name=root_files_by_name,
        api_counter=api_counter,
        env="iop",
    )

    # Assert
    mock_list_recursive.assert_called_once_with(
        client=client,
        folder_name=folder,
        api_counter_ref=api_counter,
        root_dir="TP_export",
    )
    assert len(results) == 1
    assert results[0]["name"] == "nested_file.csv"
    assert results[0]["sizes"]["original"]["bytes"] == 300
