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

from __future__ import annotations

import logging

from typing import Any

import yaml

from entsoe_pipeline import (
    OVERVIEW_TREE_YML,
    PHYSICAL_CATALOG_DIR,
    get_classifier_config,
)
from entsoe_pipeline.fms_metadata.core.generation_data import get_generation_timestamp
from entsoe_pipeline.fms_metadata.utils.serializer import save_yaml_catalog

# Setup scoped logger strictly to our package namespace to prevent polluting root
logger = logging.getLogger("entsoe_pipeline.fms_metadata.core.overview_tree")


# =============================================================================
# 1. HIERARCHICAL TRIE COMPILERS
# =============================================================================


def expand_relative_paths(paths: list[str]) -> Any:
    """Parses a list of relative path strings and expands them into a nested tree.

    Reconstructs YYYY_MM/Region/file structures recursively. Simplifies leaf
    directories containing only files into simple lists of strings.

    Args:
        paths: A list of relative path strings (e.g. ['2015_10/CWE/file.zip']).

    Returns:
        Any: A nested tree representation (dict or list).
    """
    # 1. Build the prefix tree (Trie)
    trie: dict[str, Any] = {"_files": []}
    for path in sorted(paths):
        parts = path.split("/")
        current = trie
        for part in parts[:-1]:
            current = current.setdefault(part, {"_files": []})
        current["_files"].append(parts[-1])

    # 2. Simplify the Trie recursively
    def simplify_trie(node: dict[str, Any]) -> Any:
        subdirs = {k: v for k, v in node.items() if k != "_files"}
        files = node.get("_files", [])

        if not subdirs:
            return files

        res = {}
        for name, subdir_node in subdirs.items():
            res[name] = simplify_trie(subdir_node)

        if files:
            res["files"] = files

        return res

    return simplify_trie(trie)


# =============================================================================
# 2. LOCAL ENVIRONMENT AGGREGATORS
# =============================================================================


def build_env_tree(env_name: str) -> dict[str, Any]:
    """Reads local active and legacy catalogs for an environment and builds a tree.

    Args:
        env_name: The platform environment name ('iop' or 'prod').

    Returns:
        dict[str, Any]: The structured hierarchical tree for this env, containing:
            - description (str): Narrative description of the environment.
            - root_directories (list[dict[str, Any]]): Root structures ('TP_export',
              'TP_Legacy_Publications') with nested file trees.
    """
    env_dir = PHYSICAL_CATALOG_DIR / env_name.lower()
    logger.info("Building metadata tree from local catalogs for: %s", env_name.upper())

    # 1. Process Active Directories (TP_export)
    active_dir = env_dir / "TP_export"

    # We group active folders by domain matching the standard domain order
    config = get_classifier_config()
    domains_data: dict[str, list[Any]] = {domain: [] for domain in config.domain_order}

    if active_dir.exists():
        # Read each domain catalog file (e.g., Load.yml, Generation.yml)
        for domain_file in sorted(active_dir.glob("*.yml")):
            domain_name = domain_file.stem
            if domain_name not in domains_data:
                domains_data[domain_name] = []

            try:
                with domain_file.open("r", encoding="utf-8") as f:
                    catalog = yaml.safe_load(f) or {}

                folders_dict = catalog.get("folders", {})
                for folder_name, folder_meta in sorted(folders_dict.items()):
                    files_list = [f["name"] for f in folder_meta.get("files", [])]

                    # Flat root files (e.g. Export_log_r3.csv) are added directly
                    if folder_name.endswith((".csv", ".zip")):
                        domains_data[domain_name].append(folder_name)
                    else:
                        # Otherwise, add it as folder_name: [files]
                        domains_data[domain_name].append(
                            {folder_name: sorted(files_list)}
                        )
            except Exception:
                logger.exception("Failed to read local active catalog: %s", domain_file)

    # 2. Process Legacy Publications (TP_Legacy_Publications)
    legacy_dir = env_dir / "TP_Legacy_Publications"
    legacy_tree: dict[str, Any] = {}

    if legacy_dir.exists():
        # Crawl each archive catalog file (e.g., R3_Archives.yml)
        for archive_file in sorted(legacy_dir.glob("*.yml")):
            archive_name = archive_file.stem
            legacy_tree[archive_name] = {}

            try:
                with archive_file.open("r", encoding="utf-8") as f:
                    catalog = yaml.safe_load(f) or {}

                folders_dict = catalog.get("folders", {})
                for folder_name, folder_meta in sorted(folders_dict.items()):
                    files_paths = [f["name"] for f in folder_meta.get("files", [])]

                    # Reconstruct the nested directory tree
                    legacy_tree[archive_name][folder_name] = expand_relative_paths(
                        files_paths
                    )
            except Exception:
                logger.exception(
                    "Failed to read local legacy catalog: %s", archive_file
                )

    # Calculate exact counts of categorized directories
    active_count = sum(len(items) for items in domains_data.values())
    legacy_count = sum(len(folders) for folders in legacy_tree.values())

    return {
        "description": (
            "ENTSO-E Production Platform"
            if env_name.upper() == "PROD"
            else "ENTSO-E Integration/Test Platform"
        ),
        "root_directories": [
            {
                "name": "TP_export",
                "description": "Active publications folder",
                "item_count": active_count,
                "domains": {k: v for k, v in domains_data.items() if v},
            },
            {
                "name": "TP_Legacy_Publications",
                "description": "Legacy publications folder",
                "item_count": legacy_count,
                "archives": legacy_tree,
            },
        ],
    }


def ingest_overview_tree_metadata() -> None:
    """Orchestrates local catalogs processing, building the master overview_tree.yml."""
    logger.info("=== STARTING LOCAL METADATA OVERVIEW TREE COMPILATION ===")

    # Process local metadata catalogs for IOP and PROD
    iop_tree = build_env_tree("IOP")
    prod_tree = build_env_tree("PROD")

    overview_tree_data = {
        "generated_at": get_generation_timestamp(),
        "environments": {
            "IOP": iop_tree,
            "Prod": prod_tree,
        },
    }

    # Persist tree catalog using the safe block indent dumper
    logger.info("Persisting master tree catalog to: %s", OVERVIEW_TREE_YML)
    save_yaml_catalog(OVERVIEW_TREE_YML, overview_tree_data)

    logger.info("=== OVERVIEW TREE COMPILATION SUCCESSFULLY COMPLETED ===")
