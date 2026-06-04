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

"""Quality gate to verify that all package __init__.py modules are fully importable.

Ensures that no __init__.py file has broken imports, missing dependencies,
or invalid references inside its __all__ exports list.
"""

from __future__ import annotations

import importlib

from pathlib import Path

import pytest

from entsoe_pipeline import SRC_DIR


def find_all_package_modules() -> list[tuple[str, Path]]:
    """Crawls the src directory to discover all Python packages containing __init__.py.

    Returns:
        list[tuple[str, Path]]: List of (module_name, init_file_path) tuples.
    """
    package_modules = []
    # Recursively traverse the src directory to find all __init__.py files
    for path in SRC_DIR.rglob("__init__.py"):
        # Resolve the relative path from src/ to build the module name
        relative = path.parent.relative_to(SRC_DIR)
        # e.g., entsoe_pipeline/fms_metadata -> entsoe_pipeline.fms_metadata
        parts = relative.parts
        if not parts:
            continue
        module_name = ".".join(parts)
        package_modules.append((module_name, path))

    return sorted(package_modules, key=lambda x: x[0])


# =============================================================================
# 1. QUALITY GATE TESTS: __init__.py EXPORTS AUDIT
# =============================================================================


@pytest.mark.parametrize(("module_name", "path"), find_all_package_modules())
def test_init_file_is_importable_and_exports_are_valid(
    module_name: str, path: Path
) -> None:
    """Audit each __init__.py file to ensure it imports and exports cleanly.

    Ensures:
    1. The package module is successfully imported without raising ImportError.
    2. Every name declared in the package's __all__ list is actually exported
       and accessible on the module namespace.
    """
    # -------------------------------------------------------------------------
    # ARRANGE: Ensure the target package initialization file exists
    # -------------------------------------------------------------------------
    assert path.exists(), f"Package __init__.py file does not exist at: {path}"

    # -------------------------------------------------------------------------
    # ACT: Dynamically load the package module
    # -------------------------------------------------------------------------
    try:
        module = importlib.import_module(module_name)
    except Exception as e:
        pytest.fail(
            f"Failed to import package module '{module_name}' from {path}. "
            f"Error details: {e}"
        )

    # -------------------------------------------------------------------------
    # ASSERT: Verify that every name declared in __all__ exists in the module
    # -------------------------------------------------------------------------
    if hasattr(module, "__all__"):
        all_exports = module.__all__
        assert isinstance(all_exports, list), (
            f"__all__ inside '{module_name}' must be a list of strings."
        )

        missing_exports = [name for name in all_exports if not hasattr(module, name)]

        assert not missing_exports, (
            f"Package '{module_name}' defines names in __all__ that do not "
            f"exist in the module namespace: {missing_exports}"
        )
