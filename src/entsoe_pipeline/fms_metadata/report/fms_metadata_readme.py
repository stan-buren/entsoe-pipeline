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

Queries physical metadata from PostgreSQL and auto-generates a human-readable
analytical Markdown report detailing active data domains and legacy archives.
"""

from __future__ import annotations

import logging
import re

from datetime import UTC, datetime

from sqlalchemy import create_engine, select

from entsoe_pipeline import FMS_REPORT_PATH
from entsoe_pipeline.db import build_metadata, get_db_url

logger = logging.getLogger("entsoe_pipeline.fms_metadata.report.generator")


def _format_size(mb_val: float) -> str:
    """Formats a Megabyte float value into a readable string.

    Args:
        mb_val: Physical size in Megabytes.

    Returns:
        str: Formatted string in MB (e.g. '123.45 MB').
    """
    return f"{mb_val:.2f} MB"


def _get_domain_summary(
    conn, fms_folders, fms_files, env: str, domain: str
) -> tuple[float, float, int, str]:
    """Queries aggregated domain folder metrics and determines file date ranges.

    Args:
        conn: Active database connection.
        fms_folders: The fms_folders table object.
        fms_files: The fms_files table object.
        env: Target platform environment name (e.g. 'iop' or 'prod').
        domain: Specific domain or archive identifier name.

    Returns:
        tuple[float, float, int, str]: A tuple containing:
          - total_original_mb (float)
          - total_compressed_mb (float)
          - file_count (int)
          - date_range (str)
    """
    stmt = select(
        fms_folders.c.id,
        fms_folders.c.original_bytes,
        fms_folders.c.compressed_bytes,
        fms_folders.c.item_count,
    ).where(
        fms_folders.c.environment == env.lower(),
        fms_folders.c.domain == domain,
    )
    rows = conn.execute(stmt).fetchall()

    orig_bytes = sum(row[1] for row in rows)
    comp_bytes = sum(row[2] for row in rows)
    file_count = sum(row[3] for row in rows)

    orig_mb = round(orig_bytes / (1024 * 1024), 4)
    comp_mb = round(comp_bytes / (1024 * 1024), 4)

    folder_ids = [row[0] for row in rows]
    if not folder_ids:
        return 0.0, 0.0, 0, "N/A"

    # Query file names associated with these folders to parse date range.
    file_stmt = select(fms_files.c.name).where(fms_files.c.folder_id.in_(folder_ids))
    file_names = [row[0] for row in conn.execute(file_stmt).fetchall()]

    # Parse date range using year_month search in file names (e.g. '2023_04').
    pattern = re.compile(r"(\d{4}_\d{2})")
    months = [match.group(1) for f in file_names if (match := pattern.search(f))]

    if months:
        months.sort()
        date_range = f"{months[0]} to {months[-1]}"
    else:
        date_range = "N/A"

    return orig_mb, comp_mb, file_count, date_range


def compile_report() -> None:
    """Orchestrates FMS database metadata aggregation and generates the Markdown report."""
    logger.info("Initializing human-readable metadata report generation...")

    report_content = []
    report_content.append("# ENTSO-E FMS Metadata Catalog Analysis Report")
    report_content.append("")
    report_content.append(
        "This report is an automatically compiled, human-readable analytical "
        "summary of the ENTSO-E File Management System (FMS) active domains "
        "and historical legacy archives cataloged in the database."
    )
    report_content.append("")
    report_content.append(
        f"*Generated at: {datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')} (UTC)*"
    )
    report_content.append("")
    report_content.append("---")

    engine = create_engine(get_db_url())
    metadata = build_metadata()
    fms_folders = metadata.tables["fms_folders"]
    fms_files = metadata.tables["fms_files"]

    envs = ["IOP", "PROD"]

    with engine.connect() as conn:
        for env in envs:
            # Check if folders exist for the current environment.
            check_stmt = select(fms_folders.c.id).where(
                fms_folders.c.environment == env.lower()
            )
            if not conn.execute(check_stmt).first():
                continue

            report_content.append("")
            report_content.append(f"## Platform Environment: {env}")
            report_content.append("")

            # 1. Active Domains
            report_content.append("### 🚀 Active Publication Domains (TP_export)")
            report_content.append("")
            report_content.append(
                "| Domain | Files Count | Original Size | "
                "Compressed Size | Compression | Date Range |"
            )
            report_content.append("|---|---|---|---|---|---|")

            total_export_orig = 0.0
            total_export_comp = 0.0
            total_export_files = 0

            # Query unique domains registered under TP_export folder root.
            active_domains_stmt = (
                select(fms_folders.c.domain)
                .where(
                    fms_folders.c.environment == env.lower(),
                    fms_folders.c.folder_path.like("/TP_export/%"),
                )
                .distinct()
                .order_by(fms_folders.c.domain)
            )
            active_domains = [
                row[0] for row in conn.execute(active_domains_stmt).fetchall()
            ]

            for domain in active_domains:
                orig, comp, count, dates = _get_domain_summary(
                    conn, fms_folders, fms_files, env, domain
                )
                total_export_orig += orig
                total_export_comp += comp
                total_export_files += count
                ratio = f"{orig / max(comp, 1.0):.2f}x" if comp else "N/A"
                report_content.append(
                    f"| {domain} | {count} | {_format_size(orig)} | "
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

            total_legacy_orig = 0.0
            total_legacy_comp = 0.0
            total_legacy_files = 0

            # Query unique legacy archives registered under TP_Legacy_Publications folder root.
            legacy_stmt = (
                select(fms_folders.c.domain)
                .where(
                    fms_folders.c.environment == env.lower(),
                    fms_folders.c.folder_path.like("/TP_Legacy_Publications/%"),
                )
                .distinct()
                .order_by(fms_folders.c.domain)
            )
            legacy_domains = [row[0] for row in conn.execute(legacy_stmt).fetchall()]

            for domain in legacy_domains:
                orig, comp, count, dates = _get_domain_summary(
                    conn, fms_folders, fms_files, env, domain
                )
                total_legacy_orig += orig
                total_legacy_comp += comp
                total_legacy_files += count
                ratio = f"{orig / max(comp, 1.0):.2f}x" if comp else "N/A"
                report_content.append(
                    f"| {domain} | {count} | {_format_size(orig)} | "
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

    # Write output Markdown report to FMS_REPORT_PATH.
    try:
        FMS_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with FMS_REPORT_PATH.open("w", encoding="utf-8") as f:
            f.write("\n".join(report_content))
        logger.info(
            "Successfully generated human-readable report at: %s",
            FMS_REPORT_PATH,
        )
    except Exception:
        logger.exception("Failed to write Markdown report to %s", FMS_REPORT_PATH)


if __name__ == "__main__":
    from entsoe_pipeline.logger import setup_logging

    setup_logging()
    compile_report()
