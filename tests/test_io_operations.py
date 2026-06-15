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

"""Unit Tests for low-level I/O operations.

Tests cover file selection, FMS API ZIP extraction, and S3 communication.
Follows 3A - Arrange, Act, Assert.
"""

from __future__ import annotations

import io
import zipfile

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from botocore.exceptions import ClientError

from entsoe_pipeline.io.core.file_selector import select_most_recent_csv
from entsoe_pipeline.io.core.fms_operations import (
    download_raw_zip_from_fms,
    extract_csv_bytes_from_zip,
)
from entsoe_pipeline.io.core.s3_operations import (
    s3_object_exists,
    upload_local_file_to_s3,
)
from entsoe_pipeline.logger.exceptions import EntsoeApiError, EntsoeConnectionError

# =============================================================================
# 1. UNIT TESTS: FILE SELECTOR
# =============================================================================


def test_select_most_recent_csv_empty() -> None:
    """Verifies None is returned if no CSV files exist in listed items."""
    client = MagicMock()
    mapping = {
        "top_level_folder": "TP_export",
        "remote_folder_path": "Load",
        "val": True,
        "active_folder": "ActualTotalLoad",
    }
    with patch(
        "entsoe_pipeline.io.core.file_selector.list_folder_raw_items", return_value=[]
    ):
        res = select_most_recent_csv(client, mapping)
        assert res is None


def test_select_most_recent_csv_with_filter() -> None:
    """Verifies correct selection when a specific list of files is configured."""
    client = MagicMock()
    mapping = {
        "top_level_folder": "TP_export",
        "remote_folder_path": "Load",
        "val": ["file1.csv"],
        "active_folder": "ActualTotalLoad",
    }
    files = [
        {"name": "file1.csv", "lastUpdatedTimestamp": "2026-06-01T00:00:00Z"},
        {"name": "file2.csv", "lastUpdatedTimestamp": "2026-06-02T00:00:00Z"},
    ]
    with patch(
        "entsoe_pipeline.io.core.file_selector.list_folder_raw_items",
        return_value=files,
    ):
        res = select_most_recent_csv(client, mapping)
        assert res is not None
        assert res["name"] == "file1.csv"
        assert res["remote_folder"] == "ActualTotalLoad"


def test_select_most_recent_csv_with_filter_no_match() -> None:
    """Verifies None is returned if files do not match configured filenames."""
    client = MagicMock()
    mapping = {
        "top_level_folder": "TP_export",
        "remote_folder_path": "Load",
        "val": ["file3.csv"],
        "active_folder": "ActualTotalLoad",
    }
    files = [
        {"name": "file1.csv", "lastUpdatedTimestamp": "2026-06-01T00:00:00Z"},
    ]
    with patch(
        "entsoe_pipeline.io.core.file_selector.list_folder_raw_items",
        return_value=files,
    ):
        res = select_most_recent_csv(client, mapping)
        assert res is None


def test_select_most_recent_csv_exception() -> None:
    """Verifies list exceptions are successfully propagated."""
    client = MagicMock()
    mapping = {
        "top_level_folder": "TP_export",
        "remote_folder_path": "Load",
        "val": True,
        "active_folder": "ActualTotalLoad",
    }
    with (
        patch(
            "entsoe_pipeline.io.core.file_selector.list_folder_raw_items",
            side_effect=ValueError("test err"),
        ),
        pytest.raises(ValueError, match="test err"),
    ):
        select_most_recent_csv(client, mapping)


# =============================================================================
# 2. UNIT TESTS: FMS OPERATIONS
# =============================================================================


def test_download_raw_zip_from_fms_success() -> None:
    """Verifies post call is executed and raw bytes returned."""
    client = MagicMock()
    client.BASEURL = "https://example.com"
    client.access_token = "token"
    client.proxies = {}
    client.timeout = 10

    mock_response = MagicMock()
    mock_response.content = b"zipbytes"
    client.session.post.return_value = mock_response

    data = download_raw_zip_from_fms(client, "TP_export", "path", "file.csv")
    assert data == b"zipbytes"
    client.session.post.assert_called_once()


def test_download_raw_zip_from_fms_failure() -> None:
    """Verifies HTTP errors are wrapped inside EntsoeConnectionError."""
    client = MagicMock()
    client.BASEURL = "https://example.com"
    client.session.post.side_effect = ValueError("network error")

    with pytest.raises(EntsoeConnectionError, match="FMS download request failed"):
        download_raw_zip_from_fms(client, "TP_export", "path", "file.csv")


def test_extract_csv_bytes_from_zip_success() -> None:
    """Verifies a CSV file is extracted from a zip container."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("test.csv", b"csvdata")

    res = extract_csv_bytes_from_zip(buf.getvalue(), "test.csv")
    assert res == b"csvdata"


def test_extract_csv_bytes_from_zip_empty() -> None:
    """Verifies EntsoeApiError is raised when zip archive is empty."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w"):
        pass

    with pytest.raises(
        EntsoeApiError, match="FMS download response ZIP contains no files"
    ):
        extract_csv_bytes_from_zip(buf.getvalue(), "test.csv")


def test_extract_csv_bytes_from_zip_invalid() -> None:
    """Verifies EntsoeApiError is raised on corrupted zip archives."""
    with pytest.raises(EntsoeApiError, match="Failed to extract FMS downloaded file"):
        extract_csv_bytes_from_zip(b"invalid zip", "test.csv")


# =============================================================================
# 3. UNIT TESTS: S3 OPERATIONS
# =============================================================================


def test_upload_local_file_to_s3_success(tmp_path: Path) -> None:
    """Verifies standard boto3 upload path."""
    f = tmp_path / "test.txt"
    f.write_text("hello")
    s3_client = MagicMock()
    upload_local_file_to_s3(f, "key", "bucket", s3_client)
    s3_client.upload_file.assert_called_once_with(
        Filename=str(f), Bucket="bucket", Key="key"
    )


def test_upload_local_file_to_s3_failure(tmp_path: Path) -> None:
    """Verifies errors during upload wrap in EntsoeConnectionError."""
    f = tmp_path / "test.txt"
    f.write_text("hello")
    s3_client = MagicMock()
    s3_client.upload_file.side_effect = Exception("s3 error")
    with pytest.raises(EntsoeConnectionError, match="S3 upload failed for key key"):
        upload_local_file_to_s3(f, "key", "bucket", s3_client)


def test_s3_object_exists_true() -> None:
    """Verifies head_object returning successfully means exists is True."""
    s3_client = MagicMock()
    s3_client.head_object.return_value = {}
    assert s3_object_exists("key", "bucket", s3_client) is True


def test_s3_object_exists_false_404() -> None:
    """Verifies ClientError with 404 code maps to False."""
    s3_client = MagicMock()
    err_response = {"Error": {"Code": "404", "Message": "Not Found"}}
    s3_client.head_object.side_effect = ClientError(err_response, "HeadObject")
    assert s3_object_exists("key", "bucket", s3_client) is False


def test_s3_object_exists_false_other_err() -> None:
    """Verifies ClientError with non-404 code maps to False."""
    s3_client = MagicMock()
    err_response = {"Error": {"Code": "500", "Message": "Internal Error"}}
    s3_client.head_object.side_effect = ClientError(err_response, "HeadObject")
    assert s3_object_exists("key", "bucket", s3_client) is False


def test_s3_object_exists_unexpected_exception() -> None:
    """Verifies raw Exceptions map to False."""
    s3_client = MagicMock()
    s3_client.head_object.side_effect = RuntimeError("unexpected")
    assert s3_object_exists("key", "bucket", s3_client) is False
