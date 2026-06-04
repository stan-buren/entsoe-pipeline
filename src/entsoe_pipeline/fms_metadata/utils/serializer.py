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

Provides custom dumpers and serialization helpers to write block-indented YAML
catalogs smoothly to disk.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from entsoe_pipeline.fms_metadata.core.generation_data import (
    get_generation_timestamp,
)


class IndentedSafeDumper(yaml.SafeDumper):
    """Custom YAML SafeDumper that forces indentation for sequence (list) items.

    Ensures list sequence items (prefixed by '-') are aligned and indented
    relative to their parent mapping keys to match IDE standard formatting.
    """

    def increase_indent(
        self,
        flow: bool = False,
        indentless: bool = False,  # noqa: ARG002
    ) -> Any:
        """Forces sequence indentation by overriding indentless settings."""
        return super().increase_indent(flow, indentless=False)


def save_yaml_catalog(
    output_path: Path,
    payload: Any,
) -> None:
    """Serializes any structured payload into an indented YAML catalog file.

    Forces clean sequence indentation aligning with IDE formats.

    Args:
        output_path: Target filesystem Path to write.
        payload: Structured Python dictionary or list to serialize.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        yaml.dump(
            payload,
            f,
            Dumper=IndentedSafeDumper,
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
            indent=2,
        )


def save_fms_catalog(
    output_path: Path,
    api_requests_count: int,
    folders_metadata: dict[str, Any],
) -> None:
    """Serializes compiled folders metadata catalog into an indented YAML file.

    Generates the current ISO UTC execution timestamp and writes the payload
    gracefully to disk.

    Args:
        output_path: Target Path to write the YAML file.
        api_requests_count: Total API calls executed during the crawl.
        folders_metadata: Mapping of folder_name -> compiled folder metadata.
    """
    current_time_utc = get_generation_timestamp()
    payload = {
        "generated_at": current_time_utc,
        "total_api_requests": api_requests_count,
        "folders": folders_metadata,
    }
    save_yaml_catalog(output_path, payload)
