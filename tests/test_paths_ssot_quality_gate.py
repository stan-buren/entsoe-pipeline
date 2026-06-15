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

"""Quality gate to enforce that all file path constants are centralized in paths.py.

Audits every Python script within the source package to ensure they never
define raw path constructors or perform root-relative calculations in-place.
"""

from __future__ import annotations

import re

from pathlib import Path

import pytest

from entsoe_pipeline import SRC_DIR, TESTS_DIR

# Locate the config package directory to exempt paths.py from checks
EXEMPT_FILES = {
    "paths.py",
    "project_root.py",
    "test_paths.py",
    "test_paths_ssot_quality_gate.py",
}


def find_all_source_modules() -> list[Path]:
    """Retrieves all Python modules within the main source package and test suite.

    Excludes paths.py, test-specific path tests, and pre-commit tools.

    Returns:
        list[Path]: List of Path objects pointing to Python files.
    """
    source_files = []
    # Search all python modules under entsoe_pipeline
    for path in SRC_DIR.rglob("*.py"):
        if path.name in EXEMPT_FILES:
            continue
        source_files.append(path)

    # Search all test modules under tests, excluding pre-commit hooks and path tests
    for path in TESTS_DIR.rglob("*.py"):
        if "pre_commit" in path.parts:
            continue
        if path.name in EXEMPT_FILES:
            continue
        source_files.append(path)

    return sorted(source_files)


# =============================================================================
# 1. QUALITY GATE TESTS: SSOT PATH CONVENTION AUDIT
# =============================================================================


@pytest.mark.parametrize("file_path", find_all_source_modules())
def test_script_contains_no_raw_path_definitions(file_path: Path) -> None:
    """Audit source modules to enforce that path logic is imported from paths.py.

    Assures that files do not contain:
    1. Direct raw Path construction from PROJECT_ROOT (e.g., `PROJECT_ROOT /`).
    2. Self-resolving path lookups utilizing `Path(__file__)`.
    """
    # -------------------------------------------------------------------------
    # ARRANGE: Verify that the source module exists and read its contents
    # -------------------------------------------------------------------------
    assert file_path.exists(), f"Source file does not exist at: {file_path}"
    content = file_path.read_text(encoding="utf-8")

    # -------------------------------------------------------------------------
    # ACT: Scan for forbidden raw path resolution patterns
    # -------------------------------------------------------------------------
    forbidden_patterns = {
        r"PROJECT_ROOT\s*/": (
            "Direct raw path concatenation using PROJECT_ROOT. "
            "Please register this directory path as a constant in paths.py instead."
        ),
        r"PROJECT_ROOT\.joinpath": (
            "Direct joinpath lookup using PROJECT_ROOT. "
            "Please register this directory path as a constant in paths.py instead."
        ),
        r"Path\(\s*__file__\s*\)": (
            "Self-resolving path lookup utilizing __file__. "
            "All repository path resolution must be centralized in paths.py."
        ),
        r"Path\(\s*__file__\s*\)(\.resolve\(\))?\.parent": (
            "Direct parent traversal relative to __file__. "
            "All repository path resolution must be centralized in paths.py."
        ),
        r"os\.path\.(abspath|dirname|realpath)\(\s*__file__\s*\)": (
            "In-place os.path resolution relative to __file__. "
            "All repository path resolution must be centralized in paths.py."
        ),
        r'Path\(\s*["\'](fms_metadata|\.data|config_env|config_env_example|tests|docs)["\']\s*\)': (
            "Direct instantiation of a hardcoded path pointing to a repository folder. "
            "Please import the pre-defined path constant from paths.py instead."
        ),
        r'Path\(\s*["\'](?:\.env|\.project_root)["\']\s*\)': (
            "Direct instantiation of a hardcoded path pointing to configuration/metadata files. "
            "Please import the pre-defined path constant from paths.py instead."
        ),
        r'Path\(\s*["\']\.\./': (
            "Direct relative parent traversal (..) in Path instantiation. "
            "Please register the directory path as a constant in paths.py instead."
        ),
        r"Path\.cwd\(\)": (
            "Raw current working directory lookup via Path.cwd(). "
            "All repository path resolution must be centralized in paths.py."
        ),
        r"os\.getcwd\(\)": (
            "Raw current working directory lookup via os.getcwd(). "
            "All repository path resolution must be centralized in paths.py."
        ),
        r"os\.path\.join\(\s*(?:PROJECT_ROOT|Path\b|__file__|os\.path|os\.getcwd)": (
            "Dangerous raw path combination using os.path.join with base path objects. "
            "All paths must be imported from paths.py as Path objects."
        ),
        r'open\(\s*["\'](?:\.env|config_env|\.data|fms_metadata)': (
            "Direct open() call targeting hardcoded raw path names. "
            "Please use pre-defined Path constants from paths.py instead."
        ),
    }

    violations = []
    for pattern, explanation in forbidden_patterns.items():
        if re.search(pattern, content):
            violations.append(explanation)

    # -------------------------------------------------------------------------
    # ASSERT: Confirm that no SSOT path violations were discovered
    # -------------------------------------------------------------------------
    assert not violations, (
        f"Path convention violation(s) discovered in [ {file_path.name} ] "
        f"(at file:///{file_path}):\n" + "\n".join(f"  - {v}" for v in violations)
    )
