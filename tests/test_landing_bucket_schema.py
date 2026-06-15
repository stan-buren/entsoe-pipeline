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

"""Unit tests for the landing bucket schema generator and configuration.

This suite ensures the correctness of the compiled landing bucket directory contract
and validates that the generated schema matches the FMS tree structure catalog.
"""

import pytest

from ruamel.yaml import YAML

from entsoe_pipeline import (
    LANDING_BUCKET_SCHEMA_YML,
    OVERVIEW_TREE_YML,
)
from entsoe_pipeline.fms_metadata.ingestion.landing_bucket_schema import (
    extract_folders_from_tree,
)


@pytest.mark.unit
def test_landing_bucket_schema_exists() -> None:
    """Verify that the generated landing bucket schema file exists."""
    # -------------------------------------------------------------------------
    # ARRANGE: Resolve path to schema yml file
    # -------------------------------------------------------------------------
    schema_path = LANDING_BUCKET_SCHEMA_YML

    # -------------------------------------------------------------------------
    # ACT & ASSERT: Assert schema file existence on disk
    # -------------------------------------------------------------------------
    assert schema_path.exists(), (
        f"Landing bucket schema does not exist at: {schema_path}. "
        f"Please run landing_bucket_schema_builder.py first."
    )


@pytest.mark.unit
def test_landing_bucket_schema_structure_parity() -> None:
    """Verify that the compiled schema matches the overview tree structure.

    Extracts all folders directly from overview_tree.yml and asserts that they
    match the list declared in config/landing_bucket_schema.yml exactly.
    """
    # -------------------------------------------------------------------------
    # ARRANGE: Load both overview tree and schema catalogs
    # -------------------------------------------------------------------------
    yaml = YAML(typ="safe")

    assert OVERVIEW_TREE_YML.exists(), (
        f"Required overview tree file not found: {OVERVIEW_TREE_YML}"
    )
    assert LANDING_BUCKET_SCHEMA_YML.exists(), (
        f"Schema file not found: {LANDING_BUCKET_SCHEMA_YML}"
    )

    with OVERVIEW_TREE_YML.open(encoding="utf-8") as f:
        tree_data = yaml.load(f) or {}

    with LANDING_BUCKET_SCHEMA_YML.open(encoding="utf-8") as f:
        schema_data = yaml.load(f) or {}

    # -------------------------------------------------------------------------
    # ACT: Extract expected and actual folder lists
    # -------------------------------------------------------------------------
    expected_folders = extract_folders_from_tree(tree_data)
    actual_folders = schema_data.get("folders", [])

    # -------------------------------------------------------------------------
    # ASSERT: Assert parity, versions, and properties
    # -------------------------------------------------------------------------
    assert schema_data.get("schema_version") == "1.0.0"
    assert isinstance(actual_folders, list)
    assert len(actual_folders) > 0

    # Every expected prefix must be in the actual schema, and vice versa
    assert set(actual_folders) == set(expected_folders), (
        "Folders list in landing_bucket_schema.yml does not match overview_tree.yml. "
        "Please run landing_bucket_schema_builder.py to update it."
    )
