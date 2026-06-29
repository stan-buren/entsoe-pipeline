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

"""Unit Tests for FMS Metadata Utility Modules.

Verifies dynamic folder resolution, YAML serialization, schema transformation,
and date range compilation using the 3A pattern.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

from entsoe_pipeline.fms_metadata.utils.overview_parser import (
    get_domain_folders,
    get_legacy_archive_folders,
    parse_months_range,
)
from entsoe_pipeline.fms_metadata.utils.serializer import (
    save_fms_catalog,
    save_yaml_catalog,
)
from entsoe_pipeline.fms_metadata.utils.transformer import (
    compile_env_stats,
    compile_folder_metadata,
    format_file_sizes,
    map_raw_fms_item,
)

# =============================================================================
# 1. UNIT TESTS: UTILS / OVERVIEW_PARSER
# =============================================================================


def test_get_domain_folders_returns_folders(tmp_path: Path) -> None:
    """Verifies that get_domain_folders resolves the correct domains list."""
    # -------------------------------------------------------------------------
    # ARRANGE: Prepare the dummy environments YAML mapping and temp file
    # -------------------------------------------------------------------------
    dummy_yaml = {
        "environments": {
            "IOP": {
                "root_directories": [
                    {
                        "name": "TP_export",
                        "domains": {
                            "Load": ["ActualTotalLoad_r3"],
                        },
                    }
                ]
            }
        }
    }
    temp_overview = tmp_path / "overview.yml"

    with temp_overview.open("w", encoding="utf-8") as f:
        yaml.safe_dump(dummy_yaml, f)

    with patch(
        "entsoe_pipeline.fms_metadata.utils.overview_parser.OVERVIEW_YML", temp_overview
    ):
        # -------------------------------------------------------------------------
        # ACT: Retrieve the active load domain folders
        # -------------------------------------------------------------------------
        folders = get_domain_folders("Load", "IOP")

        # -------------------------------------------------------------------------
        # ASSERT: Verify the correct list of folders is returned
        # -------------------------------------------------------------------------
        assert folders == ["ActualTotalLoad_r3"]


def test_get_legacy_archive_folders_returns_folders(tmp_path: Path) -> None:
    """Verifies that legacy archive folders are correctly resolved and filtered."""
    # -------------------------------------------------------------------------
    # ARRANGE: Prepare the dummy legacy overview and mock path
    # -------------------------------------------------------------------------
    dummy_yaml = {
        "environments": {
            "IOP": {
                "root_directories": [
                    {
                        "name": "TP_Legacy_Publications",
                        "folders": [
                            "AcceptedAggregatedOffers_r2",
                            "FlowBasedCapacityAllocationArchives_r3",
                            "BalanceManagementCsv_R1",
                            "RandomFolder_without_suffix",
                        ],
                    }
                ]
            }
        }
    }
    temp_overview = tmp_path / "overview.yml"

    with temp_overview.open("w", encoding="utf-8") as f:
        yaml.safe_dump(dummy_yaml, f)

    with patch(
        "entsoe_pipeline.fms_metadata.utils.overview_parser.OVERVIEW_YML", temp_overview
    ):
        # -------------------------------------------------------------------------
        # ACT: Retrieve R3, R2, and R1 legacy folders
        # -------------------------------------------------------------------------
        r3_folders = get_legacy_archive_folders("R3_Archives", "IOP")
        r2_folders = get_legacy_archive_folders("R2_Archives", "IOP")
        r1_folders = get_legacy_archive_folders("R1_Archives_CSV_XML", "IOP")

        # -------------------------------------------------------------------------
        # ASSERT: Verify correct release-level matches and fallbacks
        # -------------------------------------------------------------------------
        assert r3_folders == ["FlowBasedCapacityAllocationArchives_r3"]
        assert r2_folders == ["AcceptedAggregatedOffers_r2"]
        assert r1_folders == ["BalanceManagementCsv_R1", "RandomFolder_without_suffix"]


def test_parse_months_range_extracts_bounds() -> None:
    """Verifies parse_months_range correctly determines oldest/newest months."""
    # -------------------------------------------------------------------------
    # ARRANGE: Prepare dummy files with month ranges in their names
    # -------------------------------------------------------------------------
    dummy_files = [
        {"name": "2026_03_ActualTotalLoad.csv"},
        {"name": "2015_12_ActualTotalLoad.csv"},
        {"name": "2020_06_ActualTotalLoad.csv"},
    ]

    # -------------------------------------------------------------------------
    # ACT: Parse the oldest and newest represented months
    # -------------------------------------------------------------------------
    date_range = parse_months_range(dummy_files)

    # -------------------------------------------------------------------------
    # ASSERT: Verify the expected date range represents filename bounds
    # -------------------------------------------------------------------------
    assert date_range == "2015_12 to 2026_03"


def test_parse_months_range_returns_unknown_for_empty() -> None:
    """Verifies parse_months_range handles empty or patternless names gracefully."""
    # -------------------------------------------------------------------------
    # ARRANGE: Prepare file names with no month patterns
    # -------------------------------------------------------------------------
    dummy_files = [{"name": "random_file.csv"}]

    # -------------------------------------------------------------------------
    # ACT: Attempt parsing represented months range
    # -------------------------------------------------------------------------
    date_range = parse_months_range(dummy_files)

    # -------------------------------------------------------------------------
    # ASSERT: Expect fallback to 'Unknown' string representation
    # -------------------------------------------------------------------------
    assert date_range == "Unknown"


# =============================================================================
# 2. UNIT TESTS: UTILS / TRANSFORMER
# =============================================================================


def test_format_file_sizes_computes_metrics() -> None:
    """Verifies format_file_sizes correctly translates bytes to bits and MB."""
    # -------------------------------------------------------------------------
    # ARRANGE: Define physical size in raw bytes
    # -------------------------------------------------------------------------
    bytes_val = 1024 * 1024  # 1 MB

    # -------------------------------------------------------------------------
    # ACT: Format bytes into recursively nested physical metrics
    # -------------------------------------------------------------------------
    sizes = format_file_sizes(bytes_val)

    # -------------------------------------------------------------------------
    # ASSERT: Verify accurate bytes, bits, and MB computations
    # -------------------------------------------------------------------------
    assert sizes["bytes"] == bytes_val
    assert sizes["bits"] == bytes_val * 8
    assert sizes["mb"] == 1.0


@patch("entsoe_pipeline.fms_metadata.utils.transformer.calculate_idempotency_hash")
def test_map_raw_fms_item_transforms_payload(mock_calc_hash: MagicMock) -> None:
    """Verifies raw FMS API dictionaries are transformed into catalog structures."""
    # -------------------------------------------------------------------------
    # ARRANGE: Setup mock hash signature and raw FMS catalog record
    # -------------------------------------------------------------------------
    mock_calc_hash.return_value = "dummyhash123"
    raw_item = {
        "name": "2026_05_Load.csv",
        "fileId": "file-uuid",
        "size": 500,
        "originalSize": 1000,
        "lastUpdatedTimestamp": "2026-05-28T12:00:00.000Z",
    }

    # -------------------------------------------------------------------------
    # ACT: Map raw FMS catalog item into our target catalog schema
    # -------------------------------------------------------------------------
    mapped = map_raw_fms_item(raw_item)

    # -------------------------------------------------------------------------
    # ASSERT: Verify output fields match the standardized catalog layout
    # -------------------------------------------------------------------------
    assert mapped["name"] == "2026_05_Load.csv"
    assert mapped["file_id"] == "file-uuid"
    assert mapped["sizes"]["original"]["bytes"] == 1000
    assert mapped["sizes"]["compressed"]["bytes"] == 500
    assert mapped["last_updated"] == "2026-05-28T12:00:00.000Z"
    assert mapped["xxhash"] == "dummyhash123"


def test_compile_folder_metadata_aggregates_files() -> None:
    """Verifies compile_folder_metadata sums metrics across multiple files."""
    # -------------------------------------------------------------------------
    # ARRANGE: Define structured file dictionaries containing physical sizes
    # -------------------------------------------------------------------------
    dummy_files = [
        {
            "sizes": {
                "original": {"bytes": 100},
                "compressed": {"bytes": 50},
            }
        },
        {
            "sizes": {
                "original": {"bytes": 200},
                "compressed": {"bytes": 100},
            }
        },
    ]

    # -------------------------------------------------------------------------
    # ACT: Compile folder-level metrics across the aggregated file set
    # -------------------------------------------------------------------------
    compiled = compile_folder_metadata("DummyFolder", dummy_files)

    # -------------------------------------------------------------------------
    # ASSERT: Verify correct counts, relative paths, and summed byte sizes
    # -------------------------------------------------------------------------
    assert compiled["folder_path"] == "/TP_export/DummyFolder/"
    assert compiled["item_count"] == 2
    assert compiled["sizes"]["original"]["bytes"] == 300
    assert compiled["sizes"]["compressed"]["bytes"] == 150


def test_compile_env_stats_summarizes_environment() -> None:
    """Verifies compile_env_stats creates a clear environment stats summary."""
    # -------------------------------------------------------------------------
    # ARRANGE: Setup environment metadata records and API counter metrics
    # -------------------------------------------------------------------------
    dummy_files = [
        {
            "name": "2026_05_Load.csv",
            "sizes": {
                "original": {"bytes": 1024 * 1024},
                "compressed": {"bytes": 512 * 1024},
            },
        }
    ]

    # -------------------------------------------------------------------------
    # ACT: Compile high-level summary stats for the platform
    # -------------------------------------------------------------------------
    stats = compile_env_stats("IOP", dummy_files, api_requests_count=5)

    # -------------------------------------------------------------------------
    # ASSERT: Verify counts, parsed dates, and MB metrics are correct
    # -------------------------------------------------------------------------
    assert stats["env"] == "IOP"
    assert stats["file_count"] == 1
    assert stats["original_mb"] == 1.0
    assert stats["compressed_mb"] == 0.5
    assert stats["date_range"] == "2026_05 to 2026_05"
    assert stats["api_requests"] == 5


# =============================================================================
# 3. UNIT TESTS: UTILS / SERIALIZER
# =============================================================================


@patch("entsoe_pipeline.fms_metadata.utils.serializer.save_yaml_with_observability")
def test_save_yaml_catalog_opens_and_dumps(
    mock_save_observability: MagicMock, tmp_path: Path
) -> None:
    """Verifies save_yaml_catalog writes YAML blocks to filesystem target."""
    # -------------------------------------------------------------------------
    # ARRANGE: Configure output catalog path and payload dictionary
    # -------------------------------------------------------------------------
    target = tmp_path / "dummy_catalog.yml"
    payload = {"hello": "world"}

    # -------------------------------------------------------------------------
    # ACT: Serialize the payload into YAML catalog block formats
    # -------------------------------------------------------------------------
    save_yaml_catalog(target, payload)

    # -------------------------------------------------------------------------
    # ASSERT: Verify save_yaml_with_observability is called
    # -------------------------------------------------------------------------
    mock_save_observability.assert_called_once_with(target, payload)


@patch("entsoe_pipeline.fms_metadata.utils.serializer.save_yaml_catalog")
def test_save_fms_catalog_adds_timestamps(
    mock_save_yaml: MagicMock, tmp_path: Path
) -> None:
    """Verifies save_fms_catalog delegates correctly to save_yaml_catalog."""
    # -------------------------------------------------------------------------
    # ARRANGE: Configure temporary target catalog path
    # -------------------------------------------------------------------------
    target = tmp_path / "fms_catalog.yml"

    # -------------------------------------------------------------------------
    # ACT: Serialize compiled folder catalog with run watermarks
    # -------------------------------------------------------------------------
    save_fms_catalog(target, api_requests_count=10, folders_metadata={})

    # -------------------------------------------------------------------------
    # ASSERT: Verify catalog details are saved to save_yaml_catalog
    # -------------------------------------------------------------------------
    mock_save_yaml.assert_called_once()
    saved_payload = mock_save_yaml.call_args[0][1]
    assert saved_payload["total_api_requests"] == 10
    assert saved_payload["folders"] == {}
