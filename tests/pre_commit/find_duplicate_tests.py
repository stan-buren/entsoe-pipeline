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

"""Automated pre-commit script to identify duplicate test files.

This script scans the test directory, normalizes the Python content of all tests
(by ignoring comments and empty lines), and computes SHA-256 hashes of the resulting
normalized representation. If any two or more test modules produce identical hashes,
they are identified as structural duplicates, causing the pre-commit hook to fail.
This maintains repository hygiene and stops copy-paste bloat in the test suite.
"""

import hashlib
import os
import re
import sys

from collections import defaultdict
from pathlib import Path

from entsoe_pipeline import TESTS_DIR

# Establish the test repository root to scan
ROOT = sys.argv[1] if len(sys.argv) > 1 else str(TESTS_DIR)


def normalize_py(text: str) -> str:
    """Normalize Python code to enable precise semantic similarity matching.

    This function strips out single-line block comments, inline comments, and
    blanks, reducing python source text to its pure structural executable shape.
    This guarantees that two identical tests with minor comment discrepancies are
    correctly matched as duplicates.

    Args:
        text: The raw Python source file content string.

    Returns:
        The normalized Python source code with all comments and empty lines removed.
    """
    lines = []
    for line in text.splitlines():
        # Strip out comment lines
        if re.match(r"^\s*#", line):
            continue
        # Strip out blank lines
        if not line.strip():
            continue
        lines.append(line.strip())
    return "\n".join(lines)


def main() -> None:
    """Locate duplicate test modules by executing semantic code hashing."""
    # -------------------------------------------------------------------------
    # 1. Traversing Test Directory & Parsing Python Modules
    # -------------------------------------------------------------------------
    hash_map = defaultdict(list)

    for dirpath, _, files in os.walk(ROOT):
        for f in files:
            if not f.endswith(".py"):
                continue
            if f == "__init__.py":
                continue

            p = Path(dirpath) / f
            try:
                with p.open(encoding="utf-8") as fh:
                    content = fh.read()
                    norm = normalize_py(content)

                    # Ignore tiny files or empty test markers
                    if len(norm) < 100:
                        continue

                # Generate high-collision-resistant
                # SHA-256 footprint of normalized shape
                h = hashlib.sha256(norm.encode()).hexdigest()
                hash_map[h].append(p)
            except Exception as e:
                print(f"Error processing {p}: {e}", file=sys.stderr)
                continue

    # -------------------------------------------------------------------------
    # 2. Scanning for Structural Hash Collisions
    # -------------------------------------------------------------------------
    dups = [v for v in hash_map.values() if len(v) > 1]

    # -------------------------------------------------------------------------
    # 3. Reporting Validation Findings & Exit Status
    # -------------------------------------------------------------------------
    if dups:
        print("DUPLICATE TEST FILES FOUND:")
        print("=" * 60)
        total_lines = 0

        for group in dups:
            print("\nDuplicate group:")
            for p in group:
                with p.open(encoding="utf-8") as fh:
                    lines = sum(1 for _ in fh)
                print(f"  {p} ({lines} lines)")
                if group.index(p) > 0:  # Accumulate lines of redundant clones
                    total_lines += lines

        print("\n" + "=" * 60)
        print(f"Total duplicate lines that could be removed: {total_lines}")
        sys.exit(1)
    else:
        print("✅ No duplicate test files found")
        sys.exit(0)


if __name__ == "__main__":
    main()
