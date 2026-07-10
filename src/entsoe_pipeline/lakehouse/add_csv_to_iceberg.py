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

"""High-level ingestion workflow to write dataframes into Apache Iceberg tables."""

from __future__ import annotations

import logging

from pyspark.sql import DataFrame, SparkSession

from entsoe_pipeline.config.config_loader import (
    get_fms_schemas_config,
    get_lakehouse_parquet_codec_config,
)
from entsoe_pipeline.lakehouse.core.get_domain_business_keys import (
    get_domain_business_keys,
)
from entsoe_pipeline.lakehouse.core.merge_to_iseberg import merge_dataframe_into_table
from entsoe_pipeline.lakehouse.iceberg_tables import ensure_iceberg_table_exists

logger = logging.getLogger("entsoe_pipeline.lakehouse.add_csv_to_iceberg")


def add_csv_to_iceberg_table(
    spark: SparkSession,
    df: DataFrame,
    fms_name: str,
    total_raw_size_bytes: int,
) -> str:
    """Orchestrates writing and merging Spark DataFrames into an Iceberg table.

    Validates target table presence (creating it dynamically on catalog registry if missing),
    scales partition counts through coalesce based on uncompressed input bytes,
    resolves composite business keys, and executes either merge or append operations.

    Args:
        spark: The active SparkSession instance.
        df: Mapped Spark DataFrame containing data to commit.
        fms_name: Strict FMS contract schema name (e.g. 'OtherMarketInformation_r3').
        total_raw_size_bytes: Size of uncompressed raw CSV source files.

    Returns:
        str: Fully qualified target Iceberg table name (e.g. 'lakehouse.db.table_name').

    Raises:
        ValueError: If schema specifications for the given contract are missing.
    """
    # 1. Ensure target Iceberg table exists in catalog using the current DataFrame schema
    table_name = ensure_iceberg_table_exists(spark, fms_name, df.schema)

    # 2. Retrieve schema configurations to resolve keys
    schemas_cfg = get_fms_schemas_config()
    publication_schema = schemas_cfg.publications.get(fms_name)

    # 3. Calculate partition size optimization (target target_parquet_size_bytes)
    parquet_config = get_lakehouse_parquet_codec_config()
    override = parquet_config.publication_overrides.get(fms_name)
    write_props = override or parquet_config.write_properties
    target_size_bytes = write_props.target_parquet_size_bytes

    # Uncompressed raw-to-parquet ratio is roughly 5x
    num_files = max(1, int(total_raw_size_bytes / (target_size_bytes * 5)))
    logger.info(
        "Ingesting CSV data into table '%s'. Raw size: %d MB. Target partitions count: %d",
        table_name,
        int(total_raw_size_bytes / (1024 * 1024)),
        num_files,
    )
    df_optimized = df.coalesce(num_files)

    # 4. Resolve composite primary keys using low-level core heuristics
    keys = []
    if publication_schema and publication_schema.columns:
        keys = get_domain_business_keys(publication_schema)

    # 5. Execute write operation: MERGE if keys exist, otherwise APPEND fallback
    if not keys:
        logger.warning(
            "Schema Incomplete / Legacy (ADR-010): No business primary keys resolved for '%s'. "
            "Appending records to table '%s' instead of merging.",
            fms_name,
            table_name,
        )
        df_optimized.write.format("iceberg").mode("append").save(table_name)
        logger.info("Successfully appended data to Iceberg table '%s'.", table_name)
    else:
        merge_dataframe_into_table(
            spark=spark,
            df=df_optimized,
            table_name=table_name,
            keys=keys,
        )

    return table_name
