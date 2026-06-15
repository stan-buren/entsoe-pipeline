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

"""Immutable custom active mode configuration core module."""

from __future__ import annotations

from dataclasses import dataclass

import yaml


@dataclass(frozen=True)
class CustomConfig:
    """Immutable custom configuration.

    Attributes:
        active_mode (str): Active domains config mode (e.g. 'Default', 'Custom',
          'Example').
        config_name (str | None): Specific configuration name.
    """

    active_mode: str
    config_name: str | None = None

    @classmethod
    def _from_yaml(cls) -> CustomConfig:
        """Loads and parses the active mode configuration from my_entsoe_domains.yml.

        Returns:
            CustomConfig: The loaded custom configuration.
        """
        from entsoe_pipeline.config.paths import (
            MY_ENTSOE_DOMAINS_ENV_YML,
        )

        if not MY_ENTSOE_DOMAINS_ENV_YML.exists():
            raise FileNotFoundError(
                f"Custom domains configuration file not found at: "
                f"{MY_ENTSOE_DOMAINS_ENV_YML}"
            )

        with MY_ENTSOE_DOMAINS_ENV_YML.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        active_mode = str(data.get("active_mode", "Default"))
        config_name = data.get("config_name")
        if config_name is not None:
            config_name = str(config_name)

        return cls(active_mode=active_mode, config_name=config_name)
