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

"""Core Iceberg schema registry generator module."""

from __future__ import annotations

import json
import logging
import re

from pathlib import Path
from typing import Any

import yaml

from pyspark.sql.types import (
    DataType,
    DecimalType,
    DoubleType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
    _parse_datatype_string,
)

from entsoe_pipeline import get_fms_schemas_config
from entsoe_pipeline.logger import EntsoeConfigurationError
from entsoe_pipeline.spark.entsoe_fms_schemas_mapping import build_spark_schema_from_fms

logger = logging.getLogger("entsoe_pipeline.spark.core.iseberg_schema_generator")

TECHNICAL_ENDPOINTS = {
    "Export_log_r3.csv",
    "Export_oce_log_r3.csv",
}


def to_snake_case(name: str) -> str:
    """Standardizes raw CSV headers to clean lower_snake_case.

    Args:
        name: The raw column name from the CSV file.

    Returns:
        str: The sanitized column name.
    """
    # 1. Strip unit descriptors and UTC markers
    clean = re.sub(r"\(UTC\)|\[MW\]|\[EUR/MWh\]|\[EUR/MW\]|\[%\]", "", name).strip()
    # 2. Split CamelCase words with underscores
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", clean)
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
    # 3. Replace spaces, hyphens, and dots with underscores
    s3 = re.sub(r"[\s\-.]+", "_", s2)
    # 4. Standardize names
    return s3.lower().strip("_")


def parse_type_string(type_str: str) -> DataType:
    """Parses a type string (e.g. 'decimal(18, 4)', 'integer') to a PySpark DataType."""
    type_str = type_str.lower().strip()
    if type_str == "string":
        return StringType()
    if type_str in ("integer", "int"):
        return IntegerType()
    if type_str == "long":
        return LongType()
    if type_str == "double":
        return DoubleType()
    if type_str == "timestamp":
        return TimestampType()
    if type_str.startswith("decimal"):
        match = re.match(r"decimal\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)", type_str)
        if match:
            precision = int(match.group(1))
            scale = int(match.group(2))
            return DecimalType(precision, scale)
    return _parse_datatype_string(type_str)


