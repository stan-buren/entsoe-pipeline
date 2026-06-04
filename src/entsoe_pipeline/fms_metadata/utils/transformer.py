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

"""Transformer module for ENTSO-E FMS Metadata schemas.

Responsible for formatting raw bytes, mapping remote FMS JSON catalog entries
into structured dictionaries, and compiling domain folder and environmental summaries.
"""

from __future__ import annotations

from typing import Any

from entsoe_pipeline.api import calculate_idempotency_hash
from entsoe_pipeline.fms_metadata.utils.overview_parser import parse_months_range


def format_file_sizes(bytes_count: int) -> dict[str, Any]:
    """Formats raw bytes into a nested structure (bytes, bits, mb).

    Args:
        bytes_count: Physical size in raw bytes.

    Returns:
        Dict[str, Any]: Nested bytes, bits, and mb mapping.
    """
    return {
        "bytes": bytes_count,
        "bits": bytes_count * 8,
        "mb": round(bytes_count / (1024 * 1024), 4),
    }


def map_raw_fms_item(item: dict[str, Any]) -> dict[str, Any]:
    """Maps a raw FMS API record into our structured metadata schema.

    Computes the file's xxh3_128 watermark signature and formats physical
    metrics recursively.

    Args:
        item: Raw FMS catalog item dictionary.

    Returns:
        Dict[str, Any]: Mapped dictionary conforming to the catalog schema.
    """
    name = item.get("name", "")
    size_bytes = item.get("originalSize", 0)
    comp_size_bytes = item.get("size", 0)
    last_updated = item.get("lastUpdatedTimestamp", "")
    file_id = item.get("fileId", "")

    # Invoke xxHash utility from the API transport layer
    file_hash = calculate_idempotency_hash(name, size_bytes, last_updated)

    return {
        "name": name,
        "file_id": file_id,
        "sizes": {
            "original": format_file_sizes(size_bytes),
            "compressed": format_file_sizes(comp_size_bytes),
        },
        "last_updated": last_updated,
        "xxhash": file_hash,
    }


def compile_folder_metadata(
    folder_name: str,
    files: list[dict[str, Any]],
    root_dir: str = "TP_export",
) -> dict[str, Any]:
    """Aggregates physical sizes and compiles folder-level metadata.

    Sums the raw original and compressed sizes across all files in the folder
    and formats them recursively.

    Args:
        folder_name: Remote FMS directory name.
        files: List of structured file metadata dictionaries.
        root_dir: Root directory of the remote FMS path (e.g. 'TP_export',
          'TP_Legacy_Publications').

    Returns:
        Dict[str, Any]: Compiled folder metadata dictionary.
    """
    total_size_bytes = sum(f["sizes"]["original"]["bytes"] for f in files)
    total_comp_size_bytes = sum(f["sizes"]["compressed"]["bytes"] for f in files)

    return {
        "folder_path": f"/{root_dir}/{folder_name}/",
        "item_count": len(files),
        "sizes": {
            "original": format_file_sizes(total_size_bytes),
            "compressed": format_file_sizes(total_comp_size_bytes),
        },
        "files": files,
    }


def compile_env_stats(
    env: str,
    all_env_files: list[dict[str, Any]],
    api_requests_count: int,
) -> dict[str, Any]:
    """Compiles high-level environmental crawling stats for summaries.

    Args:
        env: The platform identifier ('IOP' or 'PROD').
        all_env_files: Collated list of all mapped files in the environment.
        api_requests_count: Total FMS API requests triggered.

    Returns:
        Dict[str, Any]: Flat stats metadata dictionary.
    """
    total_original_bytes = sum(f["sizes"]["original"]["bytes"] for f in all_env_files)
    total_compressed_bytes = sum(
        f["sizes"]["compressed"]["bytes"] for f in all_env_files
    )

    return {
        "env": env,
        "file_count": len(all_env_files),
        "original_mb": round(total_original_bytes / (1024 * 1024), 2),
        "compressed_mb": round(total_compressed_bytes / (1024 * 1024), 2),
        "date_range": parse_months_range(all_env_files),
        "api_requests": api_requests_count,
    }
