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

"""Unit tests for metadata crawlers common helper utilities."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from sqlalchemy import create_engine, select

from entsoe_pipeline.db import build_metadata, init_db
from entsoe_pipeline.fms_metadata.core.metadata_crawlers_common import (
    fetch_root_files_mapping,
    save_crawled_folder_metadata,
)


@pytest.fixture(name="db_env")
def fixture_db_env(tmp_path, monkeypatch) -> str:
    """Fixture to configure and return a temporary SQLite database URL."""
    db_file = tmp_path / "test_metadata_common.db"
    url = f"sqlite:///{db_file}"
    monkeypatch.setenv("DATABASE_URL", url)
    return url


@pytest.mark.unit
@patch(
    "entsoe_pipeline.fms_metadata.core.metadata_crawlers_common.list_folder_raw_items"
)
def test_fetch_root_files_mapping_exception(mock_list: MagicMock, caplog) -> None:
    """Verify that fetch_root_files_mapping logs exception and returns empty dict on failure."""
    # Arrange
    import logging

    logging.getLogger("entsoe_pipeline").propagate = True
    client = MagicMock()
    mock_list.side_effect = Exception("FMS API connection failure")

    # Act
    result = fetch_root_files_mapping(client, [0], "iop")

    # Assert
    assert result == {}
    assert "Failed to fetch root files mapping" in caplog.text


@pytest.mark.unit
@patch(
    "entsoe_pipeline.fms_metadata.core.metadata_crawlers_common.list_folder_raw_items"
)
def test_fetch_root_files_mapping_success(mock_list: MagicMock) -> None:
    """Verify that fetch_root_files_mapping returns filename mapping on success."""
    # Arrange
    client = MagicMock()
    mock_list.return_value = [
        {"name": "file1.csv", "size": 100},
        {"name": "file2.csv", "size": 200},
    ]

    # Act
    result = fetch_root_files_mapping(client, [0], "iop")

    # Assert
    assert result == {
        "file1.csv": {"name": "file1.csv", "size": 100},
        "file2.csv": {"name": "file2.csv", "size": 200},
    }


@pytest.mark.unit
def test_save_crawled_folder_metadata_update(db_env: str) -> None:
    """Verify save_crawled_folder_metadata updates existing folder metadata in the database."""
    # Arrange
    init_db()
    engine = create_engine(db_env)
    db_metadata = build_metadata()
    fms_folders = db_metadata.tables["fms_folders"]
    fms_files = db_metadata.tables["fms_files"]

    env = "iop"
    domain = "Load"
    folder_path = "/TP_export/ActualTotalLoad_6.1.A_r3/"

    # Insert initial folder record
    with engine.begin() as conn:
        conn.execute(
            fms_folders.insert(),
            [
                {
                    "environment": env,
                    "domain": domain,
                    "folder_path": folder_path,
                    "crawled_at": datetime(2026, 7, 1, 10, 0, 0, tzinfo=UTC),
                    "item_count": 0,
                    "original_bytes": 0,
                    "compressed_bytes": 0,
                }
            ],
        )

    # Act
    folder_meta = {
        "item_count": 5,
        "sizes": {
            "original": {"bytes": 5000},
            "compressed": {"bytes": 2500},
        },
    }
    save_crawled_folder_metadata(
        engine=engine,
        fms_folders=fms_folders,
        fms_files=fms_files,
        env=env,
        domain=domain,
        folder_path=folder_path,
        folder_meta=folder_meta,
        files=[],
    )

    # Assert
    with engine.connect() as conn:
        stmt = select(
            fms_folders.c.item_count,
            fms_folders.c.original_bytes,
            fms_folders.c.compressed_bytes,
        ).where(
            fms_folders.c.environment == env,
            fms_folders.c.folder_path == folder_path,
        )
        row = conn.execute(stmt).fetchone()

    assert row is not None
    assert row[0] == 5
    assert row[1] == 5000
    assert row[2] == 2500
