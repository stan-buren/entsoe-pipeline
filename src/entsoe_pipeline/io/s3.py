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

"""S3 operational client interface for file uploads."""

from __future__ import annotations

from pathlib import Path

from entsoe_pipeline import get_config
from entsoe_pipeline.io.core.s3_operations import upload_local_file_to_s3
from entsoe_pipeline.lakehouse.core.s3_tree_builder import get_s3_client


def upload_file_to_s3(local_path: Path, s3_key: str) -> None:
    """Uploads a local file to the landing S3 bucket.

    Args:
        local_path: Path to the local file.
        s3_key: The target S3 object key.

    Raises:
        EntsoeConnectionError: If upload fails.
    """
    config = get_config()
    bucket_name = config.buckets.s3_landing_bucket
    client = get_s3_client()
    upload_local_file_to_s3(
        local_path=local_path,
        s3_key=s3_key,
        bucket_name=bucket_name,
        s3_client=client,
    )
