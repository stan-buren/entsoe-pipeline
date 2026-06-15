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

"""ENTSO-E FMS Operational File Downloader interface."""

from __future__ import annotations

from typing import Any

from entsoe_pipeline.api.client import create_fms_client
from entsoe_pipeline.api.ls_fms import (
    list_folder_raw_items,
    list_folder_raw_items_recursive,
)
from entsoe_pipeline.io.core.fms_operations import (
    download_raw_zip_from_fms,
    extract_csv_bytes_from_zip,
)
from entsoe_pipeline.logger.exceptions import EntsoeConnectionError
from entsoe_pipeline.vendor_patches.entsoe_py import ConfigurableEntsoeFileClient


def get_fms_client(env_name: str | None = None) -> ConfigurableEntsoeFileClient:
    """Retrieves an authenticated FMS client for the environment.

    Args:
        env_name: The environment name ('IOP' or 'PROD').

    Returns:
        ConfigurableEntsoeFileClient: Authenticated client instance.
    """
    try:
        return create_fms_client(env_name)
    except Exception as e:
        raise EntsoeConnectionError(f"FMS client initialization failed: {e}") from e


def list_fms_files(
    client: ConfigurableEntsoeFileClient,
    folder_name: str,
    root_dir: str = "TP_export",
    recursive: bool = False,
) -> list[dict[str, Any]]:
    """Lists files inside an FMS folder and returns their raw metadata.

    Args:
        client: The authenticated client.
        folder_name: The folder relative path under the root.
        root_dir: Root FMS directory (e.g. 'TP_export', 'TP_Legacy_Publications').
        recursive: Whether to list files recursively.

    Returns:
        list[dict[str, Any]]: List of file dictionaries with metadata.
    """
    if recursive:
        return list_folder_raw_items_recursive(client, folder_name, root_dir=root_dir)
    return list_folder_raw_items(client, folder_name, root_dir=root_dir)


def download_fms_file(
    client: ConfigurableEntsoeFileClient,
    top_level_folder: str,
    folder_path: str,
    filename: str,
) -> bytes:
    """Downloads a file from ENTSO-E FMS and extracts the inner CSV contents.

    Args:
        client: The authenticated client.
        top_level_folder: The root folder on FMS (e.g., 'TP_export').
        folder_path: The path under the root folder.
        filename: The name of the file to download.

    Returns:
        bytes: Uncompressed CSV file bytes.
    """
    zip_data = download_raw_zip_from_fms(
        client=client,
        top_level_folder=top_level_folder,
        folder_path=folder_path,
        filename=filename,
    )
    return extract_csv_bytes_from_zip(zip_data=zip_data, filename=filename)
