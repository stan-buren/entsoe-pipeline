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

"""Symmetry and verification tests for the environment path system.

This module ensures our pipeline can dynamically locate the project root under
different runtime execution contexts (e.g., local shell, docker container, or
orchestrated production run) and that all exported directory constants are
sound.
"""

import os

from pathlib import Path

import pytest

import entsoe_pipeline.config.paths as paths

from entsoe_pipeline.config.paths import find_project_root

# -----------------------------------------------------------------------------
# Configuration Constants & Single Source of Truth
# -----------------------------------------------------------------------------
# Single source of truth for all expected paths and their structure
# relative to PROJECT_ROOT.
# If you add a new path constant to paths.py, simply append it to this dictionary!

EXPECTED_PATHS = {
    "PROJECT_ROOT": None,  # Base root path
    "DATA_DIR": ".data",
    "TESTS_DIR": "tests",
    "ADR_DIR": "docs/adr",
    "ADR_TEMPLATE_PATH": "docs/adr/template/ADR_TEMPLATE.md",
    "CONFIG_DIR": "config_env",
    "MANUAL_DATA_DIR": ".data/manual_added_data",
    "ENV_FILE": ".env",
    "FMS_METADATA_DIR": "fms_metadata",
    "OVERVIEW_YML": "fms_metadata/overview.yml",
}


def test_find_project_root_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that find_project_root respects the PROJECT_ROOT env variable.

    When running inside containerized platforms like Apache Airflow or Kubernetes
    executors, the filesystem structure can change. To guarantee absolute path
    portability, this test ensures that the directory resolver respects and returns
    whatever path is injected via the standard 'PROJECT_ROOT' environment variable
    rather than trying to dynamically scan parent directories.

    Args:
        monkeypatch: Pytest utility fixture for safely modifying environment
          variables and module state during a test run.
    """
    # -------------------------------------------------------------------------
    # ARRANGE: A fake project root path configured via environment variable
    # -------------------------------------------------------------------------
    fake_path = "/tmp/airflow_configured_root"  # noqa: S108

    # -------------------------------------------------------------------------
    # ACT: We inject it into the environment using monkeypatch
    # -------------------------------------------------------------------------
    monkeypatch.setenv("PROJECT_ROOT", fake_path)

    # -------------------------------------------------------------------------
    # ASSERT: The function must return this path
    # -------------------------------------------------------------------------
    assert find_project_root() == Path(fake_path)


def test_find_project_root_static_fallback(mocker) -> None:
    """Verify that find_project_root falls back to parents[1] if no markers exist.

    This handles the developer checkout scenario where the `.project_root` marker
    file might be absent or deleted, and no environment overrides are defined.
    The dynamic path resolver must gracefully fall back to checking the parent
    directories relative to the location of the `paths.py` source file itself. We
    simulate this fallback by mocking filesystem checks.

    Args:
        mocker: Pytest-mock fixture to patch system properties.
    """
    # -------------------------------------------------------------------------
    # ARRANGE: We mock Path.exists to return False specifically for '.project_root'
    # -------------------------------------------------------------------------
    original_exists = Path.exists

    def mock_exists(self: Path) -> bool:
        if self.name == ".project_root":
            return False
        return original_exists(self)

    # Use mocker to temporarily patch Path.exists globally
    mocker.patch.object(Path, "exists", mock_exists)

    # Also ensure the environment variable PROJECT_ROOT is cleared during the test
    mocker.patch.dict(os.environ, {}, clear=True)

    # -------------------------------------------------------------------------
    # ACT: We execute the lookup
    # -------------------------------------------------------------------------
    root = find_project_root()

    # -------------------------------------------------------------------------
    # ASSERT: It should fall back to current_file.parents[1] (project root)
    # -------------------------------------------------------------------------
    expected_root = Path(__file__).resolve().parents[1]  # Parent of tests/ folder
    assert root == expected_root


def test_exported_path_constants() -> None:
    """Verify that all exported path constants are Path objects and correct.

    This ensures that each constant defined in paths.py is an absolute path
    pointing to the correct location relative to the detected PROJECT_ROOT.
    It loops through our single source of truth (EXPECTED_PATHS) and verifies
    both types and relative structure.
    """
    # -------------------------------------------------------------------------
    # ARRANGE: Access to the dynamically resolved project root
    # -------------------------------------------------------------------------
    project_root = paths.PROJECT_ROOT
    assert isinstance(project_root, Path)

    # -------------------------------------------------------------------------
    # WHEN / THEN: Dynamically verify each constant from our single source of truth
    # -------------------------------------------------------------------------
    for name, relative_path in EXPECTED_PATHS.items():
        value = getattr(paths, name)
        assert isinstance(value, Path), f"Constant '{name}' is not a Path object"

        if relative_path is not None:
            assert value == project_root / relative_path, (
                f"Constant '{name}' does not point to the expected relative path."
            )


def test_all_path_constants_are_validated() -> None:
    """Ensure that all uppercase Path constants exported by paths.py are covered.

    This acts as a meta-test/lint check: if a developer adds a new path to
    paths.py but forgets to add it to the EXPECTED_PATHS dictionary, this test
    will fail, forcing strict test-coverage for our environment paths.
    """
    # -------------------------------------------------------------------------
    # ARRANGE: Dynamically discovered uppercase Path constants in paths.py
    # -------------------------------------------------------------------------
    discovered_constants = {
        name
        for name, value in vars(paths).items()
        if name.isupper() and isinstance(value, Path)
    }

    # -------------------------------------------------------------------------
    # ACT: We compare discovered constants against our single source of truth
    # -------------------------------------------------------------------------
    missing_tests = discovered_constants - EXPECTED_PATHS.keys()
    extra_tests = EXPECTED_PATHS.keys() - discovered_constants

    # -------------------------------------------------------------------------
    # ASSERT: Assert that both sets match exactly, preventing untested constants
    # -------------------------------------------------------------------------
    assert not missing_tests, (
        f"New path constants added to paths.py are NOT covered by tests: "
        f"{missing_tests}. "
        f"Please add them to the EXPECTED_PATHS dictionary in test_paths.py!"
    )
    assert not extra_tests, (
        f"The following constants in EXPECTED_PATHS were removed or "
        f"renamed in paths.py: {extra_tests}. "
        f"Please clean them up!"
    )
