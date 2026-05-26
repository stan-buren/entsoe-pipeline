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

    response = client.session.post(
        client.BASEURL + "listFolder",
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
