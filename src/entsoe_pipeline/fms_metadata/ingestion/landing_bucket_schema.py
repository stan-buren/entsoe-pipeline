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

"""Module to build the landing bucket schema contract from overview_tree.yml.

This script parses the compiled FMS directory layout tree and generates
a declarative catalog of expected directory paths in the landing zone
bucket for both Integration/Test (iop) and Production (prod) environments.
"""

from __future__ import annotations

import logging

from typing import Any

import yaml

from entsoe_pipeline import (
    LANDING_BUCKET_SCHEMA_YML,
    OVERVIEW_TREE_YML,
)

logger = logging.getLogger(
    "entsoe_pipeline.fms_metadata.ingestion.landing_bucket_schema"
)


def extract_folders_from_tree(tree_data: dict[str, Any]) -> list[str]:
    """Extracts all target directory prefixes from the overview tree structure.

    Args:
        tree_data: Parsed representation of overview_tree.yml.

    Returns:
        A sorted list of unique directory prefixes (e.g.
        'iop/TP_export/Load/ActualTotalLoad_6.1.A_r3').
    """
    folders = []

    environments = tree_data.get("environments", {})
    for env_key, env_data in environments.items():
        # Map environment name to standardized lowercase directory prefix
        env_lowercase = env_key.lower()
        root_dirs = env_data.get("root_directories", [])

        for rdir in root_dirs:
            rdir_name = rdir.get("name")

            if rdir_name == "TP_export":
                domains = rdir.get("domains", {})
                for domain_name, items in domains.items():
                    for item in items:
                        if isinstance(item, dict):
                            for extract_name in item:
                                path = (
                                    f"{env_lowercase}/{rdir_name}/"
                                    f"{domain_name}/{extract_name}"
                                )
                                folders.append(path)
            elif rdir_name == "TP_Legacy_Publications":
                archives = rdir.get("archives", {})

                # Traverse legacy archive trees recursively to locate directories
                def recurse_legacy(node: Any, current_path: list[str]) -> None:
                    if isinstance(node, list):
                        # Node is list of files; current path represents the folder
                        folders.append("/".join(current_path))
                    elif isinstance(node, dict):
                        for key, val in node.items():
                            recurse_legacy(val, [*current_path, key])

                for archive_name, archive_node in archives.items():
                    recurse_legacy(
                        archive_node,
                        [env_lowercase, rdir_name, archive_name],
                    )

    return sorted(set(folders))


def build_landing_bucket_schema() -> None:
    """Builds and saves the landing bucket directory schema configuration file.

    Loads the FMS catalog tree from OVERVIEW_TREE_YML, extracts all directory
    prefixes, and saves the schema to LANDING_BUCKET_SCHEMA_YML.
    """
    logger.info("=== STARTING LANDING BUCKET SCHEMA GENERATION ===")

    # Check if overview tree is available
    if not OVERVIEW_TREE_YML.exists():
        raise FileNotFoundError(
            f"Required overview tree file does not exist: {OVERVIEW_TREE_YML}"
        )

    logger.info("Reading overview tree catalog from: %s", OVERVIEW_TREE_YML)
    with OVERVIEW_TREE_YML.open(encoding="utf-8") as f:
        tree_data = yaml.safe_load(f) or {}

    # Extract target directories
    folders = extract_folders_from_tree(tree_data)
    logger.info("Extracted %d directory prefixes from tree.", len(folders))

    # Construct schema catalog payload
    schema_payload = {
        "schema_version": "1.0.0",
        "folders": folders,
    }

    # Persist the configuration contract
    logger.info(
        "Persisting landing bucket directory schema to: %s",
        LANDING_BUCKET_SCHEMA_YML,
    )
    from entsoe_pipeline.logger import save_yaml_with_observability

    save_yaml_with_observability(LANDING_BUCKET_SCHEMA_YML, schema_payload)

    logger.info("=== LANDING BUCKET SCHEMA GENERATION COMPLETED ===")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    build_landing_bucket_schema()
