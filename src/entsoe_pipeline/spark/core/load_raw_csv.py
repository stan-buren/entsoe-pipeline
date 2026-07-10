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

"""Low-level Spark computational utilities for reading and parsing landing CSVs."""

from __future__ import annotations

import logging

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, to_timestamp
from pyspark.sql.types import StructType, TimestampType

logger = logging.getLogger("entsoe_pipeline.spark.core.load_raw_csv")


def load_raw_csv_with_schema(
    spark: SparkSession,
    paths: list[str],
    spark_schema: StructType,
    date_format: str | None = None,
) -> DataFrame:
    """Reads raw CSV files from S3 using Spark and enforces target data schema.

    Maps CSV headers dynamically to lower_snake_case column names and casts
    types according to the target StructType. Formats timestamps safely.

    Args:
        spark: The active SparkSession instance.
        paths: List of absolute S3A paths to read (e.g. s3a://landing-zone/...).
        spark_schema: Target StructType containing column names and target types.
        date_format: Expected timestamp format pattern (e.g., 'dd/MM/yyyy HH:mm').

    Returns:
        DataFrame: Converted Spark DataFrame matching the target schema.
    """
    logger.info("Reading %d CSV path(s) into Spark DataFrame...", len(paths))

    # Read CSV first as string types for headers mapping, then cast explicitly
    # This prevents parser failures on mismatched formats (e.g. custom date formats)
    csv_reader = spark.read.format("csv").option("header", "true").option("sep", "\t")

    df = csv_reader.load(paths)

    # 1. Map columns from CSV header names (source_csv_column) to target db_names
    # E.g. rename 'StartOutage(UTC)' to 'start_outage_utc'
    select_exprs = []
    for field in spark_schema.fields:
        csv_col_name = field.metadata.get("source_csv_column")
        if not csv_col_name:
            # Fallback to column name if metadata is missing
            csv_col_name = field.name

        # Ensure the column exists in the read CSV schema
        if csv_col_name in df.columns:
            expr = col(csv_col_name).alias(field.name)
            select_exprs.append(expr)
        else:
            logger.warning(
                "Source CSV column '%s' not found in loaded CSV file(s). Ignored.",
                csv_col_name,
            )

    df_mapped = df.select(*select_exprs)

    # 2. Perform explicit type casting according to Spark target schema
    for field in spark_schema.fields:
        col_name = field.name
        target_type = field.dataType

        if isinstance(target_type, TimestampType) and date_format:
            # Parse custom dates safely using to_timestamp
            df_mapped = df_mapped.withColumn(
                col_name, to_timestamp(col(col_name), date_format)
            )
        else:
            # Cast standard types (e.g., String, Double, Decimal, Integer)
            df_mapped = df_mapped.withColumn(col_name, col(col_name).cast(target_type))

    return df_mapped
