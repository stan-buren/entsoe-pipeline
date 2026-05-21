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

"""Configuration loader module for the ENTSO-E data pipeline.

This module provides type-safe, immutable configuration objects by parsing
infrastructure YAML files and loading environment parameters.
"""

from dataclasses import dataclass

import yaml

# We import the CONFIG_DIR we registered in entsoe_pipeline earlier!
from entsoe_pipeline.config.paths import CONFIG_DIR


@dataclass(frozen=True)
class PortsConfig:
    """Immutable infrastructure ports configuration.

    Attributes:
        s3_compatible (int): Port for S3-compatible API.
        iceberg_catalog (int): Port for Apache Iceberg REST Catalog.
    """
    s3_compatible: int
    iceberg_catalog: int

    @classmethod
    def from_yaml(cls) -> "PortsConfig":
        """Loads and parses the ports configuration from ports.yml.

        Returns:
            PortsConfig: A type-safe configuration object.

        Raises:
            FileNotFoundError: If ports.yml is missing.
            yaml.YAMLError: If ports.yml contains invalid syntax.
        """
        ports_file = CONFIG_DIR / "ports.yml"

        with ports_file.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        ports_data = data.get("ports", {})

        # Enforce type casting and fallback values
        return cls(
            s3_compatible=int(ports_data.get("s3_compatible", 8333)),
            iceberg_catalog=int(ports_data.get("iceberg_catalog", 8181)),
        )

