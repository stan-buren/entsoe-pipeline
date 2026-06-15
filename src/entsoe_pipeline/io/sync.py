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
    XXHASH_REGISTRY_JSON,
    get_active_domains_config,
    get_config,
    get_landing_bucket_schema,
)
from entsoe_pipeline.api.xxhash import calculate_idempotency_hash
from entsoe_pipeline.io.core import (
    check_idempotency,
    extract_active_folders,
    load_xxhash_registry,
    resolve_target_mappings,
    save_xxhash_registry,
    select_most_recent_csv,
    verify_free_disk_space,
)
from entsoe_pipeline.io.fms import download_fms_file, get_fms_client
from entsoe_pipeline.io.s3 import upload_file_to_s3
from entsoe_pipeline.lakehouse.core.s3_tree_builder import get_s3_client

logger = logging.getLogger("entsoe_pipeline.io.sync")


def sync_active_domains(env_name: str) -> dict[str, Any]:
    """Synchronizes active datasets from the remote ENTSO-E FMS to S3 storage.

    For each active folder:
      - Resolves the schema path matching the active folder.
      - Lists remote files, filters and selects the most recent CSV.
      - Checks local disk safety.
      - Checks if the file is already synced.
      - Downloads the file and uploads it to S3.

    Args:
        env_name: The target environment ('IOP' or 'PROD').

    Returns:
        dict[str, Any]: Metrics of the sync run.
    """
    logger.info("=== STARTING SYNC RUN FOR ENVIRONMENT: %s ===", env_name)

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

    xxhash_registry = load_xxhash_registry(XXHASH_REGISTRY_JSON)
    metrics = {"processed": 0, "downloaded": 0, "skipped": 0, "errors": 0}

    for mapping in target_mappings:
        try:
            # 3. Select the single most recent file
            file_meta = select_most_recent_csv(fms_client, mapping)
            if not file_meta:
                metrics["skipped"] += 1
                continue

            filename = file_meta["name"]
            size_bytes = file_meta.get("originalSize", 0)
            last_updated = file_meta.get("lastUpdatedTimestamp", "")
            remote_folder = file_meta["remote_folder"]
            schema_path = mapping["schema_path"]
            top_level = mapping["top_level_folder"]

            logger.info(
                "Selected most recent CSV file: %s (size: %d bytes, updated: %s)",
                filename,
                size_bytes,
                last_updated,
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
                registry=xxhash_registry,
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

            # Record in registry and persist
            xxhash_registry[s3_key] = expected_hash
            save_xxhash_registry(xxhash_registry, XXHASH_REGISTRY_JSON)

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
