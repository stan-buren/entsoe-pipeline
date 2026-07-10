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

"""Unit Tests for FMS Core Ingestion Orchestration Engine.

Verifies the central metadata gathering and database persistence flows for
active FMS domains using temporary SQLite database.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sqlalchemy import create_engine, select

from entsoe_pipeline.db import build_metadata, init_db
from entsoe_pipeline.fms_metadata.core.domain_metadata_crawler import (
    ingest_domain_metadata,
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
    "entsoe_pipeline.fms_metadata.core.domain_metadata_crawler.crawl_metadata_folder"
)
@patch(
    "entsoe_pipeline.fms_metadata.core.domain_metadata_crawler.fetch_root_files_mapping"
)
@patch("entsoe_pipeline.fms_metadata.core.domain_metadata_crawler.create_fms_client")
@patch("entsoe_pipeline.fms_metadata.core.domain_metadata_crawler.get_domain_folders")
def test_ingest_domain_metadata_orchestrates_flow(
    mock_get_folders: MagicMock,
    mock_create_client: MagicMock,
    mock_fetch_mapping: MagicMock,
    mock_crawl_folder: MagicMock,
    db_env: str,
) -> None:
    """Verifies that ingest_domain_metadata orchestrates FMS ingestion and DB storage.

    Args:
        mock_get_folders: Mock domain folders resolver.
        mock_create_client: Mock client creator.
        mock_fetch_mapping: Mock recursive root files mapping resolver.
        mock_crawl_folder: Mock folder files crawler.
        db_env: Configured temporary database URL.
    """
    # -------------------------------------------------------------------------
    # ARRANGE: Mock CLI folder resolve and raw API JSON endpoints
    # -------------------------------------------------------------------------
    init_db()
    engine = create_engine(db_env)
    metadata = build_metadata()
    fms_folders = metadata.tables["fms_folders"]

    mock_get_folders.return_value = ["ActualTotalLoad_r3"]
    mock_client = MagicMock()
    mock_create_client.return_value = mock_client
    mock_fetch_mapping.return_value = {}
    mock_crawl_folder.return_value = [
        {
            "name": "2026_05_Load.csv",
            "file_id": "uuid-1",
            "sizes": {
                "compressed": {"bytes": 100, "mb": 0.0001},
                "original": {"bytes": 200, "mb": 0.0002},
            },
            "last_updated": "2026-05-28T12:00:00Z",
            "xxhash": "some-hash",
        }
    ]

    # -------------------------------------------------------------------------
    # ACT: Trigger the core metadata pipeline for a domain
    # -------------------------------------------------------------------------
    ingest_domain_metadata("Load", env="iop")

    # -------------------------------------------------------------------------
    # ASSERT: Verify environments are crawled and catalogs are serialized to DB
    # -------------------------------------------------------------------------
    assert mock_get_folders.call_count == 1
    assert mock_create_client.call_count == 1
    assert mock_fetch_mapping.call_count == 1
    assert mock_crawl_folder.call_count == 1

    with engine.connect() as conn:
        f_row = conn.execute(
            select(fms_folders.c.item_count, fms_folders.c.original_bytes)
        ).fetchone()
        assert f_row is not None
        assert f_row[0] == 1
        assert f_row[1] == 200
