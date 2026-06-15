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

"""Low-level active domains configuration parsing."""

from __future__ import annotations

import logging

from typing import Any

logger = logging.getLogger("entsoe_pipeline.io.core.config_parser")


def extract_active_folders(
    env_name: str, config_data: dict[str, Any]
) -> dict[str, Any]:
    """Parses domains configuration to find all active folders for the env.

    Args:
        env_name: Platform environment ('IOP' or 'PROD').
        config_data: Parsed domains configuration dictionary.

    Returns:
        dict[str, Any]: Dictionary mapping active folder names to their values.
    """
    environments = config_data.get("environments", {})
    env_data = environments.get(env_name.upper())
    if not env_data:
        return {}

    active_folders: dict[str, Any] = {}
    root_dirs = env_data.get("root_directories", [])
    for rdir in root_dirs:
        domains = rdir.get("domains", {})
        for folders in domains.values():
            for folder, val in folders.items():
                if val is not False:
                    active_folders[folder] = val

        folders = rdir.get("folders", {})
        for folder, val in folders.items():
            if val is not False:
                active_folders[folder] = val

    return active_folders
