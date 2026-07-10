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

"""Dynamic, schema-driven database initialization helper for ENTSO-E FMS Metadata."""

from __future__ import annotations

import logging
import os

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    create_engine,
)

from entsoe_pipeline import (
    get_db_schema_config,
    get_hosts_config,
    get_ports_config,
)

logger = logging.getLogger("entsoe_pipeline.db.init_entsoe_metadata_db_schema")


def get_db_url() -> str:
    """Resolves and returns the database connection URL dynamically from configs.

    Returns:
        str: The fully formatted JDBC-like PostgreSQL database connection URL.
    """
    if env_url := os.environ.get("DATABASE_URL"):
        return env_url

    host = get_hosts_config().database
    port = get_ports_config().database
    db_name = os.environ.get("DATABASE_NAME", "entsoe_metadata")
    username = os.environ.get("DATABASE_USER", "entsoe")
    password = os.environ.get("DATABASE_PASSWORD", "password")

    return f"postgresql+psycopg://{username}:{password}@{host}:{port}/{db_name}"


def map_type(type_name: str) -> type:
    """Maps database-neutral YAML types to SQLAlchemy column type classes.

    Args:
        type_name: A string representing the database-neutral column type
          declared in the schema configuration YAML file.

    Returns:
        type: The matching SQLAlchemy column type class (e.g. Integer, String).

    Raises:
        ValueError: If the type_name does not match any allowed mapping keys.
    """
    mapping = {
        "integer": Integer,
        "bigint": BigInteger,
        "string": String,
        "datetime": DateTime,
    }
    sa_type = mapping.get(type_name.lower())
    if not sa_type:
        raise ValueError(f"Unsupported column type in schema contract: {type_name}")
    return sa_type


def build_metadata() -> MetaData:
    """Dynamically compiles SQLAlchemy metadata from the YAML schema contract.

    Returns:
        MetaData: A populated SQLAlchemy MetaData catalog mapping all dynamic
          table definitions.
    """
    schema_data = get_db_schema_config()
    metadata = MetaData()
    tables_data = schema_data.get("tables", {})

    for table_name, table_def in tables_data.items():
        columns = []

        # 1. Map columns dynamically from config properties.
        for col_name, col_def in table_def.get("columns", {}).items():
            sa_type = map_type(col_def.get("type", "string"))

            col_args = []
            if fk := col_def.get("foreign_key"):
                col_args.append(ForeignKey(fk))

            sa_col = Column(
                col_name,
                sa_type,
                *col_args,
                primary_key=col_def.get("primary_key", False),
                autoincrement=col_def.get("autoincrement", False),
                nullable=col_def.get("nullable", True),
                index=col_def.get("index", False),
            )
            columns.append(sa_col)

        # 2. Map table-level constraints dynamically from config.
        constraints = []
        for const_name, const_def in table_def.get("constraints", {}).items():
            const_type = const_def.get("type")
            if const_type == "unique":
                cols = const_def.get("columns", [])
                constraints.append(UniqueConstraint(*cols, name=const_name))

        # 3. Instantiate Table and register it dynamically in Metadata.
        Table(table_name, metadata, *columns, *constraints)

    return metadata


def init_db() -> None:
    """Initializes or updates database schema based on the YAML schema contract."""
    logger.info("Initializing ENTSO-E physical metadata database schema...")
    url = get_db_url()

    # SQLite requires check_same_thread=False for multi-threaded test runs
    if url.startswith("sqlite"):
        engine = create_engine(url, connect_args={"check_same_thread": False})
    else:
        engine = create_engine(url)

    metadata = build_metadata()
    metadata.create_all(engine)
    logger.info("Database schema initialized successfully.")


if __name__ == "__main__":
    from entsoe_pipeline.logger import setup_logging

    setup_logging()
    init_db()
