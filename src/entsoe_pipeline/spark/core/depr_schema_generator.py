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

"""Core schema generator module for the ENTSO-E Spark pipeline."""

from __future__ import annotations

import logging
import re

from pathlib import Path
from typing import Any

logger = logging.getLogger("entsoe_pipeline.spark.core.schema_generator")


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


def generate_python_schema_code(
    endpoint_name: str,
    schema_fields: list[tuple[str, str]],
) -> str:
    """Formats StructField definitions into valid PySpark StructType Python code.

    Args:
        endpoint_name: Name of the endpoint (e.g., 'ActualTotalLoad_6.1.A_r3').
        schema_fields: List of tuples mapping column name to PySpark type class.

    Returns:
        str: Python code block defining the schema.
    """
    schema_const = f"{to_snake_case(endpoint_name).upper()}_SCHEMA"

    lines = [
        f"{schema_const} = StructType([",
    ]
    for col_name, type_class in schema_fields:
        clean_name = to_snake_case(col_name)
        lines.append(f'    StructField("{clean_name}", {type_class}(), True),')
    lines.append("])")

    return "\n".join(lines)


def run_schema_generation(
    samples_to_process: dict[str, dict[str, str]],
    spark: Any,
    landing_bucket: str,
    schemas_dir: Path,
) -> None:
    """Infers schemas from sample files in S3 and writes them to Python files.

    Args:
        samples_to_process: Dictionary of {domain: {endpoint: s3_key}}.
        spark: The active Spark session.
        landing_bucket: The name of the S3 landing bucket.
        schemas_dir: Destination path for generated schema files.
    """
    schemas_dir.mkdir(parents=True, exist_ok=True)
    generated_registry_entries: list[
        tuple[str, str, str]
    ] = []  # [(endpoint, domain_module, schema_const)]

    # Infer types and write domain-level schema modules
    for domain, endpoints in samples_to_process.items():
        domain_module = to_snake_case(domain)
        module_path = schemas_dir / f"{domain_module}.py"

        logger.info("Processing domain: %s -> %s.py", domain, domain_module)

        module_code_chunks = [
            f'"""{domain} domain PySpark schemas for Iceberg tables."""\n',
            "from pyspark.sql.types import (",
            "    DoubleType,",
            "    IntegerType,",
            "    LongType,",
            "    StringType,",
            "    StructField,",
            "    StructType,",
            "    TimestampType,",
            ")\n\n",
        ]

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

                # Get PySpark inferred fields
                fields = []
                for field in sample_df.schema.fields:
                    type_class = field.dataType.__class__.__name__
                    fields.append((field.name, type_class))

                # Generate code string
                code = generate_python_schema_code(endpoint, fields)
                module_code_chunks.append(code + "\n\n")

                schema_const = f"{to_snake_case(endpoint).upper()}_SCHEMA"
                generated_registry_entries.append(
                    (endpoint, domain_module, schema_const)
                )

            except Exception as e:
                logger.exception(
                    "  Failed to infer schema for endpoint %s: %s", endpoint, e
                )

        # Write domain schemas Python file
        module_path.write_text("\n".join(module_code_chunks), encoding="utf-8")
        logger.info("Saved domain schemas module: %s", module_path)

    # Centralized registry __init__.py
    init_path = schemas_dir / "__init__.py"
    init_lines = [
        '"""Centralized registry for ENTSO-E PySpark schemas."""\n',
        "from pyspark.sql.types import StructType\n",
    ]

    # Add module imports
    for domain_module in sorted({entry[1] for entry in generated_registry_entries}):
        schema_constants = [
            entry[2]
            for entry in generated_registry_entries
            if entry[1] == domain_module
        ]
        imports_str = ", ".join(sorted(schema_constants))
        init_lines.append(
            f"from entsoe_pipeline.lakehouse.schemas.{domain_module} import ({imports_str})"
        )

    init_lines.append("\n\n_SCHEMAS_REGISTRY: dict[str, StructType] = {")
    for endpoint, _, schema_const in sorted(generated_registry_entries):
        init_lines.append(f'    "{endpoint}": {schema_const},')
    init_lines.append("}\n")

    init_lines.append("""
def get_schema(endpoint_name: str) -> StructType:
    \"\"\"Retrieves the registered StructType schema for a given endpoint folder name.

    Args:
        endpoint_name: The raw endpoint directory name (e.g. 'ActualTotalLoad_6.1.A_r3').

    Returns:
        StructType: The registered PySpark schema.

    Raises:
        KeyError: If the endpoint is not registered.
    \"\"\"
    if endpoint_name not in _SCHEMAS_REGISTRY:
        raise KeyError(f"No schema registered for endpoint: '{endpoint_name}'")
    return _SCHEMAS_REGISTRY[endpoint_name]
""")

    init_path.write_text("\n".join(init_lines), encoding="utf-8")
    logger.info("Saved centralized registry: %s", init_path)
