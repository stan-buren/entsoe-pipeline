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

"""Validate Proposal filename, title consistency, structure, and placeholders.

This pre-commit hook script enforces structural and content validation rules
for Design Proposals (Proposals) maintained under docs/proposals/. It ensures
that proposals conform to the official template, specify valid statuses and dates,
and do not contain unresolved placeholders.
"""

import re
import sys

from pathlib import Path

from entsoe_pipeline import PROJECT_ROOT

# Resolve the Proposals directories dynamically from SSOT project paths
ROOT_DIR = PROJECT_ROOT / "docs" / "proposals"
TEMPLATE_PATH = ROOT_DIR / "template" / "PROPOSAL_TEMPLATE.md"

# Standard template boilerplate placeholders that must be customized
FORBIDDEN_BOILERPLATE = [
    "YYYY-MM-DD",
    "Draft / Under Review / Accepted / Rejected",
    "Author Name / AI Assistant",
    "Post-Marts Release / Phase 3 / Long-Term",
]


def get_template_headings(template_file: Path) -> list[str]:
    """Extract all structural markdown headings from the proposals template."""
    headings = []
    if not template_file.exists():
        return headings

    in_code_block = False
    with template_file.open(encoding="utf-8") as f:
        for line in f:
            clean_line = line.strip()

            if clean_line.startswith("```"):
                in_code_block = not in_code_block
                continue

            if in_code_block:
                continue

            if clean_line.startswith(("##", "###")):
                headings.append(clean_line)

    return headings


def find_placeholders(content: str) -> list[tuple[int, str]]:
    """Scan the proposal content for unreplaced template placeholder tokens."""
    placeholders = []
    pattern = re.compile(r"\[([^\]]+)\](?!\()")

    in_code_block = False
    for line_num, line in enumerate(content.splitlines(), 1):
        stripped_line = line.strip()

        if stripped_line.startswith("```"):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            continue

        if stripped_line.startswith("<!--") or stripped_line.endswith("-->"):
            continue

        for match in pattern.finditer(line):
            text = match.group(1).strip()

            if not text or text.lower() in {"x", "/"}:
                continue

            if re.match(r"^PROPOSAL-\d{3,4}$", text, re.IGNORECASE):
                continue

            placeholders.append((line_num, text))

    return placeholders


def main() -> None:
    """Validate all workspace Proposal markdown files against template requirements."""
    if not ROOT_DIR.exists():
        print(f"Proposals directory not found: {ROOT_DIR}")
        sys.exit(1)

    if not TEMPLATE_PATH.exists():
        print(f"Proposal Template not found at: {TEMPLATE_PATH}")
        sys.exit(1)

    required_headings = get_template_headings(TEMPLATE_PATH)

    ok = True
    issues = []

    # Pre-compile regular expressions used in the validation loop
    re_filename = re.compile(r"(\d{4})-.*\.md$", re.IGNORECASE)
    re_title = re.compile(r"#\s*PROPOSAL[-\s]?0*(\d+)\s*:?", re.IGNORECASE)

    # Metadata patterns
    re_status_meta = re.compile(r"\*\s*\*\*Status:\*\*\s*(.*)", re.IGNORECASE)
    re_date_meta = re.compile(r"\*\s*\*\*Created Date:\*\*\s*(.*)", re.IGNORECASE)
    re_date_format = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    for file_path in sorted(ROOT_DIR.iterdir()):
        if not file_path.name.lower().endswith(".md"):
            continue

        if file_path.is_dir() or file_path.name == "README.md":
            continue

        filename = file_path.name

        # A. Verify naming format (e.g., '0001-adaptive-iceberg-compression.md')
        m = re_filename.match(filename)
        if not m:
            issues.append(f"Bad filename format: {filename} (expected: 000X-name.md)")
            ok = False
            continue

        file_id = m.group(1).zfill(4)

        try:
            with file_path.open(encoding="utf-8") as fh:
                content = fh.read()

            lines = content.splitlines()
            if not lines:
                issues.append(f"File is empty: {filename}")
                ok = False
                continue

            # B. Verify Proposal ID in first line header matches filename ID
            first_line = lines[0].strip()
            m2 = re_title.match(first_line)
            if not m2:
                issues.append(f"No Proposal ID in title of {filename}: '{first_line}'")
                ok = False
                continue

            title_id = f"{int(m2.group(1)):04d}"
            if file_id != title_id:
                issues.append(
                    f"ID mismatch in {filename}: "
                    f"filename has ID {file_id} but title has ID {title_id}"
                )
                ok = False

            # C. Verify all mandatory template sections are present
            file_headings = []
            in_code_block = False
            for line in lines:
                stripped_line = line.strip()
                if stripped_line.startswith("```"):
                    in_code_block = not in_code_block
                    continue
                if in_code_block:
                    continue
                if stripped_line.startswith(("##", "###")):
                    file_headings.append(stripped_line)

            for heading in required_headings:
                if heading not in file_headings:
                    issues.append(
                        f"Missing required section in {filename}: '{heading}'"
                    )
                    ok = False

            # D. Verify status metadata contains valid status transitions
            status_match = re_status_meta.search(content)
            if status_match:
                status = status_match.group(1).strip()
                allowed_statuses = {"Draft", "Under Review", "Accepted", "Rejected"}
                if status not in allowed_statuses:
                    issues.append(
                        f"Invalid Status in {filename}: '{status}' "
                        f"(must be one of: {', '.join(sorted(allowed_statuses))})"
                    )
                    ok = False
            else:
                issues.append(
                    f"Missing Status metadata in {filename} "
                    "(expected: '* **Status:** [value]')"
                )
                ok = False

            # E. Verify created date format consistency
            date_match = re_date_meta.search(content)
            if date_match:
                date_str = date_match.group(1).strip()
                if not re_date_format.match(date_str):
                    issues.append(
                        f"Invalid Created Date in {filename}: '{date_str}' "
                        "(expected format: 'YYYY-MM-DD')"
                    )
                    ok = False
            else:
                issues.append(
                    f"Missing Created Date metadata in {filename} "
                    "(expected: '* **Created Date:** [value]')"
                )
                ok = False

            # F. Verify forbidden boilerplate strings (excluding code block context)
            in_code_block = False
            for line_num, line in enumerate(lines, 1):
                stripped_line = line.strip()
                if stripped_line.startswith("```"):
                    in_code_block = not in_code_block
                    continue
                if in_code_block:
                    continue
                for boilerplate in FORBIDDEN_BOILERPLATE:
                    if boilerplate in line:
                        issues.append(
                            f"Unmodified template boilerplate in {filename} "
                            f"at line {line_num}: '{boilerplate}'"
                        )
                        ok = False

            # G. Check for any remaining bracketed placeholders
            placeholders = find_placeholders(content)
            for line_num, placeholder in placeholders:
                issues.append(
                    f"Unreplaced template placeholder in {filename} "
                    f"at line {line_num}: '[{placeholder}]'"
                )
                ok = False

        except Exception as e:
            issues.append(f"Error reading {filename}: {e}")
            ok = False

    if not ok:
        print("❌ PROPOSAL VALIDATION FAILED")
        print("=" * 60)
        for issue in issues:
            print(f"  • {issue}")
        print("=" * 60)
        print(f"Total issues: {len(issues)}")
        sys.exit(1)
    else:
        print(
            "✅ All Proposals conform to the template guidelines and have consistent IDs"
        )
        sys.exit(0)


if __name__ == "__main__":
    main()
