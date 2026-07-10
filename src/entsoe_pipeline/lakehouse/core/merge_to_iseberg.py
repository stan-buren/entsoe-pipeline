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

"""Low-level Spark computational utilities for Iceberg table merge (upsert) queries."""

from __future__ import annotations

import logging
import uuid

from pyspark.sql import DataFrame, SparkSession

logger = logging.getLogger("entsoe_pipeline.lakehouse.core.merge_to_iseberg")


def merge_dataframe_into_table(
    spark: SparkSession,
    df: DataFrame,
    table_name: str,
    keys: list[str],
) -> None:
    """Executes an atomic SQL MERGE INTO (Upsert) operation against an Iceberg table.

    Registers the DataFrame as a temporary session view, builds the join query ON
    statement dynamically using the list of composite business keys, and runs the merge.
    Cleans up the temporary view in the finally block.

    Args:
        spark: The active SparkSession instance.
        df: The source Spark DataFrame to merge.
        table_name: Fully qualified target Iceberg table name (e.g. 'lakehouse.db.table').
        keys: List of composite primary key column names.

    Raises:
        ValueError: If keys list is empty.
    """
    if not keys:
        raise ValueError(
            f"Cannot run MERGE INTO on table '{table_name}' with an empty business keys list."
        )

    # 1. Create a session-unique temporary view for target DataFrame
    temp_view_name = f"src_merge_temp_{uuid.uuid4().hex[:8]}"
    df.createOrReplaceTempView(temp_view_name)

    # 2. Build ON join conditions: t.col = s.col
    join_conditions = [f"t.{col_name} = s.{col_name}" for col_name in keys]
    join_sql = " AND ".join(join_conditions)

    # 3. Dynamic MERGE INTO SQL
    merge_sql = f"""
        MERGE INTO {table_name} t
        USING {temp_view_name} s
        ON {join_sql}
        WHEN MATCHED THEN
            UPDATE SET *
        WHEN NOT MATCHED THEN
            INSERT *
    """

    logger.info(
        "Executing MERGE INTO on '%s' table using TempView '%s'...",
        table_name,
        temp_view_name,
    )
    logger.debug("SQL merge query statement: %s", merge_sql)

    try:
        spark.sql(merge_sql)
        logger.info("MERGE INTO transaction completed successfully.")
    finally:
        # Drop temporary view to clean up session registry namespace
        spark.catalog.dropTempView(temp_view_name)
