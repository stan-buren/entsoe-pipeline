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

"""Immutable Iceberg namespace configuration core module."""

from __future__ import annotations

from dataclasses import dataclass

import yaml


@dataclass(frozen=True)
class NamespacesConfig:
    """Immutable Iceberg namespace configuration.

    Attributes:
        staging (str): The namespace name for the staging (Silver) layer
            within the Iceberg table bucket.
    """

    staging: str

    @classmethod
    def _from_yaml(cls) -> NamespacesConfig:
        """Loads and parses the namespaces configuration from namespaces.yml.

        Returns:
            NamespacesConfig: The loaded namespaces configuration.
        """
        from entsoe_pipeline.config.paths import CONFIG_DIR

        ns_file = CONFIG_DIR / "namespaces.yml"

        with ns_file.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        ns_data = data.get("namespaces", {})

        return cls(
            staging=str(ns_data.get("staging", "db")),
        )
