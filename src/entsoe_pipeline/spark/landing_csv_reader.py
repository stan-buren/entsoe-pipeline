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

"""High-level Spark business logic for reading landing zone CSV datasets."""

from __future__ import annotations

import logging
import re

from pyspark.sql import DataFrame, SparkSession

from entsoe_pipeline.config.config_loader import (
    get_buckets_config,
    get_fms_schemas_config,
)
from entsoe_pipeline.spark.core.load_raw_csv import load_raw_csv_with_schema
from entsoe_pipeline.spark.entsoe_fms_schemas_mapping import build_spark_schema_from_fms

logger = logging.getLogger("entsoe_pipeline.spark.landing_csv_reader")


def to_snake_case(name: str) -> str:
    """Sanitizes raw CSV column headers to lower_snake_case.

    Strips out unit descriptors, bracketed metrics (e.g. '[MW]'), and UTC markers.

    Args:
        name: Raw header name string from CSV file.

    Returns:
        str: Sanitized snake_case column identifier.
    """
    clean = re.sub(r"\(UTC\)|\[MW\]|\[EUR/MWh\]|\[EUR/MW\]|\[%\]", "", name).strip()
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", clean)
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
    s3 = re.sub(r"[\s\-.]+", "_", s2)
    return s3.lower().strip("_")


def read_landing_csv_dataset(
    spark: SparkSession,
    s3_keys: list[str],
    fms_name: str,
) -> DataFrame:
    """Reads CSV files for a specific schema contract and maps them to target schema.

    Resolves target database column types, formats date values, parses target schemas
    from centralized FMS definitions, and loads datasets using direct S3A endpoints.
    If the target publication schema is empty, triggers auto-inference fallback.

    Args:
        spark: The active SparkSession instance.
        s3_keys: List of S3 keys from the database pending load (e.g. ['iop/.../file.csv']).
        fms_name: Strict FMS contract schema name (e.g., 'ActualTotalLoad_6.1.A_r3').

    Returns:
        DataFrame: Fully mapped Spark DataFrame conforming to Iceberg schema rules.

    Raises:
        ValueError: If schema details for the specified contract are missing.
    """
    if not s3_keys:
        raise ValueError("Cannot read landing CSV dataset with an empty S3 keys list.")

    # 1. Fetch schema configuration for specified FMS contract
    schemas_cfg = get_fms_schemas_config()
    publication_schema = schemas_cfg.publications.get(fms_name)
    if not publication_schema:
        raise ValueError(
            f"FMS schema definition not found for schema contract: '{fms_name}'"
        )

    # 2. Form S3A storage endpoint URLs
    landing_bucket = get_buckets_config().s3_landing_bucket
    s3a_paths = [f"s3a://{landing_bucket}/{s3_key.lstrip('/')}" for s3_key in s3_keys]

    # 3. Dynamic Auto-Inference Fallback (ADR-010)
    # If the YAML contract does not specify column definitions, we run Spark auto-inference
    if not publication_schema.columns:
        logger.warning(
            "Auto-Inference Fallback (ADR-010): Empty columns registry found for contract '%s'. "
            "Triggering dynamic Spark schema auto-inference for %d file(s)...",
            fms_name,
            len(s3a_paths),
        )

        # Read raw CSV using tab separator and auto-detecting types
        df_raw = (
            spark.read.format("csv")
            .option("header", "true")
            .option("sep", "\t")
            .option("inferSchema", "true")
            .load(s3a_paths)
        )

        # Sanitize column headers to lower_snake_case for Iceberg compatibility
        for col_name in df_raw.columns:
            sanitized_name = to_snake_case(col_name)
            df_raw = df_raw.withColumnRenamed(col_name, sanitized_name)

        logger.info(
            "Successfully completed dynamic auto-inference. Resolved %d columns.",
            len(df_raw.columns),
        )
        return df_raw

    # 4. Strict Schema Path: construct StructType from YAML definition
    spark_schema = build_spark_schema_from_fms(publication_schema)

    # Detect custom date format from timestamp columns
    date_format: str | None = None
    for col_def in publication_schema.columns:
        if col_def.type.lower() == "timestamp" and getattr(col_def, "format", None):
            date_format = col_def.format
            break

    logger.info(
        "Initiating Spark load for schema contract '%s' (%d files, date format: %s)...",
        fms_name,
        len(s3a_paths),
        date_format,
    )

    # Delegate execution to low-level CSV loader
    df = load_raw_csv_with_schema(
        spark=spark,
        paths=s3a_paths,
        spark_schema=spark_schema,
        date_format=date_format,
    )

    logger.info("Successfully loaded CSV dataset into memory DataFrame.")
    return df
