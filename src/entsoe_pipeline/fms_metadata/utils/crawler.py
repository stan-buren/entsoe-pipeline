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

"""Crawler utilities to dry-up FMS active and legacy directory sweeps."""

from __future__ import annotations

import logging

from typing import Any

from entsoe_pipeline.api import list_folder_raw_items_recursive
from entsoe_pipeline.config import get_fms_extensions
from entsoe_pipeline.fms_metadata.utils.transformer import map_raw_fms_item

logger = logging.getLogger("entsoe_pipeline.fms_metadata.utils.crawler")


def crawl_metadata_folder(
    client: Any,
    folder: str,
    root_files_by_name: dict[str, Any],
    api_counter: list[int],
    env: str,
    root_dir: str = "TP_export",
) -> list[dict[str, Any]]:
    """Crawls a folder (directory recursively or file) and returns mapped metadata item list.

    Args:
        client: The authenticated FMS client.
        folder: Folder path or filename.
        root_files_by_name: Dict of pre-fetched root-level items.
        api_counter: Mutable request counter.
        env: Target environment name.
        root_dir: The target FMS root directory (e.g. 'TP_export',
          'TP_Legacy_Publications').

    Returns:
        list[dict[str, Any]]: List of mapped metadata records.
    """
    allowed_exts = tuple(get_fms_extensions())
    if folder.endswith(allowed_exts):
        # Root-level file. Retrieve pre-fetched metadata.
        raw_item = root_files_by_name.get(folder)
        if raw_item:
            return [map_raw_fms_item(raw_item)]

        logger.warning(
            "Root file '%s' not found in root items of root_dir %s on env %s",
            folder,
            root_dir,
            env,
        )
        return []

    # Regular directory. Crawl recursively via FMS API
    raw_items = list_folder_raw_items_recursive(
        client=client,
        folder_name=folder,
        api_counter_ref=api_counter,
        root_dir=root_dir,
    )
    return [map_raw_fms_item(item) for item in raw_items]
