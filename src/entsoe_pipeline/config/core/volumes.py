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

"""Immutable storage volume configuration core module."""

from __future__ import annotations

from dataclasses import dataclass

import yaml


@dataclass(frozen=True)
class VolumesConfig:
    """Immutable storage volume configuration.

    Attributes:
        s3_compatible (str): Physical directory path on the host for local storage.
    """

    s3_compatible: str

    @classmethod
    def _from_yaml(cls) -> VolumesConfig:
        """Loads and parses the volume configuration from volumes.yml.

        Returns:
            VolumesConfig: The loaded volumes configuration.
        """
        from entsoe_pipeline.config.paths import CONFIG_DIR

        volumes_file = CONFIG_DIR / "volumes.yml"

        with volumes_file.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        volumes_data = data.get("volumes", {})

        return cls(
            s3_compatible=str(volumes_data.get("s3_compatible", ".data/seaweed")),
        )
