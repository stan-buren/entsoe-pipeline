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

"""Unit tests for catalog sizes calculation and ingestion workflows."""

from __future__ import annotations

from pathlib import Path

import pytest

from sqlalchemy import create_engine

from entsoe_pipeline.db import build_metadata, init_db
from entsoe_pipeline.fms_metadata.core import compile_sizes_report
from entsoe_pipeline.fms_metadata.ingestion.sizes_ingest import (
    ingest_all_catalog_sizes,
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


def test_compile_sizes_report(db_env: str) -> None:
    """Verify that compile_sizes_report aggregates and ranks data from database.

    Args:
        db_env: Configured temporary database URL.
    """
    # -------------------------------------------------------------------------
    # ARRANGE: Initialize schema and insert mock rows
    # -------------------------------------------------------------------------
    init_db()
    engine = create_engine(db_env)
    metadata = build_metadata()
    fms_folders = metadata.tables["fms_folders"]

    with engine.begin() as conn:
        conn.execute(
            fms_folders.insert(),
            [
                {
                    "environment": "iop",
                    "domain": "Load",
                    "folder_path": "/TP_export/ActualTotalLoad_6.1.A_r3/",
                    "item_count": 10,
                    "original_bytes": 10485760,  # 10 MB
                    "compressed_bytes": 1024,
                },
                {
                    "environment": "iop",
                    "domain": "Load",
                    "folder_path": "/TP_export/DayAheadTotalLoadForecast_6.1.B_r3/",
                    "item_count": 5,
                    "original_bytes": 5242880,  # 5 MB
                    "compressed_bytes": 512,
                },
                {
                    "environment": "iop",
                    "domain": "Generation",
                    "folder_path": "/TP_export/AggregatedGenerationPerType_16.1.B_C_r3/",
                    "item_count": 20,
                    "original_bytes": 20971520,  # 20 MB
                    "compressed_bytes": 2048,
                },
                {
                    "environment": "iop",
                    "domain": "OtherMarketInformation",
                    "folder_path": "/TP_export/Export_log_r3.csv",
                    "item_count": 1,
                    "original_bytes": 1048576,  # 1 MB
                    "compressed_bytes": 100,
                },
            ],
        )

    # -------------------------------------------------------------------------
    # ACT: Compile active publication sizes report
    # -------------------------------------------------------------------------
    report = compile_sizes_report(env_name="iop", root_dir="TP_export")

    # -------------------------------------------------------------------------
    # ASSERT: Check aggregated sizes, total files, and correct desc ranking
    # -------------------------------------------------------------------------
    assert report["total_size_mb"] == 36.0
    assert report["total_files"] == 36
    assert len(report["folders"]) == 3
    assert len(report["files"]) == 1

    # Check files mapping
    assert report["files"][0]["name"] == "/TP_export/Export_log_r3.csv"
    assert report["files"][0]["raw_size_mb"] == 1.0

    # Heaviest folder should rank first
    assert (
        report["folders"][0]["name"]
        == "/TP_export/AggregatedGenerationPerType_16.1.B_C_r3/"
    )
    assert report["folders"][0]["raw_size_mb"] == 20.0
    assert report["folders"][0]["files_count"] == 20

    # Second heaviest
    assert report["folders"][1]["name"] == "/TP_export/ActualTotalLoad_6.1.A_r3/"
    assert report["folders"][1]["raw_size_mb"] == 10.0

    # Lightest folder
    assert (
        report["folders"][2]["name"] == "/TP_export/DayAheadTotalLoadForecast_6.1.B_r3/"
    )
    assert report["folders"][2]["raw_size_mb"] == 5.0


def test_ingest_all_catalog_sizes_generates_files(db_env: str, tmp_path: Path) -> None:
    """Verify that all size reports are built and stored.

    Args:
        db_env: Configured temporary database URL.
        tmp_path: Pytest temporary directory path.
    """
    # -------------------------------------------------------------------------
    # ARRANGE: Initialize schema
    # -------------------------------------------------------------------------
    init_db()

    # -------------------------------------------------------------------------
    # ACT: Run size reports ingestion to temporary directory
    # -------------------------------------------------------------------------
    ingest_all_catalog_sizes(sizes_dir=tmp_path)

    # -------------------------------------------------------------------------
    # ASSERT: All 4 YAML reports must be written to sizes_dir
    # -------------------------------------------------------------------------
    assert (tmp_path / "iop_tp_export.yml").exists()
    assert (tmp_path / "iop_tp_legacy_publications.yml").exists()
    assert (tmp_path / "prod_tp_export.yml").exists()
    assert (tmp_path / "prod_tp_legacy_publications.yml").exists()
