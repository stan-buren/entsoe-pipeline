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

"""Immutable lakehouse configuration core module."""

from __future__ import annotations

from dataclasses import dataclass

import yaml


@dataclass(frozen=True)
class LakehouseConfig:
    """Immutable Lakehouse configuration.

    Attributes:
        purge_raw_after_transform (bool): Flag to delete raw CSV files after processing.
    """

    purge_raw_after_transform: bool

    @classmethod
    def _from_yaml(cls) -> LakehouseConfig:
        """Loads and parses the lakehouse configuration from lakehouse.yml.

        Returns:
            LakehouseConfig: The loaded lakehouse configuration.
        """
        from entsoe_pipeline.config.paths import CONFIG_DIR

        lakehouse_file = CONFIG_DIR / "lakehouse.yml"

        if not lakehouse_file.exists():
            return cls(purge_raw_after_transform=False)

        with lakehouse_file.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        lakehouse_data = data.get("lakehouse", {})

        return cls(
            purge_raw_after_transform=bool(
                lakehouse_data.get("purge_raw_after_transform", False)
            )
        )
