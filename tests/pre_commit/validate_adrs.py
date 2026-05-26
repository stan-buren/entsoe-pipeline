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

"""Validate ADR filename, title consistency, structure, and placeholders.

This pre-commit hook script enforces structural and content validation rules
for Architecture Decision Records (ADRs) maintained in the workspace. It ensures
that ADRs conform to the official template, do not drift in naming or ID consistency,
contain all required headings, specify valid statuses (e.g., 'Proposed', 'Accepted'),
and do not contain unresolved boilerplate placeholder tokens.
"""

import re
import sys

from pathlib import Path

from entsoe_pipeline import ADR_DIR, ADR_TEMPLATE_PATH

# -----------------------------------------------------------------------------
# Script Configuration & Constants
# -----------------------------------------------------------------------------
# Resolve the ADR directories from CLI argument overrides or central paths
ROOT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else ADR_DIR
TEMPLATE_PATH = ADR_TEMPLATE_PATH

# Standard template boilerplate placeholders that must be customized in active records
FORBIDDEN_BOILERPLATE = [
    "vX.Y / YYYY-MM-DD",
    "[Proposed | Accepted | Rejected | Deprecated | Superseded by ADR-XXXX]",
]

# Compiled pattern for matching valid "Superseded by ADR-XXXX" statuses
SUPERSEDED_STATUS_PATTERN = re.compile(r"^Superseded by ADR-\d{3,4}$", re.IGNORECASE)


def get_template_headings(template_file: Path) -> list[str]:
    """Extract all structural markdown headings from the workspace ADR template.

    This function parses the template markdown file line-by-line, capturing all
    second-level headers (e.g., starting with '##') while actively tracking
    fenced code blocks to prevent capturing accidental headers in code examples.

    Args:
        template_file: Absolute path pointing to the template markdown document.

    Returns:
        A list of heading strings in their exact order of appearance.
    """
    headings = []
    if not template_file.exists():
        return headings

    in_code_block = False
    with template_file.open(encoding="utf-8") as f:
        for line in f:
            clean_line = line.strip()

            # Track code blocks to prevent capturing headers embedded in code examples
            if clean_line.startswith("```"):
                in_code_block = not in_code_block
                continue

            if in_code_block:
                continue

            # Capture second-level section headings
            if clean_line.startswith("##"):
                headings.append(clean_line)

    return headings


def find_placeholders(content: str) -> list[tuple[int, str]]:
    """Scan the target ADR content for unreplaced template placeholder tokens.

    It detects unreplaced developer instructions typically enclosed in square
    brackets (e.g., '[Title of Decision]'). It uses regex lookahead to skip standard
    markdown links (e.g., '[link](url)'), checks for markdown list checkboxes
    (e.g., '[ ]', '[x]'), and ignores valid inter-ADR references like '[ADR-001]'.

    Args:
        content: The raw text content of the ADR markdown file under review.

    Returns:
        A list of tuples, where each tuple contains the 1-indexed line number
        and the unreplaced placeholder string.
    """
    placeholders = []

    # Matches brackets NOT followed by parenthesis (skipping standard markdown links)
    pattern = re.compile(r"\[([^\]]+)\](?!\()")

    in_code_block = False
    for line_num, line in enumerate(content.splitlines(), 1):
        stripped_line = line.strip()

        # Bypass code blocks to avoid flagging structural placeholders in code examples
        if stripped_line.startswith("```"):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            continue

        # Ignore markdown instructions or HTML comments
        if stripped_line.startswith("<!--") or stripped_line.endswith("-->"):
            continue

        for match in pattern.finditer(line):
            text = match.group(1).strip()

            # Skip empty brackets and standard checklist elements
            if not text or text.lower() in {"x", "/"}:
                continue

            # Skip valid inter-ADR linking references
            if re.match(r"^ADR-\d{3,4}$", text, re.IGNORECASE):
                continue

            placeholders.append((line_num, text))

    return placeholders


