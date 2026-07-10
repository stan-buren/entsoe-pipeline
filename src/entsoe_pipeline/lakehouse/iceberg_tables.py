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

"""Metadata and DDL creation engine for Apache Iceberg tables in the Lakehouse."""

from __future__ import annotations

import logging

from pyspark.sql import SparkSession
from pyspark.sql.types import StructType

from entsoe_pipeline.config.config_loader import (
    get_lakehouse_parquet_codec_config,
)

logger = logging.getLogger("entsoe_pipeline.lakehouse.iceberg_tables")

# REST Catalog database namespace
_LAKEHOUSE_DB = "lakehouse.db"


def ensure_iceberg_table_exists(
    spark: SparkSession, fms_name: str, df_schema: StructType
) -> str:
    """Verifies Iceberg table presence and programmatically creates it if missing.

    Reads storage Parquet compression settings from the central YAML configuration loader,
    compiles a DDL CREATE TABLE statement using the provided DataFrame schema field definitions,
    and commits it via the active SparkSession catalog.

    Args:
        spark: The active SparkSession instance.
        fms_name: Strict FMS contract schema name (e.g. 'OtherMarketInformation_r3').
        df_schema: StructType schema representing target database column fields.

    Returns:
        str: Fully qualified target Iceberg table name (e.g. 'lakehouse.db.othermarketinformation_r3').

    Raises:
        ValueError: If the provided df_schema is empty.
    """
    table_name = f"{_LAKEHOUSE_DB}.{fms_name.lower()}"

    # Check database catalog registry metadata
    if spark.catalog.tableExists(table_name):
        logger.debug("Iceberg table '%s' already exists in the catalog.", table_name)
        return table_name

    if not df_schema.fields:
        raise ValueError(
            f"Cannot create Iceberg table '{table_name}' with an empty DataFrame schema definition."
        )

    logger.info(
        "Target table '%s' is missing. Compiling DDL configurations...", table_name
    )

    # 1. Fetch Parquet codec properties from SSOT configurations
    parquet_config = get_lakehouse_parquet_codec_config()
    override = parquet_config.publication_overrides.get(fms_name)
    write_props = override or parquet_config.write_properties

    codec = write_props.compression_codec
    level = write_props.compression_level
    target_size_bytes = write_props.target_parquet_size_bytes

    # 2. Generate column definitions from df_schema fields
    cols_ddl_list = []
    for field in df_schema.fields:
        type_name = field.dataType.simpleString()
        nullable_str = "NOT NULL" if not field.nullable else ""
        cols_ddl_list.append(f"`{field.name}` {type_name} {nullable_str}".strip())

    cols_ddl = ", ".join(cols_ddl_list)

    # 3. Format Apache Iceberg specific metadata table properties
    tbl_properties = f"""
        'write.parquet.compression-codec' = '{codec}',
        'write.parquet.compression-level' = '{level}',
        'write.target-file-size-bytes' = '{target_size_bytes}',
        'write.format.default' = 'parquet'
    """

    create_ddl = f"""
        CREATE TABLE {table_name} (
            {cols_ddl}
        )
        USING iceberg
        TBLPROPERTIES ({tbl_properties})
    """

    logger.debug("Executing Spark SQL command: %s", create_ddl)
    spark.sql(create_ddl)
    logger.info("Successfully created new Iceberg table: %s", table_name)

    return table_name
