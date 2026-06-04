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

"""ENTSO-E FMS Manifest Logs Analytics and Ingestion Script.

This module connects to the live ENTSO-E FMS production platform, extracts physical
metadata and calculated xxHash digests for the core export log files, downloads them,
computes key metrics (such as row counts, date ranges, and active border pathways),
and serializes a structured metadata catalog under `fms_metadata/export_log.yml`.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import xxhash
import yaml

# Add project root to PYTHONPATH to ensure package-level absolute imports resolve
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from entsoe_pipeline import EXPORT_LOG_YML
from entsoe_pipeline.api import create_fms_client
from entsoe_pipeline.vendor_patches.entsoe_py import ConfigurableEntsoeFileClient

# Set up scoped logging configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# =============================================================================
# YAML CUSTOMIZATION
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
# METADATA EXTRACTION & ANALYTICS FUNCTIONAL CORE
# =============================================================================

def extract_fms_file_metadata(
    client: ConfigurableEntsoeFileClient,
    target_filenames: list[str],
) -> dict[str, dict[str, Any]]:
    """Crawls FMS root directory to extract physical metadata and hashes.

    Args:
        client: Authenticated ConfigurableEntsoeFileClient.
        target_filenames: List of file names to search for.

    Returns:
        Dict[str, Dict[str, Any]]: Mapping of filename -> structured metadata.
    """
    logger.info("Listing root directory /TP_export/ to extract log file details...")
    response = client.session.post(
        client.BASEURL + "listFolder",
        data=json.dumps({
            "path": "/TP_export/",
            "sorterList": [{"key": "name", "ascending": True}],
            "pageInfo": {"pageIndex": 0, "pageSize": 1000},
        }),
        headers={
            "Authorization": f"Bearer {client.access_token}",
            "Content-Type": "application/json",
        },
        proxies=client.proxies,
        timeout=client.timeout,
    )
    response.raise_for_status()
    items = response.json().get("contentItemList", [])

    extracted_meta = {}
    for item in items:
        name = item.get("name")
        if name in target_filenames:
            size_bytes = item.get("originalSize", 0)
            comp_size_bytes = item.get("size", 0)
            last_updated = item.get("lastUpdatedTimestamp", "")
            file_id = item.get("fileId", "")

            # Construct unique idempotency hash representing physical attributes
            idempotency_str = f"{name}_{size_bytes}_{last_updated}"
            file_hash = xxhash.xxh3_128(idempotency_str.encode("utf-8")).hexdigest()

            logger.info("Found log file '%s' [ID: %s, Hash: %s]", name, file_id, file_hash)

            extracted_meta[name] = {
                "file_id": file_id,
                "last_updated": last_updated,
                "xxhash": file_hash,
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
            }

    return extracted_meta


def analyze_standard_log(df: pd.DataFrame) -> dict[str, Any]:
    """Computes key analytics for the standard export log.

    Args:
        df: Pandas DataFrame representing Export_log_r3.csv.

    Returns:
        Dict[str, Any]: Computed metrics dictionary.
    """
    logger.info("Computing metrics for the standard export log...")
    total_rows = len(df)
    unique_datasets = df["file_name"].nunique()

    # Determine date range represented in files
    pattern = pd.to_numeric(df["year"], errors="coerce")
    min_year = int(pattern.min()) if not pd.isna(pattern.min()) else "Unknown"
    max_year = int(pattern.max()) if not pd.isna(pattern.max()) else "Unknown"

    return {
        "total_rows": total_rows,
        "unique_datasets": unique_datasets,
        "date_range": f"{min_year} to {max_year}",
        "max_update_time_range": f"{df['max_update_time(UTC)'].min()} to {df['max_update_time(UTC)'].max()}",
    }


def analyze_oce_log(df: pd.DataFrame) -> dict[str, Any]:
    """Computes key analytics for the Offered Capacity Evolution log.

    Args:
        df: Pandas DataFrame representing Export_oce_log_r3.csv.

    Returns:
        Dict[str, Any]: Computed metrics dictionary.
    """
    logger.info("Computing metrics for the Offered Capacity Evolution log...")
    total_rows = len(df)
    unique_datasets = df["file_name"].nunique()

    # Calculate active border directions tracked in the evolution log
    unique_borders = 0
    if "out_area" in df.columns and "in_area" in df.columns:
        df["border_dir"] = df["out_area"].astype(str) + "_" + df["in_area"].astype(str)
        unique_borders = int(df["border_dir"].nunique())

    pattern = pd.to_numeric(df["year"], errors="coerce")
    min_year = int(pattern.min()) if not pd.isna(pattern.min()) else "Unknown"
    max_year = int(pattern.max()) if not pd.isna(pattern.max()) else "Unknown"

    return {
        "total_rows": total_rows,
        "unique_datasets": unique_datasets,
        "unique_borders": unique_borders,
        "date_range": f"{min_year} to {max_year}",
    }


# =============================================================================
# MAIN EXECUTOR
# =============================================================================

def main() -> None:
    """Main orchestrator function."""
    logger.info("=== STARTING FMS LOG METADATA DISCOVERY & ANALYTICS ===")

    # 1. Connect to production FMS
    try:
        client = create_fms_client("PROD")
    except Exception as e:
        logger.error("Failed to initialize FMS Client: %s", e)
        sys.exit(1)

    # 2. Extract physical metadata and file_ids from root folder listing
    target_files = ["Export_log_r3.csv", "Export_oce_log_r3.csv"]
    try:
        log_meta = extract_fms_file_metadata(client, target_files)
    except Exception as e:
        logger.error("Error fetching FMS root folder listing: %s", e)
        sys.exit(1)

    if not all(k in log_meta for k in target_files):
        logger.error("Critical: Could not locate both log files in the root folder listing!")
        sys.exit(1)

    # 3. Download and parse both log files
    logger.info("Downloading Export_log_r3.csv from FMS...")
    try:
        df_std = client.download_single_file(folder="", filename="Export_log_r3.csv")
    except Exception as e:
        logger.error("Failed to download standard export log: %s", e)
        sys.exit(1)

    logger.info("Downloading Export_oce_log_r3.csv from FMS...")
    try:
        df_oce = client.download_single_file(folder="", filename="Export_oce_log_r3.csv")
    except Exception as e:
        logger.error("Failed to download Offered Capacity Evolution log: %s", e)
        sys.exit(1)

    # 4. Compute analytics
    std_metrics = analyze_standard_log(df_std)
    oce_metrics = analyze_oce_log(df_oce)

    # Inject metrics into metadata blocks
    log_meta["Export_log_r3.csv"]["analytics"] = std_metrics
    log_meta["Export_oce_log_r3.csv"]["analytics"] = oce_metrics

    # 5. Persist to fms_metadata/export_log.yml
    current_time_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "generated_at": current_time_utc,
        "total_api_requests": 3,
        "logs": log_meta,
    }

    EXPORT_LOG_YML.parent.mkdir(parents=True, exist_ok=True)
    with EXPORT_LOG_YML.open("w", encoding="utf-8") as f:
        yaml.dump(
            payload,
            f,
            Dumper=IndentedSafeDumper,
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
            indent=2,
        )

    logger.info("Success! Metadata catalog compiled to: %s", EXPORT_LOG_YML)

    # =========================================================================
    # PRINT ANALYTICS SUMMARY REPORT
    # =========================================================================
    print("\n" + "=" * 60)
    print("             ENTSO-E FMS LOG INGESTION REPORT")
    print("=" * 60)
    print(f"Generated At: {current_time_utc}")
    print("-" * 60)
    
    std = log_meta["Export_log_r3.csv"]
    print("1. Standard Publications Ledger (Export_log_r3.csv):")
    print(f"   - File ID:      {std['file_id']}")
    print(f"   - Physical Size:{std['sizes']['original']['mb']} MB")
    print(f"   - xxHash:       {std['xxhash']}")
    print(f"   - Total Rows:   {std['analytics']['total_rows']} entries")
    print(f"   - Datasets:     {std['analytics']['unique_datasets']} folders")
    print(f"   - Date Range:   {std['analytics']['date_range']}")
    
    print("-" * 60)
    oce = log_meta["Export_oce_log_r3.csv"]
    print("2. Offered Capacity Evolution Ledger (Export_oce_log_r3.csv):")
    print(f"   - File ID:      {oce['file_id']}")
    print(f"   - Physical Size:{oce['sizes']['original']['mb']} MB")
    print(f"   - xxHash:       {oce['xxhash']}")
    print(f"   - Total Rows:   {oce['analytics']['total_rows']} entries")
    print(f"   - Datasets:     {oce['analytics']['unique_datasets']} folders")
    print(f"   - Active Borders:{oce['analytics']['unique_borders']} borders")
    print(f"   - Date Range:   {oce['analytics']['date_range']}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
