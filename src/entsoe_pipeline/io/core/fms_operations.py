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

"""Low-level FMS API downloads and archive extraction operations."""

from __future__ import annotations

import io
import logging
import zipfile

from entsoe_pipeline.logger.exceptions import EntsoeApiError, EntsoeConnectionError
from entsoe_pipeline.vendor_patches.entsoe_py import ConfigurableEntsoeFileClient

logger = logging.getLogger("entsoe_pipeline.io.core.fms_operations")


def download_raw_zip_from_fms(
    client: ConfigurableEntsoeFileClient,
    top_level_folder: str,
    folder_path: str,
    filename: str,
) -> bytes:
    """Sends a POST request to FMS to download a file wrapped inside a ZIP.

    Args:
        client: The authenticated client.
        top_level_folder: Root folder on FMS (e.g. 'TP_export').
        folder_path: Path under the root folder (e.g. 'ActualTotalLoad_6.1.A_r3').
        filename: Name of the target file to download.

    Returns:
        bytes: Raw zip archive bytes.

    Raises:
        EntsoeConnectionError: If network download fails.
    """
    url = (client.BASEURL or "").rstrip("/") + "/downloadFileContent"

    # Normalize folder path to have leading and trailing slashes
    folder_str = f"/{top_level_folder}/{folder_path}".replace("//", "/")
    if not folder_str.endswith("/"):
        folder_str += "/"

    payload = {
        "folder": folder_str,
        "filename": filename,
        "downloadAsZip": True,
        "topLevelFolder": top_level_folder,
    }

    client.ensure_token_valid()
    headers = {
        "Authorization": f"Bearer {client.access_token}",
        "Content-Type": "application/json",
    }

    try:
        response = client.session.post(
            url,
            json=payload,
            headers=headers,
            proxies=client.proxies,
            timeout=client.timeout,
        )
        response.raise_for_status()
        return response.content
    except Exception as e:
        logger.exception(
            "HTTP request failed for downloading file '%s' from '%s'",
            filename,
            folder_str,
        )
        raise EntsoeConnectionError(f"FMS download request failed: {e}") from e


def extract_csv_bytes_from_zip(zip_data: bytes, filename: str) -> bytes:
    """Extracts the first CSV file from a ZIP archive.

    Args:
        zip_data: Zip archive raw bytes.
        filename: Original file name for logging context.

    Returns:
        bytes: Extracted CSV file bytes.

    Raises:
        EntsoeApiError: If the zip is empty or invalid.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            namelist = zf.namelist()
            if not namelist:
                raise EntsoeApiError("FMS download response ZIP contains no files")
            # Extract first file (the CSV)
            with zf.open(namelist[0]) as inner_file:
                return inner_file.read()
    except Exception as e:
        logger.exception("Failed to parse downloaded ZIP for file '%s'", filename)
        if isinstance(e, EntsoeApiError):
            raise
        raise EntsoeApiError(f"Failed to extract FMS downloaded file: {e}") from e
