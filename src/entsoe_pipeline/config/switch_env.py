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

"""Module for dynamically switching active environment configurations.

This module provides a utility to update the active environment configuration
value (e.g., to PROD or IOP) in the environment.yml configuration file
while preserving comments and file structure.
"""

import re
import sys

from entsoe_pipeline import CONFIG_DIR


def switch_environment(target_env: str) -> None:
    """Updates the active environment setting in the environment YAML file.

    Args:
        target_env: The target environment name, strictly 'PROD' or 'IOP'.

    Raises:
        FileNotFoundError: If the environment configuration file does not exist.
    """
    config_file = CONFIG_DIR / "enviroment.yml"

    if not config_file.exists():
        raise FileNotFoundError(
            f"Configuration file not found at {config_file}. "
            "Please initialize configs using 'just init-config' first."
        )

    content = config_file.read_text(encoding="utf-8")

    # Replaces the active_environment value while keeping YAML comments intact.
    new_content = re.sub(
        r"^(active_environment:\s*[\"']?)\w+([\"']?)",
        rf"\g<1>{target_env}\g<2>",
        content,
        flags=re.MULTILINE,
    )

    config_file.write_text(new_content, encoding="utf-8")
    print(f"[ENV] Successfully switched active environment to {target_env}.")


def main() -> None:
    """Parses command-line arguments and triggers environment switching."""
    if len(sys.argv) < 2:
        print("Usage: python switch_env.py <ENVIRONMENT>")
        sys.exit(1)

    target = sys.argv[1].upper()
    if target not in {"PROD", "IOP"}:
        print(f"Error: Unsupported environment '{target}'. Must be PROD or IOP.")
        sys.exit(1)

    try:
        switch_environment(target)
    except FileNotFoundError as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
