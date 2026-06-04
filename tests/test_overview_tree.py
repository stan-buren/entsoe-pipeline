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

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from entsoe_pipeline.fms_metadata.core.overview_tree import (
    build_env_tree,
    expand_relative_paths,
    ingest_overview_tree_metadata,
)

# =============================================================================
# 1. UNIT TESTS: RELATIVE PATH EXPANSION & TRIE SIMPLIFICATION
# =============================================================================


def test_expand_relative_paths_flat() -> None:
    """Verifies that flat file paths (no subdirectories) are returned as a flat list."""
    # -------------------------------------------------------------------------
    # ARRANGE
    # -------------------------------------------------------------------------
    flat_paths = ["file2.csv", "file1.csv"]

    # -------------------------------------------------------------------------
    # ACT
    # -------------------------------------------------------------------------
    result = expand_relative_paths(flat_paths)

    # -------------------------------------------------------------------------
    # ASSERT
    # -------------------------------------------------------------------------
    assert result == ["file1.csv", "file2.csv"]


def test_expand_relative_paths_nested() -> None:
    """Verifies relative paths expand recursively into simplified tree structures."""
    # -------------------------------------------------------------------------
    # ARRANGE
    # -------------------------------------------------------------------------
    nested_paths = [
        "2015_10/CWE/file1.zip",
        "2015_10/CWE/file2.zip",
        "2015_10/file3.zip",
        "root_file.zip",
    ]

    # -------------------------------------------------------------------------
    # ACT
    # -------------------------------------------------------------------------
    result = expand_relative_paths(nested_paths)

    # -------------------------------------------------------------------------
    # ASSERT
    # -------------------------------------------------------------------------
    assert result == {
        "2015_10": {
            "CWE": ["file1.zip", "file2.zip"],
            "files": ["file3.zip"],
        },
        "files": ["root_file.zip"],
    }


# =============================================================================
# 2. UNIT TESTS: LOCAL CATALOGS CRAWLING
# =============================================================================


@patch("entsoe_pipeline.fms_metadata.core.overview_tree.PHYSICAL_CATALOG_DIR")
def test_build_env_tree_aggregates_local_catalogs(
    mock_metadata_dir: Path,
    tmp_path: Path,
) -> None:
    """Verifies env tree correctly reads active and legacy catalogs from disk."""
    # -------------------------------------------------------------------------
    # ARRANGE
    # -------------------------------------------------------------------------
    # Configure mock metadata directory to point to the pytest tmp_path
    mock_metadata_dir.joinpath.side_effect = tmp_path.joinpath
    mock_metadata_dir.__truediv__.side_effect = lambda other: tmp_path / other

    # Setup directories
    active_dir = tmp_path / "iop" / "TP_export"
    active_dir.mkdir(parents=True, exist_ok=True)
    legacy_dir = tmp_path / "iop" / "TP_Legacy_Publications"
    legacy_dir.mkdir(parents=True, exist_ok=True)

    # 1. Create a dummy active catalog (Load.yml)
    load_catalog = {
        "generated_at": "2026-05-28T14:12:41Z",
        "folders": {
            "Export_log_r3.csv": {"files": [{"name": "Export_log_r3.csv"}]},
            "ActualTotalLoad_6.1.A_r3": {
                "files": [
                    {"name": "2020_04_ActualTotalLoad_6.1.A_r3.csv"},
                    {"name": "2021_01_ActualTotalLoad_6.1.A_r3.csv"},
                ]
            },
        },
    }
    with (active_dir / "Load.yml").open("w", encoding="utf-8") as f:
        yaml.dump(load_catalog, f)

    # 2. Create a dummy legacy catalog (R3_Archives.yml)
    legacy_catalog = {
        "folders": {
            "FlowBasedCapacityAllocationArchives_11.1.B_r3": {
                "files": [
                    {"name": "2015_10/CWE/file1.zip"},
                    {"name": "2016_01/file2.zip"},
                ]
            }
        }
    }
    with (legacy_dir / "R3_Archives.yml").open("w", encoding="utf-8") as f:
        yaml.dump(legacy_catalog, f)

    # -------------------------------------------------------------------------
    # ACT
    # -------------------------------------------------------------------------
    env_tree = build_env_tree("IOP")

    # -------------------------------------------------------------------------
    # ASSERT
    # -------------------------------------------------------------------------
    assert env_tree["description"] == "ENTSO-E Integration/Test Platform"

    root_dirs = env_tree["root_directories"]
    assert len(root_dirs) == 2

    # Assert Active root directory structure
    tp_export = next(d for d in root_dirs if d["name"] == "TP_export")
    assert tp_export["item_count"] == 2
    assert "Load" in tp_export["domains"]
    assert "Export_log_r3.csv" in tp_export["domains"]["Load"]

    folder_mapping = next(
        item for item in tp_export["domains"]["Load"] if isinstance(item, dict)
    )
    assert "ActualTotalLoad_6.1.A_r3" in folder_mapping
    assert folder_mapping["ActualTotalLoad_6.1.A_r3"] == [
        "2020_04_ActualTotalLoad_6.1.A_r3.csv",
        "2021_01_ActualTotalLoad_6.1.A_r3.csv",
    ]

    # Assert Legacy root directory structure
    tp_legacy = next(d for d in root_dirs if d["name"] == "TP_Legacy_Publications")
    assert tp_legacy["item_count"] == 1
    assert "R3_Archives" in tp_legacy["archives"]

    legacy_folder = tp_legacy["archives"]["R3_Archives"][
        "FlowBasedCapacityAllocationArchives_11.1.B_r3"
    ]
    assert legacy_folder == {
        "2015_10": {"CWE": ["file1.zip"]},
        "2016_01": ["file2.zip"],
    }


# =============================================================================
# 3. INTEGRATION TESTS: ORCHESTRATION & WRITING
# =============================================================================


@patch("entsoe_pipeline.fms_metadata.core.overview_tree.OVERVIEW_TREE_YML")
@patch("entsoe_pipeline.fms_metadata.core.overview_tree.build_env_tree")
def test_ingest_overview_tree_metadata_saves_to_yaml(
    mock_build_env_tree: pytest.Mock,
    mock_overview_tree_yml: Path,
    tmp_path: Path,
) -> None:
    """Verifies that orchestrator compiles and writes master tree."""
    # -------------------------------------------------------------------------
    # ARRANGE
    # -------------------------------------------------------------------------
    dummy_iop = {"description": "IOP description", "root_directories": []}
    dummy_prod = {"description": "Prod description", "root_directories": []}
    mock_build_env_tree.side_effect = [dummy_iop, dummy_prod]

    # Configure output file location to write to our temporary pytest directory
    test_yaml_output = tmp_path / "overview_tree.yml"
    mock_overview_tree_yml.parent = test_yaml_output.parent
    mock_overview_tree_yml.open = test_yaml_output.open

    # -------------------------------------------------------------------------
    # ACT
    # -------------------------------------------------------------------------
    ingest_overview_tree_metadata()

    # -------------------------------------------------------------------------
    # ASSERT
    # -------------------------------------------------------------------------
    assert mock_build_env_tree.call_count == 2
    mock_build_env_tree.assert_any_call("IOP")
    mock_build_env_tree.assert_any_call("PROD")

    # Verify that YAML has been persisted and contains both environments
    assert test_yaml_output.exists()
    with test_yaml_output.open("r", encoding="utf-8") as f:
        payload = yaml.safe_load(f)

    assert "environments" in payload
    assert payload["environments"]["IOP"] == dummy_iop
    assert payload["environments"]["Prod"] == dummy_prod
