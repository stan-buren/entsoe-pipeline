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

"""Unit tests for incremental delta metadata crawler logic."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from sqlalchemy import create_engine, select

from entsoe_pipeline.db import build_metadata
from entsoe_pipeline.fms_metadata.core.fms_metadata_delta import (
    resolve_exact_fms_folder,
    run_delta_metadata_refresh,
)


@pytest.fixture
def mock_db():
    """Provides a clean in-memory SQLite database populated with schema tables."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    db_metadata = build_metadata()
    db_metadata.create_all(engine)
    return engine


def test_resolve_exact_fms_folder() -> None:
    """Verify that recursive FMS folders are correctly resolved to day-level paths."""
    # 1. Test flat folder remains flat
    assert (
        resolve_exact_fms_folder(
            "ActualTotalLoad_6.1.A_r3", "2026_07_ActualTotalLoad_6.1.A_r3"
        )
        == "ActualTotalLoad_6.1.A_r3"
    )

    # 2. Test recursive folder maps to nested hierarchy
    folder = "OfferedTransferCapacitiesContinuousEvolution_11.1_r3.1"
    filename = "2026_07_08_HU_SK_OfferedTransferCapacitiesContinuousEvolution_11.1_r3.1"
    resolved = resolve_exact_fms_folder(folder, filename)
    assert resolved == f"{folder}/2026_07/2026_07_08/HU"


@patch("entsoe_pipeline.fms_metadata.core.fms_metadata_delta.get_db_url")
@patch("entsoe_pipeline.fms_metadata.core.fms_metadata_delta.create_fms_client")
@patch("entsoe_pipeline.fms_metadata.core.fms_metadata_delta.get_classifier_config")
@patch("entsoe_pipeline.fms_metadata.core.fms_metadata_delta.get_domain_folders")
@patch("entsoe_pipeline.fms_metadata.core.fms_metadata_delta.crawl_metadata_folder")
def test_delta_refresh_no_changes(
    mock_crawl: MagicMock,
    mock_folders: MagicMock,
    mock_config: MagicMock,
    mock_fms: MagicMock,
    mock_db_url: MagicMock,
    mock_db,
) -> None:
    """Verify that delta refresh skips crawling when all files are already up-to-date.

    Ref: 3A – Arrange, Act, Assert Guide
    "Arrange: Set up the object to be tested...
    Act: Act on the object...
    Assert: Make claims about the object..."
    """
    # -------------------------------------------------------------------------
    # ARRANGE:
    # 1. Setup mock database URL to redirect to our in-memory DB
    # -------------------------------------------------------------------------
    mock_db_url.return_value = "sqlite://"

    # 2. Populate folders and files in database (fully up-to-date state)
    metadata = build_metadata()
    fms_folders = metadata.tables["fms_folders"]
    fms_files = metadata.tables["fms_files"]

    with mock_db.connect() as conn:
        # Insert crawled folders
        conn.execute(
            fms_folders.insert().values(
                id=1,
                environment="iop",
                domain="Load",
                folder_path="/TP_export/ActualTotalLoad_6.1.A_r3/",
                item_count=1,
                original_bytes=1000,
                compressed_bytes=200,
                crawled_at=datetime.now(UTC),
            )
        )
        # Insert crawled files
        conn.execute(
            fms_files.insert().values(
                file_id="uuid-1",
                folder_id=1,
                name="2026_07_ActualTotalLoad_6.1.A_r3.zip",
                original_bytes=1000,
                compressed_bytes=200,
                last_updated="2026-07-07T13:55:09Z",
                xxhash="hash1",
            )
        )
        conn.commit()

    # 3. Setup mock classifier and folder discovery mapping
    mock_config.return_value.domain_order = ["Load"]
    mock_folders.return_value = ["ActualTotalLoad_6.1.A_r3"]

    # 4. Setup mock FMS client to return identical update log files
    mock_client = MagicMock()
    df_std = pd.DataFrame(
        [
            {
                "file_name": "2026_07_ActualTotalLoad_6.1.A_r3",
                "year": 2026,
                "month": 7,
                "max_update_time(UTC)": "07-07-2026 13:55:09",
                "export_time(UTC)": "07-07-2026 14:00:00",
            }
        ]
    )
    df_oce = pd.DataFrame(columns=["folder_name", "file_name", "max_update_time(UTC)"])

    def mock_download(folder, filename):
        if filename == "Export_log_r3.csv":
            return df_std
        return df_oce

    mock_client.download_single_file.side_effect = mock_download
    mock_fms.return_value = mock_client

    # -------------------------------------------------------------------------
    # ACT: Run delta metadata refresh
    # -------------------------------------------------------------------------
    with patch(
        "entsoe_pipeline.fms_metadata.core.fms_metadata_delta.create_engine",
        return_value=mock_db,
    ):
        run_delta_metadata_refresh(env="IOP", is_test=True, is_force=False)

    # -------------------------------------------------------------------------
    # ASSERT:
    # Verify no crawler jobs were scheduled since files are already fresh
    # -------------------------------------------------------------------------
    mock_crawl.assert_not_called()