def main() -> None:
    """Validate all workspace ADR markdown files against template requirements."""
    # -------------------------------------------------------------------------
    # 1. Path Verification & Input Validation
    # -------------------------------------------------------------------------
    if not ROOT_DIR.exists():
        print(f"ADR directory not found: {ROOT_DIR}")
        sys.exit(1)

    if not TEMPLATE_PATH.exists():
        print(f"ADR Template not found at: {TEMPLATE_PATH}")
        sys.exit(1)

    # -------------------------------------------------------------------------
    # 2. Extract Required Structural Template Headings
    # -------------------------------------------------------------------------
    required_headings = get_template_headings(TEMPLATE_PATH)

    ok = True
    issues = []

    # -------------------------------------------------------------------------
    # 3. Iterate & Validate each Active ADR document
    # -------------------------------------------------------------------------
    for file_path in sorted(ROOT_DIR.iterdir()):
        if not file_path.name.lower().endswith(".md"):
            continue

        if file_path.is_dir():
            continue

        filename = file_path.name

        # A. Verify naming format (e.g., 'ADR-001-centralized-configuration.md')
        m = re.match(r"ADR-(\d{3,4})-.*\.md$", filename, re.IGNORECASE)
        if not m:
            issues.append(f"Bad filename format: {filename}")
            ok = False
            continue

        file_id = m.group(1).zfill(4)  # Normalize numeric ID to 4 digits

        try:
            with file_path.open(encoding="utf-8") as fh:
                content = fh.read()

            lines = content.splitlines()
            if not lines:
                issues.append(f"File is empty: {filename}")
                ok = False
                continue

            # B. Verify ADR ID in first line header matches filename ID
            first_line = lines[0].strip()
            m2 = re.match(r"#\s*ADR[-\s]?0*(\d+)\s*:?", first_line, re.IGNORECASE)
            if not m2:
                issues.append(f"No ADR ID in title of {filename}: '{first_line}'")
                ok = False
                continue

            title_id = f"{int(m2.group(1)):04d}"
            if file_id != title_id:
                issues.append(
                    f"ID mismatch in {filename}: "
                    f"filename has ADR-{file_id} but title has ADR-{title_id}"
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
                if stripped_line.startswith("##"):
                    file_headings.append(stripped_line)

            for heading in required_headings:
                if heading not in file_headings:
                    issues.append(
                        f"Missing required section in {filename}: '{heading}'"
                    )
                    ok = False

            # D. Verify status metadata contains valid status transitions
            status_match = re.search(r"\*\*Status:\*\*\s*(.*)", content)
            if status_match:
                status = status_match.group(1).strip()
                allowed_statuses = {"Proposed", "Accepted", "Rejected", "Deprecated"}
                is_valid_status = status in allowed_statuses or bool(
                    SUPERSEDED_STATUS_PATTERN.match(status)
                )
                if not is_valid_status:
                    issues.append(
                        f"Invalid Status in {filename}: '{status}' "
                        "(must be one of: Proposed, Accepted, Rejected, Deprecated, "
                        "or 'Superseded by ADR-XXXX')"
                    )
                    ok = False
            else:
                issues.append(
                    f"Missing status metadata in {filename} "
                    "(expected: '**Status:** [value]')"
                )
                ok = False

            # E. Verify document version and date format consistency
            version_match = re.search(r"\*\*Version/Date:\*\*\s*(.*)", content)
            if version_match:
                version_str = version_match.group(1).strip()
                if not re.match(r"^v\d+\.\d+\s*/\s*\d{4}-\d{2}-\d{2}$", version_str):
                    issues.append(
                        f"Invalid Version/Date in {filename}: '{version_str}' "
                        "(expected format: 'vX.Y / YYYY-MM-DD')"
                    )
                    ok = False
            else:
                issues.append(
                    f"Missing version/date metadata in {filename} "
                    "(expected: '**Version/Date:** [value]')"
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

    # -------------------------------------------------------------------------
    # 4. Report Validation Results & Exit Status
    # -------------------------------------------------------------------------
    if not ok:
        print("❌ ADR VALIDATION FAILED")
        print("=" * 60)
        for issue in issues:
            print(f"  • {issue}")
        print("=" * 60)
        print(f"Total issues: {len(issues)}")
        sys.exit(1)
    else:
        print("✅ All ADRs conform to the template guidelines and have consistent IDs")
        sys.exit(0)


if __name__ == "__main__":
    main()
