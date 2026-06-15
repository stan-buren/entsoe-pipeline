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

"""Low-level xxHash idempotency and sync registry operations."""

from __future__ import annotations

import json
import logging

from pathlib import Path

from entsoe_pipeline.io.core.s3_operations import s3_object_exists

logger = logging.getLogger("entsoe_pipeline.io.core.idempotency")


def load_xxhash_registry(registry_path: Path) -> dict[str, str]:
    """Loads the xxHash idempotency registry from the local disk.

    Args:
        registry_path: Path to the JSON registry file.

    Returns:
        dict[str, str]: Dictionary mapping S3 keys to xxHash hex digests.
    """
    if not registry_path.exists():
        return {}
    try:
        with registry_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Failed to load xxhash registry: %s. Starting fresh.", e)
        return {}


def save_xxhash_registry(registry: dict[str, str], registry_path: Path) -> None:
    """Saves the xxHash idempotency registry back to the local disk.

    Args:
        registry: The active registry dictionary.
        registry_path: Path to save the JSON registry file.
    """
    try:
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        with registry_path.open("w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)
    except Exception as e:
        logger.exception("Failed to save xxhash registry at %s: %s", registry_path, e)


def check_idempotency(
    s3_key: str,
    expected_hash: str,
    registry: dict[str, str],
    bucket_name: str,
    s3_client,
) -> bool:
    """Verifies if the file has already been synced using the registry and S3.

    Args:
        s3_key: Target object key in S3.
        expected_hash: Expected xxHash hex digest of the file metadata.
        registry: The loaded xxHash registry.
        bucket_name: Destination S3 bucket name.
        s3_client: The S3 client.

    Returns:
        bool: True if the file has already been synced, False otherwise.
    """
    return bool(
        registry.get(s3_key) == expected_hash
        and s3_object_exists(
            s3_key=s3_key, bucket_name=bucket_name, s3_client=s3_client
        )
    )
