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

"""Scratch script to explore and extract metadata for the Load domain folders.

This script queries both the Integration/Test (IOP) and Production (PROD) platforms,
extracts physical and system features, groups them under a structured sizes section,
and serializes them into their respective fms_metadata subdirectories:
  - fms_metadata/iop/domains/TP_export/Load.yml
  - fms_metadata/prod/domains/TP_export/Load.yml

It utilizes standard paths.py definitions and the core api/client.py factories.
At the end, it outputs a comprehensive comparison summary of both catalogs.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import re
from typing import Any

import requests
import xxhash
import yaml
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from entsoe_pipeline import FMS_METADATA_DIR
from entsoe_pipeline.api import create_fms_client
from entsoe_pipeline.vendor_patches.entsoe_py import ConfigurableEntsoeFileClient

# Setup clean, scoped application logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# =============================================================================
# RESILIENT REMOTE FETCHING LOGIC
# =============================================================================

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
    reraise=True,
)
def _fetch_folder_page(
    client: ConfigurableEntsoeFileClient,
    path: str,
    page_index: int,
    page_size: int = 1000,
) -> dict[str, Any]:
    """Retrieves a single paginated chunk of items from the FMS listFolder endpoint."""
    response = client.session.post(
        client.BASEURL + "listFolder",
        data=json.dumps(
            {
                "path": path,
                "sorterList": [{"key": "name", "ascending": True}],
                "pageInfo": {"pageIndex": page_index, "pageSize": page_size},
            }
        ),
        headers={
            "Authorization": f"Bearer {client.access_token}",
            "Content-Type": "application/json",
        },
        proxies=client.proxies,
        timeout=client.timeout,
    )
    response.raise_for_status()
    return response.json()


def list_folder_files_metadata(
    client: ConfigurableEntsoeFileClient,
    folder_name: str,
    api_counter_ref: list[int],
) -> list[dict[str, Any]]:
    """Crawls a remote folder and extracts structured file metadata.

    Args:
        client: The authenticated ConfigurableEntsoeFileClient.
        folder_name: The target folder under /TP_export/ (e.g. 'ActualTotalLoad_6.1.A_r3').
        api_counter_ref: A single-element list mutable reference to track requests count.

    Returns:
        List[Dict[str, Any]]: List of file dictionaries with nested size and hash metadata.
    """
    path = f"/TP_export/{folder_name}/"
    logger.info("Crawling files in remote path: %s", path)

    all_files: list[dict[str, Any]] = []
    page_index = 0
    page_size = 1000

    while True:
        api_counter_ref[0] += 1  # Increment shared request counter
        data = _fetch_folder_page(client, path, page_index, page_size)
        items = data.get("contentItemList", [])

        for item in items:
            name = item.get("name")
            size_bytes = item.get("originalSize", 0)
            comp_size_bytes = item.get("size", 0)
            last_updated = item.get("lastUpdatedTimestamp", "")
            file_id = item.get("fileId", "")

            # Construct unique idempotency string representing current file state
            # If the file changes name, size, or timestamp, its xxHash changes instantly
            idempotency_str = f"{name}_{size_bytes}_{last_updated}"
            file_hash = xxhash.xxh3_128(idempotency_str.encode("utf-8")).hexdigest()

            all_files.append(
                {
                    "name": name,
                    "file_id": file_id,
                    "sizes": {
                        "original": {
                            "bytes": size_bytes,
                            "bits": size_bytes * 8,
                            "mb": round(size_bytes / (1024 * 1024), 4),
                        },
                        "compressed": {
                            "bytes": comp_size_bytes,
                            "bits": comp_size_bytes * 8,
                            "mb": round(comp_size_bytes / (1024 * 1024), 4),
                        },
                    },
                    "last_updated": last_updated,
                    "xxhash": file_hash,
                }
            )

        if len(items) < page_size:
            break
        page_index += 1

    all_files.sort(key=lambda x: x["name"])
    return all_files


# =============================================================================
# YAML DUMPER CUSTOMIZATION
# =============================================================================

class IndentedSafeDumper(yaml.SafeDumper):
    """Custom YAML SafeDumper that forces indentation for sequence (list) items."""

    def increase_indent(
        self,
        flow: bool = False,
        indentless: bool = False,  # noqa: ARG002
    ) -> Any:
        return super().increase_indent(flow, indentless=False)


# =============================================================================
# COMPARATIVE SUMMARY GENERATION
# =============================================================================

def parse_months_range(files: list[dict[str, Any]]) -> str:
    """Parses file names to find the oldest and newest months represented."""
    pattern = re.compile(r"(\d{4}_\d{2})")
    months = []
    for f in files:
        if match := pattern.search(f["name"]):
            months.append(match.group(1))
    
    if not months:
        return "Unknown"
    
    months.sort()
    return f"{months[0]} to {months[-1]}"


# =============================================================================
# MAIN EXECUTOR
# =============================================================================

def main() -> None:
    logger.info("=== STARTING MULTI-ENVIRONMENT LOAD METADATA EXPLORATION ===")

    load_folders = [
        "ActualTotalLoad_6.1.A_r3",
        "DayAheadTotalLoadForecast_6.1.B_r3",
        "TotalLoadForecast_6.1.C_D_E_r3",
    ]

    # Struct to keep high-level comparative stats
    comparative_stats: dict[str, dict[str, Any]] = {}

    for env in ["IOP", "PROD"]:
        logger.info("---------------------------------------------------------")
        logger.info("PROCESSING ENVIRONMENT: %s", env)
        logger.info("---------------------------------------------------------")

        # Track API requests locally for this environment
        api_counter = [0]

        try:
            client = create_fms_client(env)
        except Exception as e:
            logger.error("Failed to initialize client for %s: %s. Skipping.", env, e)
            continue

        domain_metadata = {}
        env_files_count = 0
        env_total_original_bytes = 0
        env_total_compressed_bytes = 0
        all_env_filenames: list[str] = []
        all_env_file_details: list[dict[str, Any]] = []

        for folder in load_folders:
            logger.info("Processing folder: %s", folder)
            try:
                files = list_folder_files_metadata(client, folder, api_counter)
            except Exception as e:
                logger.error("Error crawling folder %s on %s: %s", folder, env, e)
                continue
            
            total_size_bytes = sum(f["sizes"]["original"]["bytes"] for f in files)
            total_comp_size_bytes = sum(f["sizes"]["compressed"]["bytes"] for f in files)

            env_files_count += len(files)
            env_total_original_bytes += total_size_bytes
            env_total_compressed_bytes += total_comp_size_bytes
            all_env_file_details.extend(files)

            domain_metadata[folder] = {
                "folder_path": f"/TP_export/{folder}/",
                "item_count": len(files),
                "sizes": {
                    "original": {
                        "bytes": total_size_bytes,
                        "bits": total_size_bytes * 8,
                        "mb": round(total_size_bytes / (1024 * 1024), 4),
                    },
                    "compressed": {
                        "bytes": total_comp_size_bytes,
                        "bits": total_comp_size_bytes * 8,
                        "mb": round(total_comp_size_bytes / (1024 * 1024), 4),
                    },
                },
                "files": files,
            }

        # 4. Serialize the output to the correct path
        env_dir_name = env.lower()  # 'iop' or 'prod'
        output_path = FMS_METADATA_DIR / env_dir_name / "domains" / "TP_export" / "Load.yml"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info("Persisting %s metadata to: %s", env, output_path)

        current_time_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        payload = {
            "generated_at": current_time_utc,
            "total_api_requests": api_counter[0],
            "folders": domain_metadata,
        }

        with output_path.open("w", encoding="utf-8") as f:
            yaml.dump(
                payload,
                f,
                Dumper=IndentedSafeDumper,
                sort_keys=False,
                default_flow_style=False,
                allow_unicode=True,
                indent=2,
            )

        # Record comparative statistics
        comparative_stats[env] = {
            "file_count": env_files_count,
            "original_mb": round(env_total_original_bytes / (1024 * 1024), 2),
            "compressed_mb": round(env_total_compressed_bytes / (1024 * 1024), 2),
            "date_range": parse_months_range(all_env_file_details),
            "api_requests": api_counter[0],
        }

    # =============================================================================
    # 5. PRINT COMPARATIVE SUMMARY TABLE
    # =============================================================================
    logger.info("=========================================================")
    logger.info("             MULTI-ENVIRONMENT COMPARISON SUMMARY        ")
    logger.info("=========================================================")
    logger.info("%-10s | %-12s | %-12s | %-15s | %-12s | %-12s", 
                "Env", "Files Count", "Orig (MB)", "Comp (MB)", "Date Range", "API Calls")
    logger.info("-" * 85)
    
    for env, stats in comparative_stats.items():
        logger.info("%-10s | %-12d | %-12.2f | %-15.2f | %-12s | %-12d",
                    env, 
                    stats["file_count"], 
                    stats["original_mb"], 
                    stats["compressed_mb"], 
                    stats["date_range"], 
                    stats["api_requests"])
    logger.info("=========================================================")


if __name__ == "__main__":
    main()