@patch("entsoe_pipeline.fms_metadata.core.fms_metadata_delta.get_db_url")
@patch("entsoe_pipeline.fms_metadata.core.fms_metadata_delta.create_fms_client")
@patch("entsoe_pipeline.fms_metadata.core.fms_metadata_delta.get_classifier_config")
@patch("entsoe_pipeline.fms_metadata.core.fms_metadata_delta.get_domain_folders")
@patch("entsoe_pipeline.fms_metadata.core.fms_metadata_delta.crawl_metadata_folder")
def test_delta_refresh_with_updates(
    mock_crawl: MagicMock,
    mock_folders: MagicMock,
    mock_config: MagicMock,
    mock_fms: MagicMock,
    mock_db_url: MagicMock,
    mock_db,
) -> None:
    """Verify that delta refresh triggers targeted leaf crawl and upserts values correctly.

    Ref: 3A – Arrange, Act, Assert Guide
    "Arrange: Set up the object to be tested...
    Act: Act on the object...
    Assert: Make claims about the object..."
    """
    # -------------------------------------------------------------------------
    # ARRANGE:
    # 1. Setup mock database URL to redirect to our in-memory DB
    # -------------------------------------------------------------------------
    mock_db_url.return_value = "sqlite://"

    # 2. Populate folders and files in database (outdated state)
    metadata = build_metadata()
    fms_folders = metadata.tables["fms_folders"]
    fms_files = metadata.tables["fms_files"]

    with mock_db.connect() as conn:
        # Insert crawled folders
        conn.execute(
            fms_folders.insert().values(
                id=1,
                environment="iop",
                domain="Load",
                folder_path="/TP_export/ActualTotalLoad_6.1.A_r3/",
                item_count=1,
                original_bytes=1000,
                compressed_bytes=200,
                crawled_at=datetime.now(UTC),
            )
        )
        # Insert crawled files (old timestamp)
        conn.execute(
            fms_files.insert().values(
                file_id="uuid-1",
                folder_id=1,
                name="2026_07_ActualTotalLoad_6.1.A_r3.zip",
                original_bytes=1000,
                compressed_bytes=200,
                last_updated="2026-07-07T12:00:00Z",
                xxhash="hash1",
            )
        )
        conn.commit()

    # 3. Setup mock classifier and folder discovery mapping
    mock_config.return_value.domain_order = ["Load"]
    mock_folders.return_value = ["ActualTotalLoad_6.1.A_r3"]

    # 4. Setup mock FMS client to return NEWER update log files
    mock_client = MagicMock()
    df_std = pd.DataFrame(
        [
            {
                "file_name": "2026_07_ActualTotalLoad_6.1.A_r3",
                "year": 2026,
                "month": 7,
                "max_update_time(UTC)": "07-07-2026 13:55:09",  # Newer than 12:00:00Z
                "export_time(UTC)": "07-07-2026 14:00:00",
            }
        ]
    )
    df_oce = pd.DataFrame(columns=["folder_name", "file_name", "max_update_time(UTC)"])

    def mock_download(folder, filename):
        if filename == "Export_log_r3.csv":
            return df_std
        return df_oce

    mock_client.download_single_file.side_effect = mock_download
    mock_fms.return_value = mock_client

    # 5. Mock crawl metadata return values (new file details)
    mock_crawl.return_value = [
        {
            "file_id": "uuid-1",
            "name": "2026_07_ActualTotalLoad_6.1.A_r3.zip",
            "sizes": {
                "original": {"bytes": 1500},
                "compressed": {"bytes": 300},
            },
            "last_updated": "2026-07-07T13:55:09Z",
            "xxhash": "hash_new",
        }
    ]

    # -------------------------------------------------------------------------
    # ACT: Run delta metadata refresh
    # -------------------------------------------------------------------------
    with patch(
        "entsoe_pipeline.fms_metadata.core.fms_metadata_delta.create_engine",
        return_value=mock_db,
    ):
        run_delta_metadata_refresh(env="IOP", is_test=True, is_force=False)

    # -------------------------------------------------------------------------
    # ASSERT:
    # 1. Verify targeted crawl was scheduled for correct leaf folder
    # -------------------------------------------------------------------------
    mock_crawl.assert_called_once_with(
        client=mock_client,
        folder="ActualTotalLoad_6.1.A_r3",
        root_files_by_name={},
        api_counter=[0],
        env="IOP",
        root_dir="TP_export",
    )

    # 2. Verify that files and parent folder metrics were updated in database
    with mock_db.connect() as conn:
        file_row = conn.execute(
            select(fms_files.c.original_bytes, fms_files.c.xxhash)
        ).fetchone()
        folder_row = conn.execute(
            select(fms_folders.c.original_bytes, fms_folders.c.item_count)
        ).fetchone()

    assert file_row[0] == 1500
    assert file_row[1] == "hash_new"
    assert folder_row[0] == 1500
    assert folder_row[1] == 1
