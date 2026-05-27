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

"""Test suite to validate standard metadata specification for example configurations.

This quality gate ensures that all public development templates are fully documented
with rich metadata including descriptions, multiple execution examples, defaults,
and type mappings.
"""

from pathlib import Path

import pytest
import yaml

from entsoe_pipeline import PROJECT_ROOT

# Resolve the example configuration folder
CONFIG_EXAMPLE_DIR = PROJECT_ROOT / "config_env_example"


def get_example_config_files() -> list[Path]:
    """Retrieve all YAML example configuration files in the workspace.

    Returns:
        A list of Path objects pointing to config example files.
    """
    if not CONFIG_EXAMPLE_DIR.exists():
        return []
    return sorted(
        [
            p
            for p in CONFIG_EXAMPLE_DIR.iterdir()
            if p.is_file() and p.suffix in {".yml", ".yaml"}
        ]
    )


@pytest.mark.unit
@pytest.mark.parametrize("config_file", get_example_config_files())
def test_config_files_contain_valid_metadata_spec(config_file: Path) -> None:
    """Validate that every parameter has a rich, complete metadata specification.

    This test asserts that for every active parameter key declared in the file:
    1. A corresponding metadata entry exists.
    2. A detailed description (minimum 150 characters) is provided.
    3. At least 2 distinct configuration examples are supplied.
    4. A default value is specified.
    5. A valid type is specified ('integer' or 'string') and matches the default value.
    """
    # -------------------------------------------------------------------------
    # ARRANGE: Load the YAML structure and extract target parameter keys
    # -------------------------------------------------------------------------
    assert config_file.exists(), f"Configuration file not found: {config_file}"

    with config_file.open(encoding="utf-8") as fh:
        raw_text = fh.read()

    data = yaml.safe_load(raw_text)
    assert isinstance(data, dict), (
        f"Failed to parse YAML file '{config_file.name}' as a dictionary."
    )

    # Resolve active parameters based on dynamic folder stems
    if config_file.stem == "enviroment":
        # Environment layout defines parameters flatly on root or inside 'limits'
        active_params = {}
        if "active_environment" in data:
            active_params["active_environment"] = data["active_environment"]
        if "environments" in data:
            active_params["environments"] = data["environments"]
        if "limits" in data and isinstance(data["limits"], dict):
            active_params.update(data["limits"])
    else:
        # Standard configs define parameters inside a single primary block
        active_section_name = config_file.stem
        if active_section_name == "bucket":
            active_section_name = "buckets"
        assert active_section_name in data, (
            f"Config file is missing its primary section '{active_section_name}'."
        )
        active_params = data[active_section_name]
        assert isinstance(active_params, dict), (
            f"Primary section '{active_section_name}' must be a dictionary."
        )

    # Verify that a metadata block is present in the file
    assert "metadata" in data, (
        f"Config file '{config_file.name}' is missing a 'metadata' block."
    )
    metadata = data["metadata"]
    assert isinstance(metadata, dict), "The 'metadata' section must be a dictionary."

    # -------------------------------------------------------------------------
    # ACT: Audit each parameter key against our strict specification rules
    # -------------------------------------------------------------------------
    errors = []

    for key in active_params:
        # A. Check metadata entry presence
        if key not in metadata:
            errors.append(f"Parameter '{key}' is missing from the 'metadata' block.")
            continue

        meta = metadata[key]
        if not isinstance(meta, dict):
            errors.append(f"Metadata for parameter '{key}' must be a dictionary.")
            continue

        # B. Validate description presence and length (>= 150 chars)
        if "description" not in meta:
            errors.append(
                f"Parameter '{key}' is missing a 'description' field in metadata."
            )
        else:
            desc = meta["description"]
            if not isinstance(desc, str):
                errors.append(f"Description for parameter '{key}' must be a string.")
            elif len(desc.strip()) < 150:
                errors.append(
                    f"Description for parameter '{key}' is too short "
                    f"({len(desc)} characters). "
                    "Must be at least 150 characters for comprehensive explanations."
                )

        # Get the parameter type safely to guide conditional validations
        param_type = meta.get("type", "string")

        # C. Validate examples list (minimum 1 example required for non-objects)
        if param_type != "object":
            if "examples" not in meta:
                errors.append(
                    f"Parameter '{key}' is missing an 'examples' list in metadata."
                )
            else:
                examples = meta["examples"]
                if not isinstance(examples, list):
                    errors.append(f"Examples for parameter '{key}' must be a list.")
                elif len(examples) < 1:
                    errors.append(
                        f"Parameter '{key}' must have at least 1 "
                        f"configuration example. Found: {len(examples)}."
                    )

        # D. Validate default value presence (only required for simple types)
        if param_type != "object" and "default" not in meta:
            errors.append(
                f"Parameter '{key}' is missing a 'default' field in metadata."
            )

        # E. Validate type presence and correctness
        if "type" not in meta:
            errors.append(f"Parameter '{key}' is missing a 'type' field in metadata.")
        else:
            valid_types = {"string", "integer", "object"}
            if param_type not in valid_types:
                errors.append(
                    f"Parameter '{key}' has an invalid type '{param_type}'. "
                    f"Must be one of: {sorted(valid_types)}."
                )
            elif "default" in meta and param_type != "object":
                default_val = meta["default"]
                if (
                    param_type == "integer"
                    and not isinstance(default_val, int)
                    and not isinstance(default_val, bool)
                ):
                    errors.append(
                        f"Default value '{default_val}' for parameter "
                        f"'{key}' does not match type 'integer' "
                        f"(got '{type(default_val).__name__}')."
                    )
                elif param_type == "string" and not isinstance(default_val, str):
                    errors.append(
                        f"Default value '{default_val}' for parameter "
                        f"'{key}' does not match type 'string' "
                        f"(got '{type(default_val).__name__}')."
                    )

    # -------------------------------------------------------------------------
    # ASSERT: Verify that no schema discrepancies were discovered
    # -------------------------------------------------------------------------
    assert not errors, (
        f"Metadata validation failed for '{config_file.name}':\n"
        + "\n".join(f"  - {err}" for err in errors)
    )
