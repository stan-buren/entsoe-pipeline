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

"""Automated script to format YAML files using ruamel.yaml.

This script parses and formats YAML configuration files to enforce styling rules
(such as 80-character line limits and standard indentation). It can be run as a
pre-commit hook (receiving modified file paths as arguments) or manually to scan
the whole repository. It only writes updates if formatting discrepancies exist.
"""

import os
import sys

from io import StringIO
from pathlib import Path

from ruamel.yaml import YAML


def main() -> None:
    """Load, format, and save YAML files to enforce styling consistency."""
    # Configure ruamel.yaml styling parameters
    yaml = YAML()
    yaml.width = 80
    # Standard mapping=2, sequence=4, offset=2 indentation pattern
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.preserve_quotes = True

    files_to_format = []

    # If filenames are passed as arguments, process only those files
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            p = Path(arg)
            if p.suffix in (".yml", ".yaml") and p.is_file():
                files_to_format.append(p)
    else:
        # Perform a fast manual scan, skipping large directories at walk level
        for root, dirs, files in os.walk("."):
            dirs[:] = [
                d
                for d in dirs
                if d
                not in (
                    ".venv",
                    ".git",
                    ".cache",
                    "artifacts",
                    "brain",
                )
            ]
            for file in files:
                if file.endswith((".yml", ".yaml")):
                    files_to_format.append(Path(root) / file)

    modified_files = []

    for filepath in files_to_format:
        try:
            # Read current content
            with open(filepath, encoding="utf-8") as f:
                original_content = f.read()

            # Parse and dump to a string buffer to check if layout changes
            data = yaml.load(original_content)
            buffer = StringIO()
            yaml.dump(data, buffer)
            formatted_content = buffer.getvalue()

            # If formatting differs, write back and record modification
            if original_content != formatted_content:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(formatted_content)
                modified_files.append(filepath)
                print(f"Reformatted: {filepath}")

        except Exception as e:
            # Report structural syntax errors but do not fail the entire process
            print(
                f"Warning: Failed to format {filepath} due to error: {e}",
                file=sys.stderr,
            )

    if modified_files:
        print(
            f"\nFormatted {len(modified_files)} YAML files. "
            "Please review and stage changes."
        )
        sys.exit(1)
    else:
        print("All target YAML files are correctly formatted.")
        sys.exit(0)


if __name__ == "__main__":
    main()
