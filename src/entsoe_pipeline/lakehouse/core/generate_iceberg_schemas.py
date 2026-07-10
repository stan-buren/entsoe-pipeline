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

"""Schema registry generator job for the ENTSO-E Iceberg Lakehouse.

This job coordinates the generation of the target Iceberg schemas registry.
It initializes a Spark session, delegates S3 metadata extraction and schema
inference to core libraries, and persists the generated schemas.
"""

from __future__ import annotations

import logging

from sqlalchemy import create_engine, select

from entsoe_pipeline import get_buckets_config, setup_logging
from entsoe_pipeline.config.paths import (
    ISEBERG_SCHEMAS_REGISTRY_JSON,
    SCHEMA_OVERRIDES_YML,
)
from entsoe_pipeline.db import build_metadata, get_db_url
from entsoe_pipeline.logger.json_observability import save_json_with_observability
from entsoe_pipeline.spark.core import run_schema_generation
from entsoe_pipeline.spark.spark_builder import build_spark_session

logger = logging.getLogger("entsoe_pipeline.lakehouse.generate_iceberg_schemas")


def generate_iceberg_schemas_registry() -> None:
    """Infers schemas from landing zone samples and generates Iceberg registry."""
    setup_logging()
    logger.info("=== STARTING ICEBERG SCHEMA REGISTRY GENERATOR ===")

    # 1. Initialize Spark session
    logger.info("Initializing Spark session for schema inference...")
    spark = build_spark_session("Schema_Registry_Generator")
    landing_bucket = get_buckets_config().s3_landing_bucket

    logger.info("Querying landing files registry from database...")
    engine = create_engine(get_db_url())
    db_metadata = build_metadata()
    landing_files_registry = db_metadata.tables["landing_files_registry"]

    with engine.connect() as conn:
        stmt = select(landing_files_registry.c.s3_key)
        rows = conn.execute(stmt).fetchall()
    s3_keys = [row[0] for row in rows]

    # 2. Delegate execution to core schema generator
    registry_output = run_schema_generation(
        spark=spark,
        landing_bucket=landing_bucket,
        s3_keys=s3_keys,
        schemas_registry_path=ISEBERG_SCHEMAS_REGISTRY_JSON,
        overrides_path=SCHEMA_OVERRIDES_YML,
    )

    if not registry_output:
        logger.warning("No schemas generated. Registry remains unchanged.")
        return

    # 3. Save JSON schemas registry with automated warnings
    save_json_with_observability(
        ISEBERG_SCHEMAS_REGISTRY_JSON, registry_output, sort_keys=True
    )
    logger.info("=== SCHEMA REGISTRY GENERATION COMPLETED SUCCESSFULLY ===")


def main() -> None:
    """Main registry generator job entry point."""
    generate_iceberg_schemas_registry()


if __name__ == "__main__":
    main()
