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

"""Low-level FMS folder crawling and file selection logic."""

from __future__ import annotations

import logging

from typing import Any

from entsoe_pipeline.api.ls_fms import list_folder_raw_items
from entsoe_pipeline.vendor_patches.entsoe_py import ConfigurableEntsoeFileClient

logger = logging.getLogger("entsoe_pipeline.io.core.file_selector")


def select_most_recent_csv(
    client: ConfigurableEntsoeFileClient,
    mapping: dict[str, Any],
) -> dict[str, Any] | None:
    """Lists files in the FMS directory and selects the most recent CSV.

    Args:
        client: The authenticated client.
        mapping: The path mapping containing active_folder, top_level_folder,
          remote_folder_path, and val.

    Returns:
        dict[str, Any] | None: Metadata of the selected file, containing an extra
          'remote_folder' key indicating the resolved FMS folder name, or None.
    """
    top_level = mapping["top_level_folder"]
    remote_folder_path = mapping["remote_folder_path"]
    val = mapping["val"]
    active_folder = mapping["active_folder"]

    remote_folder = active_folder if top_level == "TP_export" else remote_folder_path

    try:
        fms_files = list_folder_raw_items(
            client=client,
            folder_name=remote_folder,
            root_dir=top_level,
        )
    except Exception as e:
        logger.exception("Failed to list FMS directory '%s': %s", remote_folder, e)
        raise

    csv_files = [f for f in fms_files if f.get("name", "").endswith(".csv")]
    if not csv_files:
        logger.info(
            "No CSV files found in FMS folder '/%s/%s/'", top_level, remote_folder
        )
        return None

    # Filter by configured list if val is a list of filenames
    if isinstance(val, list) and len(val) > 0:
        csv_files = [f for f in csv_files if f.get("name") in val]
        if not csv_files:
            logger.info(
                "None of the configured files %s found in FMS folder '/%s/%s/'",
                val,
                top_level,
                remote_folder,
            )
            return None

    # Sort: primary key lastUpdatedTimestamp (desc), secondary key name (desc)
    csv_files.sort(
        key=lambda x: (x.get("lastUpdatedTimestamp", "") or "", x.get("name", "")),
        reverse=True,
    )

    selected = csv_files[0]
    selected["remote_folder"] = remote_folder
    return selected
