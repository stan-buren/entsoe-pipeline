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

"""Serializer module for ENTSO-E FMS Metadata catalogs.

Provides custom serialization routing to write YAML catalogs with observability to disk.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from entsoe_pipeline.logger import save_yaml_with_observability


def save_yaml_catalog(
    output_path: Path,
    payload: Any,
) -> None:
    """Serializes any structured payload into an indented YAML catalog file.

    Forces clean sequence indentation and injects observability headers.

    Args:
        output_path: Target filesystem Path to write.
        payload: Structured Python dictionary or list to serialize.
    """
    save_yaml_with_observability(output_path, payload)


def save_fms_catalog(
    output_path: Path,
    api_requests_count: int,
    folders_metadata: dict[str, Any],
) -> None:
    """Serializes compiled folders metadata catalog into an indented YAML file.

    Forces clean sequence indentation and adds standard generated timestamp.

    Args:
        output_path: Target Path to write the YAML file.
        api_requests_count: Total API calls executed during the crawl.
        folders_metadata: Mapping of folder_name -> compiled folder metadata.
    """
    payload = {
        "total_api_requests": api_requests_count,
        "folders": folders_metadata,
    }
    save_yaml_catalog(output_path, payload)
