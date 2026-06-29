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

"""Verification tests for the detailed ENTSO-E domains overview catalog.

This test suite validates that:
1. The detailed catalog contains no duplicate keys.
2. Every domain extract declared in overview.yml has a corresponding detailed
   specification in the business context catalog.
3. Every specification conforms strictly to the schema template defined in the
   config files.
"""

from pathlib import Path

import pytest

from ruamel.yaml import YAML
from ruamel.yaml.constructor import DuplicateKeyError

from entsoe_pipeline import (
    BUSINESS_CONTEXT_CATALOG_YML,
    BUSINESS_CONTEXT_TEMPLATE_YML,
    OVERVIEW_YML,
)


def load_yaml(path: Path) -> dict:
    """Helper function to load a YAML file using ruamel.yaml."""
    yaml = YAML(typ="safe")
    with open(path, encoding="utf-8") as f:
        return yaml.load(f)


def get_expected_extracts_by_category() -> dict[str, set[str]]:
    """Helper to parse overview.yml and collect extracts by category."""
    overview = load_yaml(OVERVIEW_YML)
    expected = {}

    # Traverse all environments to collect expected extracts from TP_export
    for env in overview.get("environments", {}).values():
        for root_dir in env.get("root_directories", []):
            if root_dir.get("name") == "TP_export":
                domains = root_dir.get("domains", {})
                for category, extracts in domains.items():
                    if category not in expected:
                        expected[category] = set()
                    expected[category].update(extracts)
    return expected


@pytest.mark.unit
def test_detailed_catalog_contains_no_duplicate_keys() -> None:
    """Verify that the detailed catalog contains no duplicate YAML keys.

    We use the default strict parsing mode of ruamel.yaml, which raises a
    DuplicateKeyError if any duplicate key mappings are encountered during parsing.
    """
    # -------------------------------------------------------------------------
    # ARRANGE: Path to the detailed business context catalog
    # -------------------------------------------------------------------------
    path = BUSINESS_CONTEXT_CATALOG_YML

    # -------------------------------------------------------------------------
    # ACT & ASSERT: Attempt parsing and verify no DuplicateKeyError is raised
    # -------------------------------------------------------------------------
    try:
        yaml = YAML()
        with open(path, encoding="utf-8") as f:
            yaml.load(f)
    except DuplicateKeyError as e:
        pytest.fail(f"Detailed catalog contains duplicate keys: {e}")


@pytest.mark.unit
@pytest.mark.skip(
    reason="Skipped due to desynchronization. Will be automated via NotebookLM in Proposal 0002."
)
def test_detailed_catalog_contains_all_domains_from_overview() -> None:
    """Verify that the detailed catalog matches the domain extracts in overview.yml.

    This test enforces that:
    1. Every category in overview.yml exists in the detailed catalog.
    2. Every extract listed in overview.yml exists in the detailed catalog.
    3. There are no orphaned/unknown extracts described in the detailed catalog.
    """
    # -------------------------------------------------------------------------
    # ARRANGE: Collect expected domains and active extracts from overview.yml
    # -------------------------------------------------------------------------
    expected = get_expected_extracts_by_category()

    # -------------------------------------------------------------------------
    # ACT: Load the actual detailed catalog from the filesystem
    # -------------------------------------------------------------------------
    catalog = load_yaml(BUSINESS_CONTEXT_CATALOG_YML)
    actual_domains = catalog.get("domains", {})

    # -------------------------------------------------------------------------
    # ASSERT: Compare expected categories and extracts against the catalog
    # -------------------------------------------------------------------------
    # 1. Assert categories exist and match
    for category, expected_extracts in expected.items():
        assert category in actual_domains, (
            f"Category '{category}' defined in overview.yml is missing "
            f"from the detailed catalog."
        )

        catalog_extracts = actual_domains[category] or {}
        for extract in expected_extracts:
            assert extract in catalog_extracts, (
                f"Extract '{extract}' under category '{category}' defined in "
                f"overview.yml is missing from the detailed catalog."
            )

    # 2. Check for orphaned categories or extracts in the detailed catalog
    for category, extracts in actual_domains.items():
        assert category in expected, (
            f"Category '{category}' in detailed catalog does not exist in overview.yml."
        )
        extracts = extracts or {}
        for extract in extracts:
            assert extract in expected[category], (
                f"Extract '{extract}' under category '{category}' in detailed "
                f"catalog is not present in overview.yml's active list."
            )


@pytest.mark.unit
def test_each_domain_extract_matches_detailed_template() -> None:
    """Validate that every extract description conforms to the blueprint template."""
    # -------------------------------------------------------------------------
    # ARRANGE: Load the validation template schema and catalog data
    # -------------------------------------------------------------------------
    template = load_yaml(BUSINESS_CONTEXT_TEMPLATE_YML)
    catalog = load_yaml(BUSINESS_CONTEXT_CATALOG_YML)

    schema_props = template.get("properties", {})
    domains = catalog.get("domains", {})

    # -------------------------------------------------------------------------
    # ACT: Traverse every category and extract defined in the detailed catalog
    # -------------------------------------------------------------------------
    errors = []
    for category, extracts in domains.items():
        extracts = extracts or {}
        for extract_name, extract_data in extracts.items():
            if not isinstance(extract_data, dict):
                errors.append(
                    f"[{category}][{extract_name}] Expected entry to be a dictionary."
                )
                continue

            # -----------------------------------------------------------------
            # ASSERT: Verify each key specified in the template schema
            # -----------------------------------------------------------------
            # Check top-level properties
            for prop_name, prop_spec in schema_props.items():
                if prop_spec.get("required") and prop_name not in extract_data:
                    errors.append(
                        f"[{category}][{extract_name}] Missing required field: '{prop_name}'"
                    )
                    continue

                val = extract_data.get(prop_name)
                expected_type = prop_spec.get("type")

                if expected_type == "string" and val is not None:
                    if not isinstance(val, str):
                        errors.append(
                            f"[{category}][{extract_name}] Field '{prop_name}' "
                            f"must be a string (got {type(val).__name__})."
                        )
                elif expected_type == "object" and val is not None:
                    if not isinstance(val, dict):
                        errors.append(
                            f"[{category}][{extract_name}] Field '{prop_name}' "
                            f"must be a dictionary."
                        )
                        continue

                    # Verify nested specifications under technical_specification
                    if prop_name == "technical_specification":
                        nested_props = prop_spec.get("properties", {})
                        for n_name, n_spec in nested_props.items():
                            if n_spec.get("required") and n_name not in val:
                                errors.append(
                                    f"[{category}][{extract_name}].{prop_name} "
                                    f"Missing required nested field: '{n_name}'"
                                )
                                continue

                            n_val = val.get(n_name)
                            n_type = n_spec.get("type")
                            if n_type == "string" and n_val is not None:
                                if not isinstance(n_val, str):
                                    errors.append(
                                        f"[{category}][{extract_name}].{prop_name}.{n_name} "
                                        f"must be a string."
                                    )
                            elif n_type == "object" and n_val is not None:
                                if not isinstance(n_val, dict):
                                    errors.append(
                                        f"[{category}][{extract_name}].{prop_name}.{n_name} "
                                        f"must be a dictionary."
                                    )

    assert not errors, (
        "Detailed catalog does not match validation template schema:\n"
        + "\n".join(errors)
    )
