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

"""Immutable AWS region configuration core module."""

from __future__ import annotations

from dataclasses import dataclass

import yaml


@dataclass(frozen=True)
class RegionConfig:
    """Immutable AWS region configuration.

    Attributes:
        aws_region (str): The target AWS region name (e.g., 'us-east-1').
    """

    aws_region: str

    @classmethod
    def _from_yaml(cls) -> RegionConfig:
        """Loads and parses the AWS region configuration from region.yml.

        Returns:
            RegionConfig: The loaded AWS region configuration.
        """
        from entsoe_pipeline.config.paths import CONFIG_DIR

        region_file = CONFIG_DIR / "region.yml"

        with region_file.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        region_data = data.get("region", {})

        return cls(
            aws_region=str(region_data.get("aws_region", "us-east-1")),
        )
