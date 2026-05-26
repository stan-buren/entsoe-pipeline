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

"""Ingestion module for processing ENTSO-E FMS CSV files.

This module provides functions to read ENTSO-E FMS CSV files either from
simulated local directories or from the actual FMS API client, clean and
normalize the schema into standard database formats, and write the datasets
into S3 raw storage and structured Apache Iceberg bronze tables. It implements
a robust two-tier idempotency workflow to ensure data integration reliability.

Typical usage example:

  ingest_folder("EnergyPrices_12.1.D_r3", force_reload=False)
"""

import logging

from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from pyspark.sql import SparkSession

from entsoe_pipeline import (
    MANUAL_DATA_DIR,
    get_buckets_config,
    get_config,
)
from entsoe_pipeline.spark.spark_builder import build_spark_session
from entsoe_pipeline.vendor_patches.entsoe_py import ConfigurableEntsoeFileClient

logger = logging.getLogger("ENTSOE_Ingestion")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def check_raw_file_exists(spark: SparkSession, s3_path: str) -> bool:
    """Verifies whether a raw file exists on S3 storage.

    Uses the Hadoop FileSystem API directly from PySpark to check path
    existence via metadata without loading file content.

    Args:
        spark: The active SparkSession instance.
        s3_path: The absolute S3 storage path to check.

    Returns:
        True if the file exists on S3; False otherwise.
    """
    try:
        conf = spark.sparkContext._jsc.hadoopConfiguration()
        path_class = spark._jvm.org.apache.hadoop.fs.Path(s3_path)
        fs = path_class.getFileSystem(conf)
        return fs.exists(path_class)
    except Exception as e:
        logger.warning("Failed to verify path existence via Hadoop API: %s", e)
        return False


def clean_columns(df_columns: Sequence[str]) -> list[str]:
    """Cleans and normalizes header names into standard lower_snake_case.

    Maps bracket formats and special symbols like 'Price[Currency/MWh]' into
    SQL-friendly 'price_currency_mwh'.

    Args:
        df_columns: A list of raw column headers.

    Returns:
        A list of cleaned lower_snake_case column names.
    """
    clean_cols = []
    for col in df_columns:
        cleaned = (
            col.replace("[", "_")
            .replace("]", "")
            .replace("/", "_")
            .replace("(", "_")
            .replace(")", "")
            .replace(" ", "_")
            .lower()
        )
        clean_cols.append(cleaned)
    return clean_cols


def ingest_folder(folder_name: str, force_reload: bool = False) -> None:
    """Ingests ENTSO-E CSV datasets into raw S3 storage and Iceberg tables.

    Executes a two-tier idempotency workflow:
      1. Tier 1: Checks if the target Parquet raw file exists on S3. If yes and
         force_reload is False, the processing of this file is skipped.
      2. Tier 2: Deletes existing records matching the current source file from
         the target Iceberg table before appending the fresh batch.

    Args:
        folder_name: The name of the FMS or simulated folder to read from.
        force_reload: A boolean indicating whether to bypass the Tier 1 check
          and fully re-process files.
    """
    buckets_config = get_buckets_config()

    s3_bucket = buckets_config.s3_bucket

    config = get_config()

    spark = build_spark_session("FMS_Batch_Ingestion")

    try:
        spark.sql("CREATE DATABASE IF NOT EXISTS lakehouse.bronze")
        iceberg_table = "lakehouse.bronze.energy_prices"

        # Discovers local files for simulated execution before falling back to
        # the active network client.
        local_files = list(MANUAL_DATA_DIR.glob("*.csv"))

        if local_files:
            logger.info(
                "Discovered %d local CSV files in manual-added-data directory.",
                len(local_files),
            )
            files_to_process = {f.name: f for f in local_files}
        else:
            logger.info("No local CSV files found. Connecting to ENTSO-E FMS.")
            client = ConfigurableEntsoeFileClient(
                username=config.env_config.email,
                pwd=config.env_config.password,
                base_url=config.env_config.base_url,
                token_url=config.env_config.token_url,
            )
            remote_files = client.list_folder(folder_name)
            files_to_process = {name: name for name in sorted(remote_files.keys())}
            logger.info(
                "Found %d remote files in FMS directory '%s'.",
                len(files_to_process),
                folder_name,
            )

        for filename, file_ref in files_to_process.items():
            parquet_filename = filename.replace(".csv", ".parquet")

            raw_s3_path = f"s3a://{s3_bucket}/raw/{folder_name}/{parquet_filename}"

            logger.info("Processing file: %s", filename)

            # Validates Tier 1 idempotency to prevent redundant downloads.
            if not force_reload and check_raw_file_exists(spark, raw_s3_path):
                logger.info(
                    "Tier 1 Idempotency: Raw Parquet file exists. Skipping: %s",
                    raw_s3_path,
                )
                continue

            if isinstance(file_ref, Path):
                logger.info("Loading file locally from: %s", file_ref)
                df_pandas = pd.read_csv(file_ref, sep=";")
            else:
                logger.info("Downloading file '%s' from FMS.", filename)
                df_pandas = client.download_single_file(
                    folder=folder_name, filename=filename
                )

            logger.info("Downloaded DataFrame shape: %s", df_pandas.shape)

            df_pandas.columns = clean_columns(list(df_pandas.columns))
            df_pandas["_source_file"] = filename

            # Converts pandas object types to string to avoid spark type errors.
            for col in df_pandas.columns:
                if df_pandas[col].dtype == "object":
                    df_pandas[col] = df_pandas[col].astype(str)

            df_spark = spark.createDataFrame(df_pandas)

            logger.info("Writing clean raw copy to S3: %s", raw_s3_path)
            df_spark.write.mode("overwrite").parquet(raw_s3_path)

            # Validates Tier 2 idempotency to maintain database consistency.
            if spark.catalog.tableExists(iceberg_table):
                logger.info(
                    "Tier 2 Idempotency: Purging existing records for: %s",
                    filename,
                )
                spark.sql(
                    f"DELETE FROM {iceberg_table} WHERE _source_file = '{filename}'"  # noqa: S608
                )

            logger.info("Appending transactional records to: %s", iceberg_table)
            df_spark.write.format("iceberg").mode("append").saveAsTable(iceberg_table)
            logger.info("Successfully ingested and synchronized: %s", filename)

    finally:
        logger.info("Stopping active Spark session.")
        spark.stop()
