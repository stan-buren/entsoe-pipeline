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

"""Automated pre-commit script to scan for dead code patterns.

This script enforces clean repository structure and code hygiene. It walks
through the workspace to identify obsolete files (e.g., backups, temporary assets),
empty directories that should be pruned, test filename naming collisions in different
subdirectories, and potential dead import clutter inside module initialization
files (__init__.py).
"""

import fnmatch
import os
import sys

from pathlib import Path

from entsoe_pipeline import PROJECT_ROOT


def main() -> None:
    """Scan the workspace directories for obsolete, dead, or messy code patterns."""
    project_root = PROJECT_ROOT
    issues = []

    print("🔍 Scanning for dead code patterns...")

    # -------------------------------------------------------------------------
    # 1 & 2. Scanning for obsolete/backup and temporary files
    # -------------------------------------------------------------------------
    dead_patterns = [
        "*_old.py",
        "*_fixed.py",
        "*_backup.py",
        "*_test_old.py",
        "*_deprecated.py",
    ]
    temp_patterns = ["*.tmp", "*.temp", "*~", "*.bak", ".DS_Store"]
    ignored_dirs = {".venv", ".git", "__pycache__"}

    for dirpath, dirnames, filenames in os.walk(project_root):
        dirnames[:] = [d for d in dirnames if d not in ignored_dirs]
        rel_dir = Path(dirpath).relative_to(project_root)

        for filename in filenames:
            if any(fnmatch.fnmatch(filename, p) for p in dead_patterns):
                issues.append(f"Dead file: {rel_dir / filename}")
            elif any(fnmatch.fnmatch(filename, p) for p in temp_patterns):
                issues.append(f"Temporary file: {rel_dir / filename}")

    # -------------------------------------------------------------------------
    # 3. Scanning for empty folders that should be pruned from git indexes
    # -------------------------------------------------------------------------
    known_empty = {".git", "__pycache__", ".venv", ".pytest_cache", ".coverage"}
    for dirpath, dirnames, filenames in os.walk(project_root):
        rel_path = Path(dirpath).relative_to(project_root)

        # Ignore standard hidden or package environment folders
        if any(part in known_empty or part.startswith(".") for part in rel_path.parts):
            continue

        # Check if folder contains no files and no subfolders containing files
        if not filenames and not any(
            Path(dirpath, d).iterdir() for d in dirnames if not d.startswith(".")
        ):
            issues.append(f"Empty directory: {rel_path}")

    # -------------------------------------------------------------------------
    # 4. Checking for duplicate test stems in different folders
    # -------------------------------------------------------------------------
    test_files = {}
    for test_file in (project_root / "tests").rglob("test_*.py"):
        if "__pycache__" not in str(test_file):
            base_name = test_file.stem
            if base_name in test_files:
                rel_a = test_file.relative_to(project_root)
                rel_b = test_files[base_name].relative_to(project_root)
                issues.append(f"Potential duplicate test: {rel_a} vs {rel_b}")
            else:
                test_files[base_name] = test_file

    # -------------------------------------------------------------------------
    # 5. Scanning package __init__.py files for complex or cluttered import blocks
    # -------------------------------------------------------------------------
    for init_file in project_root.rglob("__init__.py"):
        if ".venv" not in str(init_file):
            try:
                with init_file.open(encoding="utf-8") as f:
                    content = f.read().strip()
                    if not content:
                        continue

                    # Filter out leading license comments and empty lines.
                    lines = content.splitlines()
                    non_comment_lines = []
                    for line in lines:
                        stripped = line.strip()
                        if stripped and not stripped.startswith("#"):
                            non_comment_lines.append(stripped)

                    # Verify if the first meaningful line contains a docstring.
                    # Verify if the first meaningful line contains a docstring.
                    if non_comment_lines:
                        first_meaningful = non_comment_lines[0]
                        has_docstring = first_meaningful.startswith(('"""', "'''"))

                        # Flag complex initialization files that lack clear docstrings.
                        if (
                            not has_docstring
                            and "import " in content
                            and len(lines) > 5
                        ):
                            rel_path = init_file.relative_to(project_root)
                            issues.append(
                                f"Complex __init__.py (potential dead "
                                f"imports): {rel_path}"
                            )

            except (UnicodeDecodeError, FileNotFoundError):  # noqa: S110
                pass

    # -------------------------------------------------------------------------
    # 6. Formatting & Reporting scanner outcome
    # -------------------------------------------------------------------------
    if issues:
        print("\n❌ Dead code found:")
        print("=" * 50)
        for issue in sorted(issues):
            print(f"  • {issue}")
        print("=" * 50)
        print(f"Total issues: {len(issues)}")
        print("\n💡 Cleanup suggestions:")
        print("  • Remove dead test files")
        print("  • Remove empty directories")
        print("  • Consolidate duplicate tests")
        sys.exit(1)
    else:
        print("✅ No dead code found!")
        sys.exit(0)


if __name__ == "__main__":
    main()
