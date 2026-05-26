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

import os

from pyspark.sql import SparkSession

from entsoe_pipeline import get_ports_config, get_region_config


def build_spark_session(app_name: str = "ENTSOE_Lakehouse") -> SparkSession:
    """Creates and configures a SparkSession for the ENTSOE Lakehouse.

    This builder configures the Spark session with Apache Iceberg extensions,
    connects to the S3-compatible gateway, and registers the Iceberg REST catalog.
    It resolves ports dynamically from the loaded active YAML configuration.

    Args:
        app_name: The name of the Spark application. Defaults to
          "ENTSOE_Lakehouse".

    Returns:
        An active SparkSession instance configured for the lakehouse.
    """
    # Load dynamic configurations for ports
    ports = get_ports_config()
    s3_endpoint = f"http://localhost:{ports.s3_compatible}"
    catalog_uri = f"http://localhost:{ports.iceberg_catalog}"

    # Load dynamic configuration for AWS region
    region = get_region_config()
    aws_region = region.aws_region

    # Load AWS credentials from environment variables populated via .env
    aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")

    return (
        SparkSession.builder.appName(app_name)
        .config(
            "spark.jars.packages",
            "org.apache.iceberg:iceberg-spark-runtime-4.1_2.13:1.11.0,"
            "org.apache.iceberg:iceberg-aws-bundle:1.11.0,"
            "org.apache.hadoop:hadoop-aws:3.4.2",
        )
        .config(
            "spark.sql.extensions",
            "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
        )
        # 1. REST Catalog configuration pointing to Iceberg Catalog
        .config("spark.sql.catalog.lakehouse", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.lakehouse.type", "rest")
        .config("spark.sql.catalog.lakehouse.uri", catalog_uri)
        .config("spark.sql.catalog.lakehouse.warehouse", "s3://lakehouse/")
        # 2. Iceberg S3 FileIO engine configuration for direct S3 writes
        .config(
            "spark.sql.catalog.lakehouse.io-impl", "org.apache.iceberg.aws.s3.S3FileIO"
        )
        .config("spark.sql.catalog.lakehouse.s3.endpoint", s3_endpoint)
        .config("spark.sql.catalog.lakehouse.s3.path-style-access", "true")
        .config("spark.sql.catalog.lakehouse.s3.access-key-id", aws_access_key)
        .config("spark.sql.catalog.lakehouse.s3.secret-access-key", aws_secret_key)
        .config("spark.sql.catalog.lakehouse.s3.region", aws_region)
        .config("spark.sql.catalog.lakehouse.client.region", aws_region)
        # 3. Hadoop S3A client configuration for raw reads (e.g., CSV imports)
        .config("spark.hadoop.fs.s3a.endpoint", s3_endpoint)
        .config("spark.hadoop.fs.s3a.access.key", aws_access_key)
        .config("spark.hadoop.fs.s3a.secret.key", aws_secret_key)
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.endpoint.region", aws_region)
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config(
            "spark.hadoop.fs.s3a.aws.credentials.provider",
            "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider",
        )
        .getOrCreate()
    )
