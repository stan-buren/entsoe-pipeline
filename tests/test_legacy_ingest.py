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

"""Unit Tests for FMS Legacy Publications Ingestion Engine.

Verifies the global legacy ingestion flow and core historical directory crawling
delegation using the 3A pattern.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from entsoe_pipeline.api.ls_fms import list_folder_raw_items_recursive
from entsoe_pipeline.fms_metadata.core.legacy import ingest_legacy_metadata
from entsoe_pipeline.fms_metadata.ingestion.legacy_ingest import (
    ingest_all_legacy_metadata,
)


@patch("entsoe_pipeline.fms_metadata.ingestion.legacy_ingest.ingest_legacy_metadata")
def test_ingest_all_legacy_metadata_delegates_to_core(
    mock_ingest_core: MagicMock,
) -> None:
    """Verifies that legacy ingestion crawls all three archives."""
    # -------------------------------------------------------------------------
    # ACT: Trigger the global legacy metadata crawling process
    # -------------------------------------------------------------------------
    ingest_all_legacy_metadata()

    # -------------------------------------------------------------------------
    # ASSERT: Verify it delegates cleanly for R1, R2, and R3 archives
    # -------------------------------------------------------------------------
    assert mock_ingest_core.call_count == 3
    mock_ingest_core.assert_any_call("R3_Archives", None)
    mock_ingest_core.assert_any_call("R2_Archives", None)
    mock_ingest_core.assert_any_call("R1_Archives_CSV_XML", None)


@patch("entsoe_pipeline.fms_metadata.core.legacy.save_yaml_catalog")
@patch("entsoe_pipeline.fms_metadata.core.legacy.list_folder_raw_items_recursive")
@patch("entsoe_pipeline.fms_metadata.core.legacy.list_folder_raw_items")
@patch("entsoe_pipeline.fms_metadata.core.legacy.create_fms_client")
@patch("entsoe_pipeline.fms_metadata.core.legacy.get_legacy_archive_folders")
def test_ingest_legacy_metadata_orchestrates_flow(
    mock_get_folders: MagicMock,
    mock_create_client: MagicMock,
    mock_list_items_flat: MagicMock,
    mock_list_items_rec: MagicMock,
    mock_save_catalog: MagicMock,
) -> None:
    """Verifies that legacy ingestion coordinates crawling and YAML generation."""
    # -------------------------------------------------------------------------
    # ARRANGE: Configure mock legacy archive rules, client, and file items
    # -------------------------------------------------------------------------
    mock_get_folders.return_value = ["OutagesCsv_r1"]
    mock_client = MagicMock()
    mock_create_client.return_value = mock_client
    mock_list_items_flat.return_value = []
    mock_list_items_rec.return_value = [
        {
            "name": "2014_12_Outages.csv",
            "fileId": "uuid-999",
            "size": 300,
            "originalSize": 600,
            "lastUpdatedTimestamp": "2015-01-05T00:00:00Z",
        }
    ]

    # -------------------------------------------------------------------------
    # ACT: Run the historical crawling pipeline for R1
    # -------------------------------------------------------------------------
    ingest_legacy_metadata("R1_Archives_CSV_XML")

    # -------------------------------------------------------------------------
    # ASSERT: Verify that files are listed, mapped, and cataloged for both envs
    # -------------------------------------------------------------------------
    assert mock_get_folders.call_count == 1
    assert mock_create_client.call_count == 1
    assert mock_list_items_flat.call_count == 1  # 1 root pre-fetch query
    assert mock_list_items_rec.call_count == 1  # 1 recursive directory crawl
    assert mock_save_catalog.call_count == 1


@patch("entsoe_pipeline.api.ls_fms._fetch_folder_page")
def test_list_folder_raw_items_recursive_crawls_nested(
    mock_fetch: MagicMock,
) -> None:
    """Verifies that recursive FMS crawl preserves nested file hierarchy."""
    # -------------------------------------------------------------------------
    # ARRANGE: Setup mock lister pages.
    # Page 1: contains a Folder "FR" and a root-level File "root_file.csv".
    # Page 2: (nested under "FR") contains a nested File "nested_file.csv".
    # -------------------------------------------------------------------------
    mock_client = MagicMock()
    mock_fetch.side_effect = [
        {
            "contentItemList": [
                {
                    "name": "FR",
                    "type": "Folder",
                    "fileId": "uuid-0",
                    "size": 0,
                    "originalSize": 0,
                    "lastUpdatedTimestamp": "2015-01-05T00:00:00Z",
                },
                {
                    "name": "root_file.csv",
                    "type": "File",
                    "fileId": "uuid-2",
                    "size": 100,
                    "originalSize": 200,
                    "lastUpdatedTimestamp": "2015-01-05T00:00:00Z",
                },
            ]
        },
        {
            "contentItemList": [
                {
                    "name": "nested_file.csv",
                    "type": "File",
                    "fileId": "uuid-1",
                    "size": 50,
                    "originalSize": 100,
                    "lastUpdatedTimestamp": "2015-01-05T00:00:00Z",
                }
            ]
        },
    ]

    # -------------------------------------------------------------------------
    # ACT: Run the recursive FMS crawl under a mock legacy folder
    # -------------------------------------------------------------------------
    results = list_folder_raw_items_recursive(
        mock_client,
        "BalanceManagementCsv_R1",
        root_dir="TP_Legacy_Publications",
    )

    # -------------------------------------------------------------------------
    # ASSERT: Verify names are normalized (FR/nested_file.csv) and sorted alphabetically
    # -------------------------------------------------------------------------
    assert len(results) == 2
    assert results[0]["name"] == "FR/nested_file.csv"
    assert results[1]["name"] == "root_file.csv"
    assert mock_fetch.call_count == 2
