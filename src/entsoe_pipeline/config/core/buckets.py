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

"""Immutable S3 storage bucket configuration core module."""

from __future__ import annotations

from dataclasses import dataclass

import yaml


@dataclass(frozen=True)
class BucketsConfig:
    """Immutable S3 storage bucket configuration.

    Attributes:
        s3_landing_bucket (str): The name of the S3 bucket for landing raw files.
        s3_lakehouse_bucket (str): The name of the S3 bucket for Iceberg warehouse tables.
    """

    s3_landing_bucket: str
    s3_lakehouse_bucket: str

    @classmethod
    def _from_yaml(cls) -> BucketsConfig:
        """Loads and parses the buckets configuration from bucket.yml.

        Returns:
            BucketsConfig: The loaded buckets configuration.
        """
        from entsoe_pipeline.config.paths import CONFIG_DIR

        bucket_file = CONFIG_DIR / "bucket.yml"

        with bucket_file.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        bucket_data = data.get("buckets", {})

        return cls(
            s3_landing_bucket=str(bucket_data.get("s3_landing_bucket", "landing-zone")),
            s3_lakehouse_bucket=str(
                bucket_data.get("s3_lakehouse_bucket", "lakehouse")
            ),
        )
