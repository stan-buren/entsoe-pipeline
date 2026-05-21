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

"""Script to automatically apply the Apache 2.0 license header to Python files.

This maintenance script walks recursively through the project workspace, identifies
all Python files (.py), filters out directories such as virtual environments (.venv),
caches, and git internal metadata, and adds the standard Apache 2.0 license header.
It is idempotent (won't duplicate headers) and respects shebang lines by inserting
the license header immediately after the shebang.
"""

import sys
import tempfile

from pathlib import Path

# Centralized path resolution from the package core
from entsoe_pipeline import PROJECT_ROOT

# Standard Apache 2.0 Short Boilerplate with Custom Copyright
LICENSE_HEADER = """# Copyright 2026 Stanislav Burundukov
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
"""

# Signature string to identify if the file is already licensed
LICENSE_SIGNATURE = "Licensed under the Apache License, Version 2.0"

# Outdated signature to identify if a file needs its copyright updated
OLD_COPYRIGHT_LINE = (
    "# Copyright 2026 The Learning Python Authors. All Rights Reserved."
)
NEW_COPYRIGHT_LINE = "# Copyright 2026 Stanislav Burundukov"

# Directories to exclude from the license check
EXCLUDED_DIRS = {
    ".venv",
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".htmlcov",
    "build",
    "dist",
}


def apply_license_to_file(file_path: Path) -> bool:
    """Prepend the Apache 2.0 license header to a Python file.

    It preserves any leading shebang line (e.g., `#!/usr/bin/env python3`) as the
    very first line, inserts the license block right after it, and avoids duplicate
    applications by searching for the license signature. It also updates outdated
    copyright notices if found. It performs the update atomically using a temporary
    file in the same directory.

    Args:
        file_path: Absolute path to the python target file.

    Returns:
        True if the license was added or modified; False if it was skipped or unchanged.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"⚠️ Error reading {file_path}: {e}")
        return False

    # -------------------------------------------------------------------------
    # 1. Update Existing Outdated Copyright Notices
    # -------------------------------------------------------------------------
    if OLD_COPYRIGHT_LINE in content:
        # Safely substitute the old copyright line with the new owner
        new_content = content.replace(OLD_COPYRIGHT_LINE, NEW_COPYRIGHT_LINE)
        return write_atomically(file_path, new_content)

    # -------------------------------------------------------------------------
    # 2. Skip Already Licensed Files
    # -------------------------------------------------------------------------
    if LICENSE_SIGNATURE in content:
        return False

    lines = content.splitlines(keepends=True)

    # -------------------------------------------------------------------------
    # 3. Parse Shebang & Construct Modified Content
    # -------------------------------------------------------------------------
    has_shebang = len(lines) > 0 and lines[0].startswith("#!")

    new_content_parts = []
    if has_shebang:
        new_content_parts.append(lines[0])
        # Ensure a blank line separating shebang from license
        if len(lines) > 1 and lines[1].strip() != "":
            new_content_parts.append("\n")

        new_content_parts.append(LICENSE_HEADER)
        new_content_parts.append("\n")
        new_content_parts.extend(lines[1:])
    else:
        new_content_parts.append(LICENSE_HEADER)
        new_content_parts.append("\n")
        new_content_parts.extend(lines)

    return write_atomically(file_path, "".join(new_content_parts))


def write_atomically(file_path: Path, content: str) -> bool:
    """Safely write content to the target file utilizing a temporary file buffer.

    Args:
        file_path: Absolute path to the python target file.
        content: The exact text content to write.

    Returns:
        True if the write succeeded, False otherwise.
    """
    dir_path = file_path.parent
    try:
        with tempfile.NamedTemporaryFile(
            "w", dir=dir_path, delete=False, encoding="utf-8"
        ) as temp_file:
            temp_file.write(content)
            temp_path = Path(temp_file.name)
        # Replace the original file atomically
        temp_path.replace(file_path)
    except Exception as e:
        print(f"❌ Failed to write to {file_path}: {e}")
        if "temp_path" in locals() and temp_path.exists():
            temp_path.unlink()
        return False
    else:
        return True


def should_skip(path: Path) -> bool:
    """Determine if a directory path should be skipped during recursive traversal.

    Args:
        path: A Path directory to evaluate.

    Returns:
        True if the path or any of its ancestors belong to excluded folders.
    """
    return any(part in EXCLUDED_DIRS for part in path.parts)


def main() -> None:
    """Traverse workspace recursively and apply licenses to all Python scripts."""
    # Leverage the centralized project root from the pipeline library
    workspace_root = PROJECT_ROOT
    print(f"🚀 Initializing workspace license audit in: {workspace_root}")

    python_files = [
        path for path in workspace_root.rglob("*.py") if not should_skip(path)
    ]

    print(
        f"🔍 Discovered {len(python_files)} active Python source files "
        f"(skipping caches & envs)."
    )

    applied_count = 0
    skipped_count = 0

    for file_path in sorted(python_files):
        # Skip this license script itself to prevent self-modification loops
        if file_path == Path(__file__).resolve():
            continue

        relative_path = file_path.relative_to(workspace_root)
        if apply_license_to_file(file_path):
            print(f"✅ Applied license to: {relative_path}")
            applied_count += 1
        else:
            skipped_count += 1

    print("\n" + "=" * 60)
    print("🎓 LICENSE AUDIT COMPLETE:")
    print(f"   - Total files analyzed: {len(python_files)}")
    print(f"   - Newly licensed:       {applied_count}")
    print(f"   - Already licensed:     {skipped_count}")
    print("=" * 60)

    # -------------------------------------------------------------------------
    # UNIX Exit Protocol: Exit with 1 if files were modified
    # -------------------------------------------------------------------------
    if applied_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
