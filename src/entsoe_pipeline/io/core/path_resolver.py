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

"""Low-level schema contract path matching and resolution."""

from __future__ import annotations

import logging

from typing import Any

logger = logging.getLogger("entsoe_pipeline.io.core.path_resolver")


def resolve_target_mappings(
    env_name: str,
    active_folders: dict[str, Any],
    schema_folders: list[str],
) -> list[dict[str, Any]]:
    """Resolves matching target directory paths from the schema contract.

    Args:
        env_name: Target environment name.
        active_folders: Dictionary of active folders extracted from checklist.
        schema_folders: List of directory paths in the schema contract.

    Returns:
        list[dict[str, Any]]: List of resolved schema path mappings.
    """
    env_lower = env_name.lower()
    target_mappings = []

    for path in schema_folders:
        segments = path.split("/")
        if not segments or segments[0] != env_lower:
            continue

        for active_folder, val in active_folders.items():
            if active_folder in segments:
                top_level = segments[1]
                rel_path = "/".join(segments[2:])
                target_mappings.append(
                    {
                        "schema_path": path,
                        "active_folder": active_folder,
                        "top_level_folder": top_level,
                        "remote_folder_path": rel_path,
                        "val": val,
                    }
                )
                break

    return target_mappings
