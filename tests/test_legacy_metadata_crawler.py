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
delegation using database persistence.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sqlalchemy import create_engine, select

from entsoe_pipeline.api.ls_fms import list_folder_raw_items_recursive
from entsoe_pipeline.db import build_metadata, init_db
from entsoe_pipeline.fms_metadata.core import (
    ingest_all_legacy_metadata,
)
from entsoe_pipeline.fms_metadata.core.legacy_metadata_crawler import (
    ingest_legacy_metadata,
)


@pytest.fixture(name="db_env")
def fixture_db_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Fixture to configure and return a temporary SQLite database URL.

    Args:
        tmp_path: Pytest temporary directory path.
        monkeypatch: Pytest monkeypatch utility.

    Returns:
        str: SQLite connection URL pointing to the temporary file.
    """
    db_file = tmp_path / "test_metadata.db"
    url = f"sqlite:///{db_file}"
    monkeypatch.setenv("DATABASE_URL", url)
    return url


@patch(
    "entsoe_pipeline.fms_metadata.core.legacy_metadata_crawler.ingest_legacy_metadata"
)
def test_ingest_all_legacy_metadata_delegates_to_core(
    mock_ingest_core: MagicMock,
) -> None:
    """Verifies that legacy ingestion crawls all three archives."""
    # -------------------------------------------------------------------------
    # ACT: Trigger the global legacy metadata crawling process
    # -------------------------------------------------------------------------
    ingest_all_legacy_metadata(env="iop")

    # -------------------------------------------------------------------------
    # ASSERT: Verify it delegates cleanly for R1, R2, and R3 archives
    # -------------------------------------------------------------------------
    assert mock_ingest_core.call_count == 3
    mock_ingest_core.assert_any_call("R3_Archives", "iop", None, None)
    mock_ingest_core.assert_any_call("R2_Archives", "iop", None, None)
    mock_ingest_core.assert_any_call("R1_Archives_CSV_XML", "iop", None, None)


@patch(
    "entsoe_pipeline.fms_metadata.core.legacy_metadata_crawler.crawl_metadata_folder"
)
@patch(
    "entsoe_pipeline.fms_metadata.core.legacy_metadata_crawler.fetch_root_files_mapping"
)
@patch("entsoe_pipeline.fms_metadata.core.legacy_metadata_crawler.create_fms_client")
@patch(
    "entsoe_pipeline.fms_metadata.core.legacy_metadata_crawler.get_legacy_archive_folders"
)
def test_ingest_legacy_metadata_orchestrates_flow(
    mock_get_folders: MagicMock,
    mock_create_client: MagicMock,
    mock_fetch_mapping: MagicMock,
    mock_crawl_folder: MagicMock,
    db_env: str,
) -> None:
    """Verifies that legacy ingestion coordinates crawling and DB storage.

    Args:
        mock_get_folders: Mock folders list retriever.
        mock_create_client: Mock client creator.
        mock_fetch_mapping: Mock recursive root files mapping resolver.
        mock_crawl_folder: Mock recursive folder crawler.
        db_env: Configured temporary database URL.
    """
    # -------------------------------------------------------------------------
    # ARRANGE: Configure mock legacy archive rules, client, and file items
    # -------------------------------------------------------------------------
    init_db()
    engine = create_engine(db_env)
    metadata = build_metadata()
    fms_folders = metadata.tables["fms_folders"]

    mock_get_folders.return_value = ["OutagesCsv_r1"]
    mock_client = MagicMock()
    mock_create_client.return_value = mock_client
    mock_fetch_mapping.return_value = {}
    mock_crawl_folder.return_value = [
        {
            "name": "2014_12_Outages.csv",
            "file_id": "uuid-999",
            "sizes": {
                "compressed": {"bytes": 300, "mb": 0.0003},
                "original": {"bytes": 600, "mb": 0.0006},
            },
            "last_updated": "2015-01-05T00:00:00Z",
            "xxhash": "some-hash",
        }
    ]

    # -------------------------------------------------------------------------
    # ACT: Run the historical crawling pipeline for R1
    # -------------------------------------------------------------------------
    ingest_legacy_metadata(archive_name="R1_Archives_CSV_XML", env="iop")

    # -------------------------------------------------------------------------
    # ASSERT: Verify that files are listed, mapped, and database is populated
    # -------------------------------------------------------------------------
    assert mock_get_folders.call_count == 1
    assert mock_create_client.call_count == 1
    assert mock_fetch_mapping.call_count == 1  # 1 root pre-fetch query
    assert mock_crawl_folder.call_count == 1  # 1 recursive directory crawl

    # Assert rows are persisted in SQLite
    with engine.connect() as conn:
        f_row = conn.execute(
            select(fms_folders.c.item_count, fms_folders.c.original_bytes)
        ).fetchone()
        assert f_row is not None
        assert f_row[0] == 1
        assert f_row[1] == 600


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
