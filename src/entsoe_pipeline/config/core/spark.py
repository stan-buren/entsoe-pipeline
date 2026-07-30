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

"""Immutable Spark Connect configuration core module."""

from __future__ import annotations

from dataclasses import dataclass

import yaml


@dataclass(frozen=True)
class SparkConfig:
    """Immutable Spark execution backend configuration.

    Attributes:
        mode (str): Execution mode — currently always ``"connect"``.
        connect_server (str): Spark Connect gRPC endpoint in
            ``sc://{host}:{port}`` format.
    """

    mode: str
    connect_server: str

    @classmethod
    def _from_yaml(cls) -> SparkConfig:
        """Loads and parses the Spark configuration from spark.yml.

        Returns:
            SparkConfig: The loaded Spark configuration.
        """
        from entsoe_pipeline.config.paths import CONFIG_DIR

        spark_file = CONFIG_DIR / "spark.yml"

        with spark_file.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        spark_data = data.get("spark", {})

        return cls(
            mode=str(spark_data.get("mode", "connect")),
            connect_server=str(spark_data.get("connect_server")),
        )
