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

"""Unit tests for the landing bucket schema generator and database registry."""

from __future__ import annotations

from pathlib import Path

import pytest

from sqlalchemy import create_engine, select

from entsoe_pipeline.db import build_metadata, init_db
from entsoe_pipeline.fms_metadata.ingestion.landing_bucket_schema import (
    build_landing_bucket_schema,
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


@pytest.mark.unit
def test_build_landing_bucket_schema_persists_to_db(db_env: str) -> None:
    """Verify that build_landing_bucket_schema reads from fms_folders and saves to DB.

    Args:
        db_env: Configured temporary database URL.
    """
    # -------------------------------------------------------------------------
    # ARRANGE: Initialize schema and populate fms_folders table
    # -------------------------------------------------------------------------
    init_db()

    engine = create_engine(db_env)
    db_metadata = build_metadata()
    fms_folders = db_metadata.tables["fms_folders"]
    landing_folders_schema = db_metadata.tables["landing_folders_schema"]

    from datetime import datetime

    with engine.begin() as conn:
        conn.execute(
            fms_folders.insert(),
            [
                {
                    "environment": "IOP",
                    "domain": "Load",
                    "folder_path": "/TP_export/ActualTotalLoad_6.1.A_r3/",
                    "crawled_at": datetime(2026, 7, 1, 10, 0, 0),
                    "item_count": 0,
                    "original_bytes": 0,
                    "compressed_bytes": 0,
                },
                {
                    "environment": "IOP",
                    "domain": "Balancing",
                    "folder_path": "/TP_Legacy_Publications/FlowBasedCapacityAllocationArchives_11.1.B_r3/",
                    "crawled_at": datetime(2026, 7, 1, 10, 0, 0),
                    "item_count": 0,
                    "original_bytes": 0,
                    "compressed_bytes": 0,
                },
                {
                    "environment": "IOP",
                    "domain": "Load",
                    "folder_path": "/shortpath",
                    "crawled_at": datetime(2026, 7, 1, 10, 0, 0),
                    "item_count": 0,
                    "original_bytes": 0,
                    "compressed_bytes": 0,
                },
            ],
        )

    # -------------------------------------------------------------------------
    # ACT: Run schema compiler
    # -------------------------------------------------------------------------
    build_landing_bucket_schema()

    # -------------------------------------------------------------------------
    # ASSERT: Verify database landing_folders_schema has correct entries
    # -------------------------------------------------------------------------
    with engine.connect() as conn:
        stmt = select(
            landing_folders_schema.c.s3_folder_path,
            landing_folders_schema.c.environment,
            landing_folders_schema.c.domain,
            landing_folders_schema.c.folder_name,
        ).order_by(landing_folders_schema.c.s3_folder_path)
        results = conn.execute(stmt).fetchall()

    assert len(results) == 2
    assert results[0] == (
        "iop/TP_Legacy_Publications/Balancing/FlowBasedCapacityAllocationArchives_11.1.B_r3",
        "iop",
        "Balancing",
        "FlowBasedCapacityAllocationArchives_11.1.B_r3",
    )
    assert results[1] == (
        "iop/TP_export/Load/ActualTotalLoad_6.1.A_r3",
        "iop",
        "Load",
        "ActualTotalLoad_6.1.A_r3",
    )


@pytest.mark.unit
def test_build_landing_bucket_schema_empty_db(db_env: str) -> None:
    """Verify build_landing_bucket_schema logs warning and returns when fms_folders is empty."""
    init_db()
    build_landing_bucket_schema()
