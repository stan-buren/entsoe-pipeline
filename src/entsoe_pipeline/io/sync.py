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

"""ENTSO-E Data Ingestion Synchronization Engine."""

from __future__ import annotations

import logging

from typing import Any

from entsoe_pipeline import (
    MANUAL_DATA_DIR,
    get_active_domains_config,
    get_config,
    get_landing_bucket_schema,
)
from entsoe_pipeline.api.xxhash import calculate_idempotency_hash
from entsoe_pipeline.io.core import (
    check_idempotency,
    extract_active_folders,
    register_downloaded_file,
    resolve_target_mappings,
    select_files_to_sync,
    verify_free_disk_space,
)
from entsoe_pipeline.io.fms import download_fms_file, get_fms_client
from entsoe_pipeline.io.s3 import upload_file_to_s3
from entsoe_pipeline.lakehouse.core.s3_tree_builder import get_s3_client

logger = logging.getLogger("entsoe_pipeline.io.sync")


def sync_active_domains(env_name: str, run_id: str) -> dict[str, Any]:
    """Synchronizes active datasets from the remote ENTSO-E FMS to S3 storage.

    For each active folder:
      - Resolves the schema path matching the active folder.
      - Lists remote files, filters and selects the most recent CSV.
      - Checks local disk safety.
      - Checks if the file is already synced.
      - Downloads the file and uploads it to S3.

    Args:
        env_name: The target environment ('IOP' or 'PROD').
        run_id: The unique operational tracking ID of this execution.

    Returns:
        dict[str, Any]: Metrics of the sync run.
    """
    logger.info(
        "=== STARTING SYNC RUN FOR ENVIRONMENT: %s (Run ID: %s) ===", env_name, run_id
    )

    # 1. Parse active folders from checklist
    domains_config = get_active_domains_config()
    active_folders = extract_active_folders(env_name, domains_config)
    if not active_folders:
        logger.warning(
            "No settings found for environment '%s' in active config checklist.",
            env_name,
        )
        return {"processed": 0, "downloaded": 0, "skipped": 0, "errors": 0}

    # 2. Resolve full paths from schema contract
    schema_folders = get_landing_bucket_schema()
    target_mappings = resolve_target_mappings(env_name, active_folders, schema_folders)
    logger.info(
        "Resolved %d matched directory paths from schema contract.",
        len(target_mappings),
    )

    fms_client = get_fms_client(env_name)
    s3_client = get_s3_client()
    config = get_config()
    bucket_name = config.buckets.s3_landing_bucket

    metrics = {"processed": 0, "downloaded": 0, "skipped": 0, "errors": 0}

    for mapping in target_mappings:
        try:
            # 3. Select all files matching configuration checklist
            files_to_sync = select_files_to_sync(fms_client, mapping)
            for file_meta in files_to_sync:
                filename = file_meta["name"]
                size_bytes = file_meta.get("originalSize", 0)
                last_updated = file_meta.get("lastUpdatedTimestamp", "")
                remote_folder = file_meta["remote_folder"]
                schema_path = mapping["schema_path"]
                top_level = mapping["top_level_folder"]

                # Skip empty files without fileId
                file_id = file_meta.get("fileId", "")
                if not file_id:
                    logger.warning(
                        "Selected file '%s' has no fileId (empty). Skipping ingestion.",
                        filename,
                    )
                    metrics["skipped"] += 1
                    continue

                logger.info(
                    "Selected CSV file: %s (size: %d bytes, updated: %s, fileId: %s)",
                    filename,
                    size_bytes,
                    last_updated,
                    file_id,
                )

                # 4. Check local disk space safety margin
                verify_free_disk_space(MANUAL_DATA_DIR, size_bytes)

                # 5. Check xxHash idempotency
                expected_hash = calculate_idempotency_hash(
                    filename, size_bytes, last_updated
                )
                s3_key = f"{schema_path.strip('/')}/{filename}"

                is_already_synced = check_idempotency(
                    s3_key=s3_key,
                    expected_hash=expected_hash,
                    bucket_name=bucket_name,
                    s3_client=s3_client,
                )

                if is_already_synced:
                    logger.info(
                        "File '%s' with hash %s already synced. Skipping.",
                        s3_key,
                        expected_hash,
                    )
                    metrics["skipped"] += 1
                    continue

                # 6. Execute file transfer (download from FMS, upload to S3)
                logger.info("Transferring file '%s' from FMS to S3...", filename)
                csv_data = download_fms_file(
                    client=fms_client,
                    top_level_folder=top_level,
                    folder_path=remote_folder,
                    filename=filename,
                )

                # Write temporarily to local path before uploading
                local_tmp_path = MANUAL_DATA_DIR / f"tmp_{filename}"
                local_tmp_path.parent.mkdir(parents=True, exist_ok=True)
                local_tmp_path.write_bytes(csv_data)

                # Upload to S3
                upload_file_to_s3(local_path=local_tmp_path, s3_key=s3_key)

                # Cleanup temp file
                if local_tmp_path.exists():
                    local_tmp_path.unlink()

                # Record in registry and persist to database
                register_downloaded_file(
                    s3_key=s3_key,
                    file_name=filename,
                    file_id=file_id,
                    file_size_bytes=size_bytes,
                    last_updated_timestamp=last_updated,
                    xxhash=expected_hash,
                    run_id=run_id,
                )

                metrics["downloaded"] += 1
                metrics["processed"] += 1

        except Exception as e:
            logger.exception(
                "Failed to sync folder '%s' due to error: %s",
                mapping.get("active_folder"),
                e,
            )
            metrics["errors"] += 1

    logger.info("=== SYNC RUN COMPLETED. Summary: %s ===", metrics)
    return metrics
