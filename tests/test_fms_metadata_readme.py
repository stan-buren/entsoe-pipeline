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

"""Unit Tests for FMS Metadata Catalog Report Generator.

Verifies that the report generator successfully queries the database and
aggregates metadata into the target human-readable Markdown report file.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from sqlalchemy import create_engine

from entsoe_pipeline.db import build_metadata, init_db
from entsoe_pipeline.fms_metadata.report.fms_metadata_readme import (
    _format_size,
    compile_report,
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


def test_format_size() -> None:
    """Verifies that format_size maps Megabyte floats correctly."""
    assert _format_size(10.0) == "10.00 MB"
    assert _format_size(0.0) == "0.00 MB"


def test_compile_report_generates_markdown(db_env: str, tmp_path: Path) -> None:
    """Verifies that compile_report collects database rows and writes report.

    Args:
        db_env: Configured temporary database URL.
        tmp_path: Pytest temporary directory path.
    """
    # -------------------------------------------------------------------------
    # ARRANGE: Initialize schema and insert test rows for active and legacy catalogs
    # -------------------------------------------------------------------------
    init_db()
    engine = create_engine(db_env)
    metadata = build_metadata()
    fms_folders = metadata.tables["fms_folders"]
    fms_files = metadata.tables["fms_files"]

    with engine.begin() as conn:
        # Insert active folder and its files
        res_act = conn.execute(
            fms_folders.insert().values(
                environment="iop",
                domain="Load",
                folder_path="/TP_export/Load/ActualTotalLoad_6.1.A_r3/",
                item_count=1,
                original_bytes=1024 * 1024 * 10,  # 10 MB
                compressed_bytes=1024 * 1024 * 1,  # 1 MB
            )
        )
        folder_act_id = res_act.inserted_primary_key[0]
        conn.execute(
            fms_files.insert().values(
                file_id="act-file-1",
                folder_id=folder_act_id,
                name="2023_04_Load.csv",
                original_bytes=1024 * 1024 * 10,
                compressed_bytes=1024 * 1024 * 1,
                last_updated="2026-06-30T12:00:00Z",
                xxhash="hash-1",
            )
        )

        # Insert legacy folder and its files
        res_leg = conn.execute(
            fms_folders.insert().values(
                environment="iop",
                domain="R3_Archives",
                folder_path="/TP_Legacy_Publications/R3_Archives/FlowBasedCapacityAllocationArchives_11.1.B_r3/",
                item_count=1,
                original_bytes=1024 * 1024 * 50,  # 50 MB
                compressed_bytes=1024 * 1024 * 5,  # 5 MB
            )
        )
        folder_leg_id = res_leg.inserted_primary_key[0]
        conn.execute(
            fms_files.insert().values(
                file_id="leg-file-1",
                folder_id=folder_leg_id,
                name="2018_12_FlowBased.zip",
                original_bytes=1024 * 1024 * 50,
                compressed_bytes=1024 * 1024 * 5,
                last_updated="2026-06-30T12:00:00Z",
                xxhash="hash-2",
            )
        )

    # Set temporary report path
    test_report_file = tmp_path / "README.md"

    # -------------------------------------------------------------------------
    # ACT: Run report compilation with patched output path
    # -------------------------------------------------------------------------
    with patch(
        "entsoe_pipeline.fms_metadata.report.fms_metadata_readme.FMS_REPORT_PATH",
        test_report_file,
    ):
        compile_report()

    # -------------------------------------------------------------------------
    # ASSERT: Assert file exists and contains compiled summary statistics
    # -------------------------------------------------------------------------
    assert test_report_file.exists()
    content = test_report_file.read_text(encoding="utf-8")

    # Assert active domain values in the tables
    assert "Active Publication Domains" in content
    assert "Load" in content
    assert "10.00 MB" in content
    assert "10.00x" in content  # Compression ratio
    assert "2023_04 to 2023_04" in content

    # Assert legacy archives values in the tables
    assert "Historical Publications Archives" in content
    assert "R3_Archives" in content
    assert "50.00 MB" in content
    assert "2018_12 to 2018_12" in content

    # Assert combined totals
    assert "Combined Total (IOP):" in content
    assert "`2` files" in content
