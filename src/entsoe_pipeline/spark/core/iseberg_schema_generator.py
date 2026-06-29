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

logger = logging.getLogger("entsoe_pipeline.spark.core.iseberg_schema_generator")


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
    landing_registry_path: Path,
    schemas_registry_path: Path,
    overrides_path: Path | None = None,
) -> dict[str, Any]:
    """Infers schemas from S3 and writes them as JSON values to the registry.

    Args:
        spark: The active Spark session.
        landing_bucket: The name of the S3 landing bucket.
        landing_registry_path: Path to the landing registry JSON file.
        schemas_registry_path: Path to the target schemas registry JSON file.
        overrides_path: Path to the schema_overrides.yml configuration file.
    """
    # 1. Parse landing registry and select one sample file per domain and endpoint
    if not landing_registry_path.exists():
        logger.warning(
            "Landing registry not found at: %s. Cannot infer schemas.",
            landing_registry_path,
        )
        return {}

    with landing_registry_path.open(encoding="utf-8") as f:
        landing_registry = json.load(f)

    samples_to_process: dict[str, dict[str, str]] = {}  # {domain: {endpoint: s3_key}}
    for s3_key in landing_registry:
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
            s3_path = f"s3a://{landing_bucket}/{s3_key}"
            logger.info(
                "  Inferring schema for endpoint '%s' using sample: %s",
                endpoint,
                s3_key,
            )

            try:
                # Read CSV using Spark with header and inferSchema enabled
                # We limit the read to 100 rows to make it fast
                sample_df = (
                    spark.read.option("header", "true")
                    .option("delimiter", "\t")
                    .option("inferSchema", "true")
                    .csv(s3_path)
                    .limit(100)
                )

                # Sanitize column names to snake_case in the StructType schema and inject lineage/type overrides
                cleaned_fields = []
                for field in sample_df.schema.fields:
                    clean_name = to_snake_case(field.name)

                    # 1. Start with inferred type
                    field_type = field.dataType

                    # 2. Check global pattern overrides (prefix/suffix/exact match)
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

                    # 3. Check endpoint-specific overrides (highest priority)
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

                    # Copy existing metadata or initialize a new dict
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

                # Serialize schema to PySpark jsonValue dictionary representation
                registry[endpoint] = cleaned_schema.jsonValue()
                logger.info(
                    "  Successfully registered schema for endpoint '%s'.", endpoint
                )

            except Exception as e:
                logger.exception(
                    "  Failed to infer schema for endpoint %s: %s", endpoint, e
                )

    return registry
