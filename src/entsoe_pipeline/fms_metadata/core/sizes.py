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

"""Domain logic for computing aggregated directory and table size metrics from database."""

from __future__ import annotations

from typing import Any

from sqlalchemy import create_engine, select

from entsoe_pipeline.db import build_metadata, get_db_url


def compile_sizes_report(env_name: str, root_dir: str) -> dict[str, Any]:
    """Aggregates and ranks raw data size metrics from PostgreSQL database.

    Args:
        env_name: The platform environment name ('iop' or 'prod').
        root_dir: The target FMS root directory ('TP_export' or
          'TP_Legacy_Publications').

    Returns:
        dict[str, Any]: A sorted report containing aggregated sizes and files counts.
    """
    engine = create_engine(get_db_url())
    metadata = build_metadata()
    fms_folders = metadata.tables["fms_folders"]

    # Build SQL LIKE pattern to filter directories by root path
    root_prefix = f"/{root_dir}/%"

    with engine.connect() as conn:
        stmt = (
            select(
                fms_folders.c.folder_path,
                fms_folders.c.item_count,
                fms_folders.c.original_bytes,
            )
            .where(
                fms_folders.c.environment == env_name.lower(),
                fms_folders.c.folder_path.like(root_prefix),
            )
            .order_by(fms_folders.c.original_bytes.desc())
        )
        rows = conn.execute(stmt).fetchall()

    total_bytes = 0
    total_files = 0
    folders = []
    files = []

    for folder_path, item_count, original_bytes in rows:
        total_bytes += original_bytes
        total_files += item_count

        # Check if the folder path represents a root-level file
        stripped = folder_path.strip("/")
        leaf = stripped.split("/")[-1]
        is_file = False
        for ext in (".csv", ".zip", ".xml", ".xlsx"):
            if leaf.lower().endswith(ext):
                is_file = True
                break

        if is_file:
            files.append(
                {
                    "name": folder_path.rstrip("/"),
                    "raw_size_mb": round(original_bytes / (1024 * 1024), 4),
                }
            )
        else:
            folders.append(
                {
                    "name": folder_path,
                    "files_count": item_count,
                    "raw_size_mb": round(original_bytes / (1024 * 1024), 4),
                }
            )

    return {
        "total_size_mb": round(total_bytes / (1024 * 1024), 4),
        "total_files": total_files,
        "folders": folders,
        "files": files,
    }
