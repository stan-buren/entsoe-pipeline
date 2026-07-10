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

"""Immutable infrastructure hosts configuration core module."""

from __future__ import annotations

from dataclasses import dataclass

import yaml


@dataclass(frozen=True)
class HostsConfig:
    """Immutable infrastructure hosts configuration.

    Attributes:
        seaweedfs (str): IP address or domain name of the SeaweedFS storage server.
        iceberg_catalog (str): IP address or domain name of the Iceberg REST Catalog.
        database (str): IP address or domain name of the PostgreSQL metadata database server.
    """

    seaweedfs: str
    iceberg_catalog: str
    database: str

    @classmethod
    def _from_yaml(cls) -> HostsConfig:
        """Loads and parses the hosts configuration from hosts.yml.

        Returns:
            HostsConfig: A type-safe configuration object.

        Raises:
            FileNotFoundError: If hosts.yml is missing.
            yaml.YAMLError: If hosts.yml contains invalid syntax.
        """
        from entsoe_pipeline.config.paths import CONFIG_DIR

        hosts_file = CONFIG_DIR / "hosts.yml"

        with hosts_file.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        hosts_data = data.get("hosts", {})

        return cls(
            seaweedfs=str(hosts_data.get("seaweedfs", "localhost")),
            iceberg_catalog=str(hosts_data.get("iceberg_catalog", "localhost")),
            database=str(hosts_data.get("database", "localhost")),
        )
