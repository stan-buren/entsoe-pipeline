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

"""ENTSO-E FMS Remote Directory Listing Module.

This module provides robust, fault-tolerant operations to query and paginate
directory listings on the ENTSO-E File Management System (FMS).
"""

from __future__ import annotations

import json
import logging

from typing import Any

import requests

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from entsoe_pipeline.logger import EntsoeApiError
from entsoe_pipeline.vendor_patches.entsoe_py import ConfigurableEntsoeFileClient

logger = logging.getLogger(__name__)


# =============================================================================
# INTERNAL OPERATIONS (Paginated Requests)
# =============================================================================


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
    reraise=True,
)
def _fetch_folder_page(
    client: ConfigurableEntsoeFileClient,
    path: str,
    page_index: int,
    page_size: int = 1000,
) -> dict[str, Any]:
    """Retrieves a single paginated chunk of items from the FMS listFolder endpoint.

    Args:
        client: The authenticated ConfigurableEntsoeFileClient instance.
        path: The remote target directory path (e.g. '/TP_export/').
        page_index: The specific page index to request.
        page_size: The maximum number of folder items to return in a single call.

    Returns:
        Dict[str, Any]: The raw JSON payload returned by the FMS API.
    """
    logger.debug("Requesting folder page %d for path '%s'...", page_index, path)

    client.ensure_token_valid()
    base_url = client.BASEURL or ""
    response = client.session.post(
        base_url + "listFolder",
        data=json.dumps(
            {
                "path": path,
                "sorterList": [{"key": "name", "ascending": True}],
                "pageInfo": {"pageIndex": page_index, "pageSize": page_size},
            }
        ),
        headers={
            "Authorization": f"Bearer {client.access_token}",
            "Content-Type": "application/json",
        },
        proxies=client.proxies,
        timeout=client.timeout,
    )
    response.raise_for_status()
    return response.json()


# =============================================================================
# PUBLIC INTERFACES (FMS Listing)
# =============================================================================


def ls_fms(
    client: ConfigurableEntsoeFileClient,
    path: str,
    page_size: int = 1000,
) -> list[str]:
    """Lists all files or subdirectories residing in an FMS remote path.

    This function automatically paginates across long directory structures,
    collating all elements into a single sorted list. It utilizes a exponential
    backoff retry strategy to recover gracefully from network glitches.

    Args:
        client: The authenticated ConfigurableEntsoeFileClient instance.
        path: The target remote directory path (e.g. '/TP_export/').
        page_size: The pagination page size to limit single response payloads.

    Returns:
        List[str]: A sorted list of remote folder or file names.
    """
    all_items: list[str] = []
    page_index = 0

    while True:
        data = _fetch_folder_page(client, path, page_index, page_size)
        current_items = data.get("contentItemList", [])

        all_items.extend([x["name"] for x in current_items])

        # If the number of items fetched is less than page_size, we've read the end
        if len(current_items) < page_size:
            break

        page_index += 1

    logger.info(
        "Successfully fetched %d remote folder items from FMS path '%s'",
        len(all_items),
        path,
    )
    return all_items


def list_folder_raw_items(
    client: ConfigurableEntsoeFileClient,
    folder_name: str,
    api_counter_ref: list[int] | None = None,
    root_dir: str = "TP_export",
) -> list[dict[str, Any]]:
    """Crawls a remote FMS folder and retrieves raw directory item records.

    Fetches the folder contents page by page, compiling the raw dictionaries
    as returned from the live FMS API listFolder endpoint.

    Args:
        client: The authenticated ConfigurableEntsoeFileClient instance.
        folder_name: Target folder name under the root directory
          (e.g., 'ActualTotalLoad_6.1.A_r3').
        api_counter_ref: Optional mutable list tracker to record total API requests.
        root_dir: The FMS root directory name (e.g. 'TP_export',
          'TP_Legacy_Publications').

    Returns:
        List[Dict[str, Any]]: Sorted list of raw item dictionaries.
    """
    if not folder_name:
        path = f"/{root_dir}/"
    elif folder_name.endswith(".csv"):
        path = f"/{root_dir}/{folder_name}"
    else:
        path = f"/{root_dir}/{folder_name}/"
    logger.info("Crawling files in remote FMS path: %s", path)

    all_items: list[dict[str, Any]] = []
    page_index = 0
    page_size = 1000

    while True:
        if api_counter_ref is not None:
            api_counter_ref[0] += 1

        try:
            data = _fetch_folder_page(client, path, page_index, page_size)
        except Exception as e:
            logger.exception(
                "Failed to fetch page %d for FMS path %s", page_index, path
            )
            raise EntsoeApiError(f"Error fetching directory page: {e}") from e

        items = data.get("contentItemList", [])
        all_items.extend(items)

        if len(items) < page_size:
            break
        page_index += 1

    # Sort the items alphabetically by name
    all_items.sort(key=lambda x: x.get("name", ""))
    return all_items


def list_folder_raw_items_recursive(
    client: ConfigurableEntsoeFileClient,
    folder_name: str,
    api_counter_ref: list[int] | None = None,
    root_dir: str = "TP_export",
    current_subpath: str = "",
) -> list[dict[str, Any]]:
    """Recursively crawls remote FMS folders and gathers raw file items.

    Args:
        client: The authenticated ConfigurableEntsoeFileClient instance.
        folder_name: Target root folder name under the root_dir (e.g.
          'BalanceManagementCsv_R1').
        api_counter_ref: Optional mutable list tracker to record total API requests.
        root_dir: The FMS root directory name (e.g. 'TP_export',
          'TP_Legacy_Publications').
        current_subpath: Internal accumulator path for nested subdirectories.

    Returns:
        List[Dict[str, Any]]: Sorted list of raw file dictionaries
          with normalized relative names.
    """
    if current_subpath:
        path = f"/{root_dir}/{folder_name}/{current_subpath}/"
    else:
        path = f"/{root_dir}/{folder_name}/"

    path = path.replace("//", "/")
    logger.info("Crawling files recursively in remote FMS path: %s", path)

    all_files: list[dict[str, Any]] = []
    page_index = 0
    page_size = 1000

    while True:
        if api_counter_ref is not None:
            api_counter_ref[0] += 1

        try:
            data = _fetch_folder_page(client, path, page_index, page_size)
        except Exception as e:
            logger.exception(
                "Failed to fetch page %d for recursive FMS path %s", page_index, path
            )
            raise EntsoeApiError(f"Error fetching directory page: {e}") from e

        items = data.get("contentItemList", [])

        for item in items:
            item_type = item.get("type", "File")
            item_name = item.get("name", "")

            if item_type == "Folder":
                # Recurse inside the subfolder
                subpath = (
                    f"{current_subpath}/{item_name}" if current_subpath else item_name
                )
                subpath = subpath.strip("/")

                nested_items = list_folder_raw_items_recursive(
                    client=client,
                    folder_name=folder_name,
                    api_counter_ref=api_counter_ref,
                    root_dir=root_dir,
                    current_subpath=subpath,
                )
                all_files.extend(nested_items)
            else:
                # It is a file! Normalize its name to preserve the relative
                # structure (e.g. 'FR/file.csv')
                if current_subpath:
                    item["name"] = f"{current_subpath}/{item_name}"
                all_files.append(item)

        if len(items) < page_size:
            break
        page_index += 1

    all_files.sort(key=lambda x: x.get("name", ""))
    return all_files
