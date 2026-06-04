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

"""ENTSO-E FMS Metadata Catalog Report Generator.

Parses the structured machine-readable YAML catalogs for active domains and
historical archives across all platforms (IOP and PROD), dynamically sums
file counts and sizes, and auto-generates a human-readable analytical Markdown report.
"""

from __future__ import annotations

import logging
import pathlib
import re

from datetime import UTC, datetime

import yaml

from entsoe_pipeline import FMS_REPORT_PATH, PHYSICAL_CATALOG_DIR

logger = logging.getLogger("entsoe_pipeline.fms_metadata.report.generator")


def _format_size(mb_val: float) -> str:
    """Formats a Megabyte float value into a readable string.

    Args:
        mb_val: Physical size in Megabytes.

    Returns:
        str: Formatted string in MB (e.g. '123.45 MB').
    """
    return f"{mb_val:.2f} MB"


def _sum_catalog_sizes(yml_file: pathlib.Path) -> tuple[float, float, int, str]:
    """Parses a YAML catalog and computes file count, sizes in MB, and date ranges.

    Args:
        yml_file: Absolute path to the catalog YAML file.

    Returns:
        tuple[float, float, int, str]: A tuple containing:
          - total_original_mb (float)
          - total_compressed_mb (float)
          - file_count (int)
          - date_range (str)
    """
    if not yml_file.exists():
        return 0.0, 0.0, 0, "N/A"

    try:
        with yml_file.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        logger.exception("Failed to parse catalog YAML at %s", yml_file)
        return 0.0, 0.0, 0, "Error"

    orig_mb = 0.0
    comp_mb = 0.0
    file_count = 0
    all_files = []

    folders = data.get("folders", {})
    for folder_info in folders.values():
        orig_mb += folder_info.get("sizes", {}).get("original", {}).get("mb", 0.0)
        comp_mb += folder_info.get("sizes", {}).get("compressed", {}).get("mb", 0.0)
        files_list = folder_info.get("files", [])
        file_count += len(files_list)
        all_files.extend(files_list)

    # Parse date range using year_month search in file names
    pattern = re.compile(r"(\d{4}_\d{2})")
    months = [
        match.group(1)
        for f in all_files
        if (match := pattern.search(f.get("name", "")))
    ]

    if months:
        months.sort()
        date_range = f"{months[0]} to {months[-1]}"
    else:
        date_range = "N/A"

    return orig_mb, comp_mb, file_count, date_range


def compile_report() -> None:
    """Orchestrates FMS catalogs aggregation and generates the Markdown report."""
    logger.info("Initializing human-readable metadata report generation...")

    report_content = []
    report_content.append("# ENTSO-E FMS Metadata Catalog Analysis Report")
    report_content.append("")
    report_content.append(
        "This report is an automatically compiled, human-readable analytical "
        "summary of the ENTSO-E File Management System (FMS) active domains "
        "and historical legacy archives cataloged in the repository."
    )
    report_content.append("")
    report_content.append(
        f"*Generated at: {datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')} (UTC)*"
    )
    report_content.append("")
    report_content.append("---")

    envs = ["IOP", "PROD"]

    for env in envs:
        env_dir = PHYSICAL_CATALOG_DIR / env.lower()
        if not env_dir.exists():
            continue

        report_content.append("")
        report_content.append(f"## Platform Environment: {env}")
        report_content.append("")

        # 1. Active Domains
        export_dir = env_dir / "TP_export"
        report_content.append("### 🚀 Active Publication Domains (TP_export)")
        report_content.append("")
        report_content.append(
            "| Domain | Files Count | Original Size | "
            "Compressed Size | Compression | Date Range |"
        )
        report_content.append("|---|---|---|---|---|---|")

        total_export_orig = 0
        total_export_comp = 0
        total_export_files = 0

        active_catalogs = (
            sorted(export_dir.glob("*.yml")) if export_dir.exists() else []
        )
        for cat in active_catalogs:
            domain_name = cat.stem
            orig, comp, count, dates = _sum_catalog_sizes(cat)
            total_export_orig += orig
            total_export_comp += comp
            total_export_files += count
            ratio = f"{orig / max(comp, 1.0):.2f}x" if comp else "N/A"
            report_content.append(
                f"| {domain_name} | {count} | {_format_size(orig)} | "
                f"{_format_size(comp)} | {ratio} | {dates} |"
            )

        export_ratio = (
            f"{total_export_orig / max(total_export_comp, 1.0):.2f}x"
            if total_export_comp
            else "N/A"
        )
        report_content.append(
            f"| **Active Export Total** | **{total_export_files}** | "
            f"**{_format_size(total_export_orig)}** | "
            f"**{_format_size(total_export_comp)}** | "
            f"**{export_ratio}** | **-** |"
        )

        # 2. Legacy Publications
        legacy_dir = env_dir / "TP_Legacy_Publications"
        report_content.append("")
        report_content.append(
            "### 📂 Historical Publications Archives (TP_Legacy_Publications)"
        )
        report_content.append("")
        report_content.append(
            "| Release / Archive | Files Count | Original Size | "
            "Compressed Size | Compression | Date Range |"
        )
        report_content.append("|---|---|---|---|---|---|")

        total_legacy_orig = 0
        total_legacy_comp = 0
        total_legacy_files = 0

        legacy_catalogs = (
            sorted(legacy_dir.glob("*.yml")) if legacy_dir.exists() else []
        )
        for cat in legacy_catalogs:
            archive_name = cat.stem
            orig, comp, count, dates = _sum_catalog_sizes(cat)
            total_legacy_orig += orig
            total_legacy_comp += comp
            total_legacy_files += count
            ratio = f"{orig / max(comp, 1.0):.2f}x" if comp else "N/A"
            report_content.append(
                f"| {archive_name} | {count} | {_format_size(orig)} | "
                f"{_format_size(comp)} | {ratio} | {dates} |"
            )

        legacy_ratio = (
            f"{total_legacy_orig / max(total_legacy_comp, 1.0):.2f}x"
            if total_legacy_comp
            else "N/A"
        )
        report_content.append(
            f"| **Legacy Archives Total** | **{total_legacy_files}** | "
            f"**{_format_size(total_legacy_orig)}** | "
            f"**{_format_size(total_legacy_comp)}** | "
            f"**{legacy_ratio}** | **-** |"
        )

        # 3. Combined Total
        combined_orig = total_export_orig + total_legacy_orig
        combined_comp = total_export_comp + total_legacy_comp
        combined_ratio = (
            f"{combined_orig / max(combined_comp, 1.0):.2f}x"
            if combined_comp
            else "N/A"
        )
        report_content.append("")
        report_content.append(
            f"**Combined Total ({env}):** "
            f"`{total_export_files + total_legacy_files}` files | "
            f"Original: `{_format_size(combined_orig)}` | "
            f"Compressed: `{_format_size(combined_comp)}` | "
            f"Compression: `{combined_ratio}`"
        )
        report_content.append("")
        report_content.append("---")

    # Write output Markdown report to FMS_REPORT_PATH
    try:
        FMS_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with FMS_REPORT_PATH.open("w", encoding="utf-8") as f:
            f.write("\n".join(report_content))
        logger.info(
            "Successfully generated human-readable report at: %s", FMS_REPORT_PATH
        )
    except Exception:
        logger.exception("Failed to write Markdown report to %s", FMS_REPORT_PATH)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
    )
    compile_report()
