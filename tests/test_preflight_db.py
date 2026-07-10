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

"""Unit and integration tests for database schema preflight validation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from sqlalchemy import (
    Column,
    MetaData,
    String,
    Table,
    create_engine,
)

from entsoe_pipeline.db import build_metadata
from entsoe_pipeline.preflight.core.check_db import (
    validate_schema_ddl,
    verify_db_readiness,
)


@pytest.fixture
def memory_engine():
    """Provides an in-memory SQLite engine for schema verification."""
    return create_engine("sqlite://", connect_args={"check_same_thread": False})


def test_validate_schema_ddl_success(memory_engine) -> None:
    """Verify that a database containing the correct schema DDL passes validation."""
    metadata = build_metadata()
    # Create the correct tables
    metadata.create_all(memory_engine)

    # Should run successfully without raising
    validate_schema_ddl(memory_engine)


def test_validate_schema_ddl_missing_table(memory_engine) -> None:
    """Verify ValueError is raised if a required table is missing."""
    expected_meta = build_metadata()
    metadata = MetaData()

    # Recreate all tables except 'fms_files'
    for name, table in expected_meta.tables.items():
        if name == "fms_files":
            continue
        cols = [
            Column(
                c.name,
                c.type,
                nullable=c.nullable,
                primary_key=c.primary_key,
            )
            for c in table.columns
        ]
        Table(name, metadata, *cols)

    metadata.create_all(memory_engine)

    with pytest.raises(ValueError, match="Missing table 'fms_files'"):
        validate_schema_ddl(memory_engine)


def test_validate_schema_ddl_missing_column(memory_engine) -> None:
    """Verify ValueError is raised if a required column is missing."""
    expected_meta = build_metadata()
    metadata = MetaData()

    # Create all tables, but omit the 'domain' column in 'fms_folders'
    for name, table in expected_meta.tables.items():
        cols = []
        for c in table.columns:
            if name == "fms_folders" and c.name == "domain":
                continue
            cols.append(
                Column(
                    c.name,
                    c.type,
                    nullable=c.nullable,
                    primary_key=c.primary_key,
                )
            )
        Table(name, metadata, *cols)

    metadata.create_all(memory_engine)

    with pytest.raises(
        ValueError, match="Missing column 'domain' in table 'fms_folders'"
    ):
        validate_schema_ddl(memory_engine)


def test_validate_schema_ddl_nullability_mismatch(memory_engine) -> None:
    """Verify ValueError is raised if column nullability doesn't match."""
    expected_meta = build_metadata()
    metadata = MetaData()

    # Create all tables, but make 'domain' in 'fms_folders' nullable=True (expected False)
    for name, table in expected_meta.tables.items():
        cols = []
        for c in table.columns:
            nullable = c.nullable
            if name == "fms_folders" and c.name == "domain":
                nullable = True  # Mismatch
            cols.append(
                Column(
                    c.name,
                    c.type,
                    nullable=nullable,
                    primary_key=c.primary_key,
                )
            )
        Table(name, metadata, *cols)

    metadata.create_all(memory_engine)

    with pytest.raises(
        ValueError,
        match="Nullability mismatch for column 'fms_folders.domain'",
    ):
        validate_schema_ddl(memory_engine)


def test_validate_schema_ddl_type_mismatch(memory_engine) -> None:
    """Verify ValueError is raised if column type doesn't match."""
    expected_meta = build_metadata()
    metadata = MetaData()

    # Create all tables, but make 'item_count' in 'fms_folders' a String (expected Integer)
    for name, table in expected_meta.tables.items():
        cols = []
        for c in table.columns:
            col_type = c.type
            if name == "fms_folders" and c.name == "item_count":
                col_type = String  # Mismatch
            cols.append(
                Column(
                    c.name,
                    col_type,
                    nullable=c.nullable,
                    primary_key=c.primary_key,
                )
            )
        Table(name, metadata, *cols)

    metadata.create_all(memory_engine)

    with pytest.raises(
        ValueError, match="Type mismatch for column 'fms_folders.item_count'"
    ):
        validate_schema_ddl(memory_engine)


@patch("entsoe_pipeline.preflight.core.check_db.get_db_url")
@patch("entsoe_pipeline.preflight.core.check_db.create_engine")
def test_verify_db_readiness_connection_failure(
    mock_create_engine: MagicMock, mock_get_url: MagicMock
) -> None:
    """Verify verify_db_readiness raises RuntimeError on connection failures."""
    mock_get_url.return_value = "postgresql+psycopg://user:pass@localhost:5432/db"
    mock_create_engine.side_effect = Exception("Connection Refused")

    with pytest.raises(RuntimeError, match="Failed to connect to database"):
        verify_db_readiness()


@patch("entsoe_pipeline.preflight.core.check_db.get_db_url")
@patch("entsoe_pipeline.preflight.core.check_db.validate_schema_ddl")
def test_verify_db_readiness_ddl_failure(
    mock_validate_ddl: MagicMock, mock_get_url: MagicMock
) -> None:
    """Verify verify_db_readiness raises RuntimeError on DDL mismatch."""
    mock_get_url.return_value = "sqlite://"
    mock_validate_ddl.side_effect = ValueError("DDL Mismatch")

    with pytest.raises(RuntimeError, match="Database DDL validation failed"):
        verify_db_readiness()
