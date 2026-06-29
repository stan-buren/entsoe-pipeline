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

"""Immutable infrastructure URLs configuration core module."""

from __future__ import annotations

from dataclasses import dataclass

import yaml


@dataclass(frozen=True)
class UrlsConfig:
    """Immutable infrastructure URLs configuration.

    Attributes:
        kestra (str): The external/public web URL of the Kestra platform.
    """

    kestra: str

    @classmethod
    def _from_yaml(cls) -> UrlsConfig:
        """Loads and parses the URLs configuration from urls.yml.

        Returns:
            UrlsConfig: A type-safe configuration object.

        Raises:
            FileNotFoundError: If urls.yml is missing.
            yaml.YAMLError: If urls.yml contains invalid syntax.
        """
        from entsoe_pipeline.config.paths import CONFIG_DIR

        urls_file = CONFIG_DIR / "urls.yml"

        with urls_file.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        urls_data = data.get("urls", {})

        return cls(
            kestra=str(urls_data.get("kestra", "http://localhost:8082/")),
        )
