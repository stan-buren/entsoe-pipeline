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

"""Module to build the landing bucket schema contract from the database fms_folders table.

This script parses the compiled FMS directory layout from the PostgreSQL catalog and
populates the expected directory paths registry in the 'landing_folders_schema' table
for both Integration/Test (iop) and Production (prod) environments.
"""

from __future__ import annotations

import logging

from sqlalchemy import create_engine, select

from entsoe_pipeline.db import build_metadata, get_db_url

logger = logging.getLogger(
    "entsoe_pipeline.fms_metadata.ingestion.landing_bucket_schema"
)


def build_landing_bucket_schema() -> None:
    """Builds and saves the landing bucket directory schema contract to database.

    Reads the folder pathways registered in the database table 'fms_folders',
    formats them into S3 directory prefixes, and saves them to the
    'landing_folders_schema' table.
    """
    logger.info("=== STARTING LANDING BUCKET SCHEMA GENERATION ===")

    engine = create_engine(get_db_url())
    db_metadata = build_metadata()
    fms_folders = db_metadata.tables["fms_folders"]
    landing_folders_schema = db_metadata.tables["landing_folders_schema"]

    with engine.connect() as conn:
        stmt = select(
            fms_folders.c.environment,
            fms_folders.c.domain,
            fms_folders.c.folder_path,
        )
        rows = conn.execute(stmt).fetchall()

    folders_to_insert = []
    for env, domain, folder_path in rows:
        parts = folder_path.strip("/").split("/")
        if len(parts) >= 2:
            root_dir = parts[0]
            folder_name = parts[1]
            s3_path = f"{env.lower()}/{root_dir}/{domain}/{folder_name}"
            folders_to_insert.append(
                {
                    "s3_folder_path": s3_path,
                    "environment": env.lower(),
                    "domain": domain,
                    "folder_name": folder_name,
                }
            )

    if not folders_to_insert:
        logger.warning(
            "No folders found in database table 'fms_folders' to build landing schema."
        )
        return

    # Deduplicate by s3_folder_path just in case
    unique_folders = {x["s3_folder_path"]: x for x in folders_to_insert}

    with engine.begin() as conn:
        # Clear out previous records to avoid orphans, then insert fresh schemas
        conn.execute(landing_folders_schema.delete())
        conn.execute(landing_folders_schema.insert(), list(unique_folders.values()))

    logger.info(
        "Successfully persisted %d folder schemas to database.",
        len(unique_folders),
    )
    logger.info("=== LANDING BUCKET SCHEMA GENERATION COMPLETED ===")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    build_landing_bucket_schema()
