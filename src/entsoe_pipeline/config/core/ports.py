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

"""Immutable infrastructure ports configuration core module."""

from __future__ import annotations

from dataclasses import dataclass

import yaml


@dataclass(frozen=True)
class PortsConfig:
    """Immutable infrastructure ports configuration.

    Attributes:
        s3_compatible (int): Port for S3-compatible API.
        iceberg_catalog (int): Port for Apache Iceberg REST Catalog.
        master_http (int): Port for the SeaweedFS Master HTTP Admin UI.
        master_grpc (int): Port for the SeaweedFS Master gRPC communications.
        volume_http (int): Port for the SeaweedFS Volume Server HTTP API.
        filer_http (int): Port for the SeaweedFS Filer HTTP browser interface.
        filer_grpc (int): Port for the SeaweedFS Filer gRPC metadata service.
        kestra_web (int): Port for the Kestra Web UI administration dashboard.
        kestra_api (int): Port for the Kestra API backend services.
        database (int): Port for the PostgreSQL database metadata storage.
    """

    s3_compatible: int
    iceberg_catalog: int
    master_http: int
    master_grpc: int
    volume_http: int
    filer_http: int
    filer_grpc: int
    kestra_web: int
    kestra_api: int
    database: int

    @classmethod
    def _from_yaml(cls) -> PortsConfig:
        """Loads and parses the ports configuration from ports.yml.

        Returns:
            PortsConfig: A type-safe configuration object.

        Raises:
            FileNotFoundError: If ports.yml is missing.
            yaml.YAMLError: If ports.yml contains invalid syntax.
        """
        from entsoe_pipeline.config.paths import CONFIG_DIR

        ports_file = CONFIG_DIR / "ports.yml"

        with ports_file.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        ports_data = data.get("ports", {})

        return cls(
            s3_compatible=int(ports_data.get("s3_compatible", 8333)),
            iceberg_catalog=int(ports_data.get("iceberg_catalog", 8181)),
            master_http=int(ports_data.get("master_http", 9333)),
            master_grpc=int(ports_data.get("master_grpc", 19333)),
            volume_http=int(ports_data.get("volume_http", 8080)),
            filer_http=int(ports_data.get("filer_http", 8888)),
            filer_grpc=int(ports_data.get("filer_grpc", 18888)),
            kestra_web=int(ports_data.get("kestra_web", 8082)),
            kestra_api=int(ports_data.get("kestra_api", 8083)),
            database=int(ports_data.get("database", 5432)),
        )
