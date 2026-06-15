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

"""Project root lookup implementation core module."""

from __future__ import annotations

import os

from pathlib import Path


def find_project_root() -> Path:
    """Locates the project root directory deterministically.

    This function resolves the project's root folder utilizing a three-tier
    fallback strategy: environment variable prioritization, search for a
    custom marker file, and a static parent lookup as a last resort.

    Returns:
        Path: The resolved absolute path to the project root directory.
    """
    # Tier 1: Production priority (Environment Variable).
    # If executing inside Docker/Airflow, take the pre-configured root directly.
    if env_root := os.getenv("PROJECT_ROOT"):
        return Path(env_root)

    # Tier 2: Repository marker lookup (.project_root).
    # Resolves upwards from the location of this file to trace active directories.
    current_file = Path(__file__).resolve()
    for parent in current_file.parents:
        if (parent / ".project_root").exists():
            return parent

    # Tier 3: Static fallback calculation.
    # Since this module resides in 'src/entsoe_pipeline/config/core/project_root.py',
    # its great-great-great-grandparent (parents[4]) is guaranteed to be the project root.
    return current_file.parents[4]
