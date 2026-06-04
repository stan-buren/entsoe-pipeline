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

"""Unit Tests for FMS Metadata Catalog Report Generator.

Verifies that the report generator successfully parses local YAML catalogs
and aggregates metadata into the target human-readable Markdown report file.
"""

from __future__ import annotations

import pathlib

from unittest.mock import MagicMock, patch

from entsoe_pipeline.fms_metadata.report.fms_metadata_readme import (
    _format_size,
    _sum_catalog_sizes,
    compile_report,
)


def test_format_size() -> None:
    """Verifies that format_size maps raw bytes to MB correctly."""
    # -------------------------------------------------------------------------
    # ARRANGE & ACT & ASSERT
    # -------------------------------------------------------------------------
    assert _format_size(10.0) == "10.00 MB"
    assert _format_size(0.0) == "0.00 MB"


@patch("entsoe_pipeline.fms_metadata.report.fms_metadata_readme.yaml.safe_load")
def test_sum_catalog_sizes_returns_aggregates(mock_safe_load: MagicMock) -> None:
    """Verifies that sum_catalog_sizes computes sizes and date ranges."""
    # -------------------------------------------------------------------------
    # ARRANGE: Mock a structured catalog with files under folder structures
    # -------------------------------------------------------------------------
    mock_file = MagicMock(spec=pathlib.Path)
    mock_file.exists.return_value = True
    mock_file.open.return_value.__enter__.return_value = MagicMock()

    mock_safe_load.return_value = {
        "folders": {
            "Load_6.1.A": {
                "sizes": {
                    "original": {"mb": 15.5},
                    "compressed": {"mb": 1.5},
                },
                "files": [
                    {"name": "2015_12_Load.csv"},
                    {"name": "2016_01_Load.csv"},
                ],
            }
        }
    }

    # -------------------------------------------------------------------------
    # ACT: Sum sizes from the mock catalog file
    # -------------------------------------------------------------------------
    orig_mb, comp_mb, count, dates = _sum_catalog_sizes(mock_file)

    # -------------------------------------------------------------------------
    # ASSERT: Verify summed MBs, counts, and calculated date ranges
    # -------------------------------------------------------------------------
    assert orig_mb == 15.5
    assert comp_mb == 1.5
    assert count == 2
    assert dates == "2015_12 to 2016_01"


@patch("entsoe_pipeline.fms_metadata.report.fms_metadata_readme.FMS_REPORT_PATH")
@patch("entsoe_pipeline.fms_metadata.report.fms_metadata_readme.PHYSICAL_CATALOG_DIR")
@patch("entsoe_pipeline.fms_metadata.report.fms_metadata_readme._sum_catalog_sizes")
def test_compile_report_generates_markdown(
    mock_sum_sizes: MagicMock,
    mock_metadata_dir: MagicMock,
    mock_report_path: MagicMock,
) -> None:
    """Verifies that compile_report collects catalogs and writes the Markdown report."""
    # -------------------------------------------------------------------------
    # ARRANGE: Set up directories and mock summation results
    # -------------------------------------------------------------------------
    mock_metadata_dir.exists.return_value = True

    mock_iop_dir = MagicMock(spec=pathlib.Path)
    mock_iop_dir.exists.return_value = True

    mock_export_dir = MagicMock(spec=pathlib.Path)
    mock_export_dir.exists.return_value = True

    mock_legacy_dir = MagicMock(spec=pathlib.Path)
    mock_legacy_dir.exists.return_value = True

    # Setup directory hierarchy navigation
    mock_metadata_dir.__truediv__.side_effect = lambda _: mock_iop_dir
    mock_iop_dir.__truediv__.side_effect = lambda x: (
        mock_export_dir if x == "TP_export" else mock_legacy_dir
    )

    # Glob yields 1 catalog file each for export and legacy publications
    mock_cat = MagicMock(spec=pathlib.Path)
    mock_cat.stem = "Load"
    mock_export_dir.glob.return_value = [mock_cat]
    mock_legacy_dir.glob.return_value = [mock_cat]

    # mock return: (orig_mb, comp_mb, file_count, date_range)
    mock_sum_sizes.return_value = (10.0, 1.0, 5, "2015_12 to 2026_12")

    # Mock file writing
    mock_file = MagicMock()
    mock_report_path.open.return_value.__enter__.return_value = mock_file
    mock_report_path.parent = MagicMock()

    # -------------------------------------------------------------------------
    # ACT: Run report compilation
    # -------------------------------------------------------------------------
    compile_report()

    # -------------------------------------------------------------------------
    # ASSERT: Verify report files are opened, written, and parsed correctly
    # -------------------------------------------------------------------------
    assert (
        mock_sum_sizes.call_count == 4
    )  # 2 environments * 2 subdirectories (export + legacy)
    mock_report_path.open.assert_called_once_with("w", encoding="utf-8")
    assert mock_file.write.call_count == 1
