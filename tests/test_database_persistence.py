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

"""Unit Tests for ENTSO-E physical metadata database persistence.

Verifies schema initialization, dynamically generated table structure, and
folder/file upserts against a file-backed temporary SQLite database.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sqlalchemy import create_engine, select

from entsoe_pipeline.db import build_metadata, init_db


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


def test_database_schema_initialization(db_env: str) -> None:
    """Verify that init_db successfully compiles and creates all tables.

    Args:
        db_env: Configured temporary database URL.
    """
    # -------------------------------------------------------------------------
    # ARRANGE: Create connection engine and resolve table metadata
    # -------------------------------------------------------------------------
    engine = create_engine(db_env)
    metadata = build_metadata()

    # -------------------------------------------------------------------------
    # ACT: Run schema initializer DDL
    # -------------------------------------------------------------------------
    init_db()

    # -------------------------------------------------------------------------
    # ASSERT: Tables exist and have the correct column structure
    # -------------------------------------------------------------------------
    with engine.connect() as conn:
        # Check folders table existence and columns
        fms_folders = metadata.tables["fms_folders"]
        stmt_folders = select(fms_folders.c.id, fms_folders.c.folder_path)
        # Should not raise any table-not-found exceptions
        conn.execute(stmt_folders)

        # Check files table existence and columns
        fms_files = metadata.tables["fms_files"]
        stmt_files = select(fms_files.c.file_id, fms_files.c.folder_id)
        conn.execute(stmt_files)


def test_folder_and_file_upsert_operations(db_env: str) -> None:
    """Verify folder upsert and file synchronization operations.

    Args:
        db_env: Configured temporary database URL.
    """
    # -------------------------------------------------------------------------
    # ARRANGE: Initialize schema and setup SQLAlchemy connections
    # -------------------------------------------------------------------------
    init_db()
    engine = create_engine(db_env)
    metadata = build_metadata()
    fms_folders = metadata.tables["fms_folders"]
    fms_files = metadata.tables["fms_files"]

    env = "iop"
    domain = "Load"
    folder_path = "/TP_export/Load/ActualTotalLoad_6.1.A_r3/"

    # -------------------------------------------------------------------------
    # ACT: 1. Insert folder record
    # -------------------------------------------------------------------------
    with engine.begin() as conn:
        res = conn.execute(
            fms_folders.insert().values(
                environment=env,
                domain=domain,
                folder_path=folder_path,
                item_count=2,
                original_bytes=2048,
                compressed_bytes=512,
            )
        )
        folder_id = res.inserted_primary_key[0]

        # Insert two files
        conn.execute(
            fms_files.insert(),
            [
                {
                    "file_id": "uuid-1",
                    "folder_id": folder_id,
                    "name": "file_1.csv",
                    "original_bytes": 1024,
                    "compressed_bytes": 256,
                    "last_updated": "2026-06-30T12:00:00Z",
                    "xxhash": "hash-1",
                },
                {
                    "file_id": "uuid-2",
                    "folder_id": folder_id,
                    "name": "file_2.csv",
                    "original_bytes": 1024,
                    "compressed_bytes": 256,
                    "last_updated": "2026-06-30T12:00:00Z",
                    "xxhash": "hash-2",
                },
            ],
        )

    # -------------------------------------------------------------------------
    # ASSERT: 1. Check folder stats and files exists
    # -------------------------------------------------------------------------
    with engine.connect() as conn:
        f_row = conn.execute(
            select(fms_folders.c.item_count, fms_folders.c.original_bytes).where(
                fms_folders.c.id == folder_id
            )
        ).fetchone()
        assert f_row is not None
        assert f_row[0] == 2
        assert f_row[1] == 2048

        files_count = conn.execute(
            select(fms_files.c.file_id).where(fms_files.c.folder_id == folder_id)
        ).fetchall()
        assert len(files_count) == 2

    # -------------------------------------------------------------------------
    # ACT: 2. Perform delta-sync (simulate crawling again with one file removed and one updated)
    # -------------------------------------------------------------------------
    with engine.begin() as conn:
        # Update folder stats
        conn.execute(
            fms_folders.update()
            .where(fms_folders.c.id == folder_id)
            .values(
                item_count=1,
                original_bytes=512,
                compressed_bytes=128,
            )
        )

        # Sync files: delete and insert current ones
        conn.execute(fms_files.delete().where(fms_files.c.folder_id == folder_id))
        conn.execute(
            fms_files.insert().values(
                file_id="uuid-1",
                folder_id=folder_id,
                name="file_1.csv",
                original_bytes=512,
                compressed_bytes=128,
                last_updated="2026-06-30T13:00:00Z",
                xxhash="hash-updated",
            )
        )

    # -------------------------------------------------------------------------
    # ASSERT: 2. Only file_1.csv exists, sizes and updates mapped
    # -------------------------------------------------------------------------
    with engine.connect() as conn:
        f_row = conn.execute(
            select(fms_folders.c.item_count, fms_folders.c.original_bytes).where(
                fms_folders.c.id == folder_id
            )
        ).fetchone()
        assert f_row is not None
        assert f_row[0] == 1
        assert f_row[1] == 512

        file_rows = conn.execute(
            select(fms_files.c.file_id, fms_files.c.xxhash).where(
                fms_files.c.folder_id == folder_id
            )
        ).fetchall()
        assert len(file_rows) == 1
        assert file_rows[0][0] == "uuid-1"
        assert file_rows[0][1] == "hash-updated"


def test_init_db_main(db_env: str) -> None:
    """Verify init_entsoe_metadata_db_schema CLI main execution.

    Args:
        db_env: Configured temporary database URL.
    """
    # -------------------------------------------------------------------------
    # ACT: Run DDL CLI builder using runpy for 100% main coverage
    # -------------------------------------------------------------------------
    import runpy

    from entsoe_pipeline import INIT_DB_SCHEMA_PY

    runpy.run_path(str(INIT_DB_SCHEMA_PY), run_name="__main__")

    # -------------------------------------------------------------------------
    # ASSERT: Confirm engine can query folders table
    # -------------------------------------------------------------------------
    engine = create_engine(db_env)
    metadata = build_metadata()
    fms_folders = metadata.tables["fms_folders"]
    with engine.connect() as conn:
        conn.execute(select(fms_folders.c.id))
