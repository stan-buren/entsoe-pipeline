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

"""YAML Metadata Observability and Serialization Facade."""

from __future__ import annotations

import sys

from pathlib import Path
from typing import Any

import yaml

from entsoe_pipeline.config.paths import PROJECT_ROOT
from entsoe_pipeline.logger.core.generated_at import get_generated_at_timestamp
from entsoe_pipeline.logger.core.warning import (
    get_my_entsoe_domains_warning,
    get_yaml_warning,
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


def save_yaml_with_observability(
    output_path: Path,
    payload: Any,
    generator_script_name: str | None = None,
    is_my_entsoe_domains: bool = False,
) -> None:
    """Serializes a payload to YAML with warning comments and execution timestamp.

    Args:
        output_path: Target filesystem Path to write.
        payload: Structured payload (normally a dictionary).
        generator_script_name: The name/path of the generating script.
          If None, resolves relative to PROJECT_ROOT using sys.argv[0].
        is_my_entsoe_domains: Whether this is my_entsoe_domains configuration.
    """
    # 1. Resolve generator script name
    if not generator_script_name:
        main_script = Path(sys.argv[0]).resolve()
        try:
            generator_script_name = str(main_script.relative_to(PROJECT_ROOT))
        except ValueError:
            generator_script_name = main_script.name

    # 2. Inject generated_at timestamp at the top of mapping payload
    if isinstance(payload, dict):
        ordered_payload = {"generated_at": get_generated_at_timestamp()}
        for k, v in payload.items():
            if k != "generated_at":
                ordered_payload[k] = v
        payload = ordered_payload

    # 3. Resolve warning header
    if is_my_entsoe_domains:
        warning_header = get_my_entsoe_domains_warning(generator_script_name)
    else:
        warning_header = get_yaml_warning(generator_script_name)

    # 4. Serialize using the block-indented sequence dumper
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        f.write(warning_header)
        yaml.dump(
            payload,
            f,
            Dumper=IndentedSafeDumper,
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
            indent=2,
        )
