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

"""Symmetry and schema mirror validation tests between configuration folders.

This module implements defensive design verification. It scans the git-ignored
active configuration directory 'config_env' and compares it with the template directory
'config_env_example'. This guarantees that developers never commit private keys but
always keep the public templates structurally aligned, preventing onboarding issues.
"""

from pathlib import Path

import pytest
import yaml


def get_dict_keys_recursive(d: dict, prefix: str = "") -> set[str]:
    """Recursively extract all nested dictionary key paths in dot-notation.

    This utility flattens arbitrary nested YAML schemas into a flat set of
    string addresses (e.g., 'ports.s3_compatible'), enabling precise difference
    computations across active and template configuration configurations.

    Args:
        d: The target dictionary to parse recursively.
        prefix: Accumulator string representing the current nesting depth path.

    Returns:
        A set containing all resolved dot-notation key paths.
    """
    keys = set()
    if not isinstance(d, dict):
        return keys
    for k, v in d.items():
        key_path = f"{prefix}.{k}" if prefix else str(k)
        keys.add(key_path)
        if isinstance(v, dict):
            keys.update(get_dict_keys_recursive(v, key_path))
    return keys


def test_config_mirror_symmetry() -> None:
    """Verify that the set of configuration files and their schemas match exactly.

    This dynamically compares 'config_env/' and 'config_env_example/' to identify
    missing files or mismatched keys, failing early in local pre-commit hooks.
    This ensures that when a developer adds a private parameter to their local config,
    they are forced to document it with an abstract placeholder in the example config.
    """
    # -------------------------------------------------------------------------
    # 1. Resolve paths relative to this test file (tests/test_config_mirror.py)
    # -------------------------------------------------------------------------
    project_root = Path(__file__).resolve().parents[1]
    config_dir = project_root / "config_env"
    example_dir = project_root / "config_env_example"

    # -------------------------------------------------------------------------
    # 2. In CI/CD where 'config_env/' is ignored and not committed, skip the check
    # -------------------------------------------------------------------------
    if not config_dir.exists():
        pytest.skip(
            "Active 'config_env/' directory does not exist. "
            "Skipping mirror verification."
        )

    # -------------------------------------------------------------------------
    # 3. Discover all active configuration files (YAML only)
    # -------------------------------------------------------------------------
    active_files = {
        f.name
        for f in config_dir.iterdir()
        if f.is_file() and f.name.endswith((".yml", ".yaml"))
    }

    # -------------------------------------------------------------------------
    # 4. Discover all template configuration files (YAML only)
    # -------------------------------------------------------------------------
    example_files = {
        f.name
        for f in example_dir.iterdir()
        if f.is_file() and f.name.endswith((".yml", ".yaml"))
    }

    # -------------------------------------------------------------------------
    # 5. Calculate symmetric difference to find discrepancies in file names
    # -------------------------------------------------------------------------
    missing_examples = active_files - example_files
    missing_actives = example_files - active_files

    assert not missing_examples, (
        f"Active configuration files {missing_examples} "
        f"are missing their template counterparts in config_env_example/! "
        f"Please create them so the repository remains portable."
    )

    assert not missing_actives, (
        f"Template files {missing_actives} are present in "
        f"config_env_example/ but missing from your active "
        f"config_env/ directory! "
        f"Please run 'just init-config' or create them manually."
    )

    # -------------------------------------------------------------------------
    # 6. Deep Schema Comparison: Verify YAML structure matches inside each file
    # -------------------------------------------------------------------------
    for filename in active_files:
        active_path = config_dir / filename
        example_path = example_dir / filename

        # Load active YAML
        with active_path.open(encoding="utf-8") as f:
            active_data = yaml.safe_load(f) or {}

        # Load example YAML
        with example_path.open(encoding="utf-8") as f:
            example_data = yaml.safe_load(f) or {}

        active_keys = get_dict_keys_recursive(active_data)
        example_keys = get_dict_keys_recursive(example_data)

        # Exclude metadata documentation blocks from the schema mirroring assertions.
        # The 'metadata' section is unique to example configurations and must not
        # be replicated in actual developer environments.
        example_keys = {
            k
            for k in example_keys
            if not (k == "metadata" or k.startswith("metadata."))
        }

        # Calculate difference between dynamic schemas
        missing_keys = active_keys - example_keys
        extra_keys = example_keys - active_keys

        assert not missing_keys, (
            f"YAML keys {missing_keys} in 'config_env/{filename}' "
            f"are missing from the template counterpart "
            f"'config_env_example/{filename}'! "
            f"Please keep them in sync."
        )

        assert not extra_keys, (
            f"YAML keys {extra_keys} in template "
            f"'config_env_example/{filename}' are missing from "
            f"your active 'config_env/{filename}' file! "
            f"Please update your active configuration."
        )