def run_schema_generation(
    spark: Any,
    landing_bucket: str,
    s3_keys: list[str],
    schemas_registry_path: Path,
    overrides_path: Path | None = None,
) -> dict[str, Any]:
    """Infers schemas from configuration templates and S3, then saves them to registry.

    For registered endpoints, builds schema from entsoe_fms_schemas.yml.
    For technical files, falls back to Spark's auto-inference.

    Args:
        spark: The active Spark session.
        landing_bucket: The name of the S3 landing bucket.
        s3_keys: The list of S3 CSV keys to use for fallback schema inference.
        schemas_registry_path: Path to the target schemas registry JSON file.
        overrides_path: Path to the schema_overrides.yml configuration file.
    """
    # 1. Load FMS schemas configurations
    logger.info("Loading FMS schemas specifications...")
    fms_schemas_config = get_fms_schemas_config()
    fms_publications = fms_schemas_config.publications

    # Map of domain to endpoints found in registry S3 keys
    samples_to_process: dict[str, dict[str, str]] = {}  # {domain: {endpoint: s3_key}}
    for s3_key in s3_keys:
        parts = s3_key.split("/")
        if len(parts) < 4 or not s3_key.endswith(".csv"):
            continue

        domain = parts[2]
        endpoint = parts[3]

        if domain not in samples_to_process:
            samples_to_process[domain] = {}

        if endpoint not in samples_to_process[domain]:
            samples_to_process[domain][endpoint] = s3_key

    # 2. Load existing target registry if it exists, to support incremental updates
    registry: dict[str, Any] = {}
    if schemas_registry_path.exists():
        try:
            with schemas_registry_path.open(encoding="utf-8") as f:
                registry = json.load(f)
            logger.info(
                "Loaded %d existing schema entries from registry.", len(registry)
            )
        except Exception as e:
            logger.warning("Could not read existing registry, generating fresh: %s", e)

    # 3. Load custom schema overrides if available
    overrides: dict[str, Any] = {}
    if overrides_path and overrides_path.exists():
        try:
            with overrides_path.open(encoding="utf-8") as f:
                overrides = yaml.safe_load(f) or {}
            logger.info("Loaded schema overrides config from %s", overrides_path)
        except Exception as e:
            logger.warning("Could not load schema overrides: %s", e)

    global_overrides = overrides.get("global", {})
    endpoint_overrides = overrides.get("endpoints", {})

    # Process each sample file and infer schema
    for domain, endpoints in samples_to_process.items():
        logger.info("Processing domain: %s", domain)
        for endpoint, s3_key in endpoints.items():
            if endpoint in TECHNICAL_ENDPOINTS:
                # Technical logs fallback to Spark auto-inference
                s3_path = f"s3a://{landing_bucket}/{s3_key}"
                logger.info(
                    "  Inferring schema for technical endpoint '%s' using sample: %s",
                    endpoint,
                    s3_key,
                )

                try:
                    # Read CSV using Spark with header and inferSchema enabled
                    sample_df = (
                        spark.read.option("header", "true")
                        .option("delimiter", "\t")
                        .option("inferSchema", "true")
                        .csv(s3_path)
                        .limit(100)
                    )

                    # Sanitize column names and inject overrides
                    cleaned_fields = []
                    for field in sample_df.schema.fields:
                        clean_name = to_snake_case(field.name)
                        field_type = field.dataType

                        # Check global overrides
                        for pattern, override_type_str in global_overrides.items():
                            match = False
                            if pattern.startswith("*") and pattern.endswith("*"):
                                match = pattern[1:-1] in clean_name
                            elif pattern.startswith("*"):
                                match = clean_name.endswith(pattern[1:])
                            elif pattern.endswith("*"):
                                match = clean_name.startswith(pattern[:-1])
                            else:
                                match = clean_name == pattern

                            if match:
                                try:
                                    field_type = parse_type_string(override_type_str)
                                except Exception as e:
                                    logger.warning(
                                        "Could not parse global override type '%s' for pattern '%s': %s",
                                        override_type_str,
                                        pattern,
                                        e,
                                    )
                                break

                        # Check endpoint overrides
                        if (
                            endpoint in endpoint_overrides
                            and clean_name in endpoint_overrides[endpoint]
                        ):
                            override_type_str = endpoint_overrides[endpoint][clean_name]
                            try:
                                field_type = parse_type_string(override_type_str)
                            except Exception as e:
                                logger.warning(
                                    "Could not parse endpoint override type '%s' for %s.%s: %s",
                                    override_type_str,
                                    endpoint,
                                    clean_name,
                                    e,
                                )

                        meta = dict(field.metadata) if field.metadata else {}
                        meta["source_csv_column"] = field.name
                        cleaned_fields.append(
                            StructField(
                                name=clean_name,
                                dataType=field_type,
                                nullable=field.nullable,
                                metadata=meta,
                            )
                        )
                    cleaned_schema = StructType(cleaned_fields)
                    registry[endpoint] = cleaned_schema.jsonValue()
                    logger.info(
                        "  Successfully registered schema for technical endpoint '%s'.",
                        endpoint,
                    )

                except Exception as e:
                    logger.exception(
                        "  Failed to infer schema for technical endpoint %s: %s",
                        endpoint,
                        e,
                    )
            else:
                # Data publication - must exist in config schemas SSOT
                logger.info(
                    "  Building schema for endpoint '%s' using entsoe_fms_schemas.yml config",
                    endpoint,
                )
                if endpoint not in fms_publications:
                    raise EntsoeConfigurationError(
                        f"Endpoint '{endpoint}' was not found in entsoe_fms_schemas.yml. "
                        f"Please add it to the schema registry configurations."
                    )

                pub_schema = fms_publications[endpoint]
                spark_schema = build_spark_schema_from_fms(pub_schema)
                registry[endpoint] = spark_schema.jsonValue()
                logger.info(
                    "  Successfully registered schema for publication '%s' from configuration.",
                    endpoint,
                )

    return registry
