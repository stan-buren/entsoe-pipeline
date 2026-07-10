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

"""PostgreSQL database connectivity and DDL schema validation preflight checks."""

from __future__ import annotations

import logging

from typing import TYPE_CHECKING

from sqlalchemy import create_engine, inspect, text

from entsoe_pipeline.db import build_metadata, get_db_url

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

logger = logging.getLogger("entsoe_pipeline.preflight.core.check_db")


def verify_db_readiness() -> None:
    """Verifies database connectivity and validates existing DDL against the YAML contract.

    Raises:
        RuntimeError: If connection cannot be established or DDL mismatch is detected.
    """
    logger.info("Performing database preflight checks...")
    db_url = get_db_url()

    # 1. Test connectivity
    try:
        if db_url.startswith("sqlite"):
            engine = create_engine(db_url, connect_args={"check_same_thread": False})
        else:
            engine = create_engine(db_url)

        # Force a connection check
        with engine.connect() as conn:
            # Simple query to verify connection
            conn.execute(text("SELECT 1"))
    except Exception as e:
        raise RuntimeError(f"Failed to connect to database: {e}") from e

    # 2. Validate DDL
    try:
        validate_schema_ddl(engine)
    except Exception as e:
        raise RuntimeError(f"Database DDL validation failed: {e}") from e

    logger.info("Database preflight checks completed successfully.")


def validate_schema_ddl(engine: Engine) -> None:
    """Compares the reflected database columns/tables against the expected MetaData catalog.

    Args:
        engine: The initialized SQLAlchemy connection engine.

    Raises:
        ValueError: If any table or column definition is missing or mismatched.
    """
    expected_metadata = build_metadata()
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    for table_name, expected_table in expected_metadata.tables.items():
        if table_name not in existing_tables:
            raise ValueError(
                f"Missing table '{table_name}' in database. "
                "Please initialize the schema first."
            )

        # Retrieve actual columns
        actual_cols_info = inspector.get_columns(table_name)
        actual_cols = {col["name"]: col for col in actual_cols_info}

        for expected_col in expected_table.columns:
            col_name = expected_col.name
            if col_name not in actual_cols:
                raise ValueError(
                    f"Missing column '{col_name}' in table '{table_name}'."
                )

            actual_col = actual_cols[col_name]

            # Verify nullability
            if expected_col.nullable != actual_col["nullable"]:
                raise ValueError(
                    f"Nullability mismatch for column '{table_name}.{col_name}': "
                    f"expected {expected_col.nullable}, found {actual_col['nullable']}."
                )

            # Verify python types
            try:
                expected_py_type = expected_col.type.python_type
                actual_py_type = actual_col["type"].python_type
            except NotImplementedError:
                expected_py_type = str(expected_col.type)
                actual_py_type = str(actual_col["type"])

            if expected_py_type != actual_py_type:
                raise ValueError(
                    f"Type mismatch for column '{table_name}.{col_name}': "
                    f"expected python type {expected_py_type}, found {actual_py_type}."
                )
