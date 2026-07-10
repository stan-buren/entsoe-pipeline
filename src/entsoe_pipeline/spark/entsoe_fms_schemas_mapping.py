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

"""ENTSO-E FMS schemas mapping logic to PySpark StructType."""

from __future__ import annotations

import re

from pyspark.sql.types import (
    BooleanType,
    DataType,
    DecimalType,
    DoubleType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

from entsoe_pipeline.config.core.entsoe_fms_schemas import FmsPublicationSchema


def parse_fms_type_to_spark(type_str: str) -> DataType:
    """Parses FMS schema datatype string into PySpark DataType class.

    Args:
        type_str: Datatype string from configuration (e.g. 'decimal(18,4)', 'timestamp').

    Returns:
        DataType: Matching PySpark datatype object.
    """
    type_str = type_str.lower().strip()

    if type_str == "string":
        return StringType()
    if type_str == "boolean":
        return BooleanType()
    if type_str == "timestamp":
        return TimestampType()
    if type_str in ("integer", "int"):
        return IntegerType()
    if type_str == "long":
        return LongType()
    if type_str == "double":
        return DoubleType()

    if type_str.startswith("decimal"):
        match = re.match(r"decimal\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)", type_str)
        if match:
            precision = int(match.group(1))
            scale = int(match.group(2))
            return DecimalType(precision, scale)

    # Fallback to StringType for safety, logged as warning
    return StringType()


def build_spark_schema_from_fms(publication_schema: FmsPublicationSchema) -> StructType:
    """Builds a PySpark StructType schema from FMS publication schema.

    Args:
        publication_schema: The loaded publication schema metadata from entsoe_fms_schemas.yml.

    Returns:
        StructType: The generated PySpark schema.
    """
    fields = []
    for col in publication_schema.columns:
        spark_type = parse_fms_type_to_spark(col.type)
        # Store raw source metadata lineage
        meta = {
            "source_csv_column": col.csv_name,
        }
        if col.description:
            meta["description"] = col.description

        fields.append(
            StructField(
                name=col.db_name,
                dataType=spark_type,
                nullable=not col.required,
                metadata=meta,
            )
        )
    return StructType(fields)
