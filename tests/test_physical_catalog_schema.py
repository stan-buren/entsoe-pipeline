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

"""Automated quality gate verification suite for physical metadata catalogs.

Crawls all environment catalogs recursively and asserts strict conformance
to the declarative schema contract in config/entsoe_physical_catalog_template.yml.
"""

from __future__ import annotations

import re

from datetime import datetime

import yaml

from entsoe_pipeline import PHYSICAL_CATALOG_DIR, PHYSICAL_CATALOG_TEMPLATE_YML

# =============================================================================
# Helper Utilities & Parsing Rules
# =============================================================================


def is_valid_iso_datetime(dt_str: str) -> bool:
    """Verifies if a string is a valid ISO 8601 UTC datetime format."""
    try:
        # Standard formats: 2026-05-28T14:12:41Z or with milliseconds/fractional seconds
        dt_str = dt_str.replace("Z", "+00:00")
        datetime.fromisoformat(dt_str)
    except (ValueError, TypeError):
        return False
    else:
        return True


def is_valid_xxhash(hash_str: str) -> bool:
    """Checks if a string conforms to a standard 128-bit xxhash hex checksum pattern."""
    if not isinstance(hash_str, str):
        return False
    return bool(re.match(r"^[a-f0-9]{32}$", hash_str))


# =============================================================================
# Test Suite Execution
# =============================================================================


def test_physical_catalog_schema_conformance() -> None:
    """Recursively validates all physical catalogs against the SSOT template schema."""
    # 1. Arrange: Assert configuration files and directories exist
    assert PHYSICAL_CATALOG_TEMPLATE_YML.exists(), (
        f"Validation template schema not found at: {PHYSICAL_CATALOG_TEMPLATE_YML}"
    )
    assert PHYSICAL_CATALOG_DIR.exists(), (
        f"Physical catalogs root directory not found at: {PHYSICAL_CATALOG_DIR}"
    )

    # Load and parse the declarative schema config contract
    with PHYSICAL_CATALOG_TEMPLATE_YML.open(encoding="utf-8") as f:
        schema = yaml.safe_load(f) or {}

    assert "schema_version" in schema, (
        "Declarative schema is missing 'schema_version' attribute."
    )

    # 2. Act: Crawl and find all catalog files recursively
    catalog_files = list(PHYSICAL_CATALOG_DIR.glob("**/*.yml"))
    assert catalog_files, (
        f"No physical catalog YAML files discovered under: {PHYSICAL_CATALOG_DIR}"
    )

    # 3. Assert: Validate catalog files dynamically against contract rules
    for catalog_file in catalog_files:
        with catalog_file.open(encoding="utf-8") as f:
            catalog = yaml.safe_load(f) or {}

        # Determine target context based on path folder structure

        # --- A. Root Properties Verification ---
        # Assert required root keys are present
        assert "generated_at" in catalog, (
            f"Missing 'generated_at' root key in {catalog_file.name}"
        )
        assert "total_api_requests" in catalog, (
            f"Missing 'total_api_requests' root key in {catalog_file.name}"
        )
        assert "folders" in catalog, (
            f"Missing 'folders' root key in {catalog_file.name}"
        )

        # Assert correct data types
        assert isinstance(catalog["generated_at"], str), (
            f"'generated_at' is not a string in {catalog_file.name}"
        )
        assert is_valid_iso_datetime(catalog["generated_at"]), (
            f"Invalid ISO datetime '{catalog['generated_at']}' in {catalog_file.name}"
        )
        assert isinstance(catalog["total_api_requests"], int), (
            f"'total_api_requests' is not an integer in {catalog_file.name}"
        )
        assert catalog["total_api_requests"] >= 0, (
            f"'total_api_requests' is negative in {catalog_file.name}"
        )
        assert isinstance(catalog["folders"], dict), (
            f"'folders' is not a dictionary in {catalog_file.name}"
        )

        # --- B. Folders Mapping & Physical Sizes Verification ---
        for folder_name, folder_meta in catalog["folders"].items():
            assert isinstance(folder_meta, dict), (
                f"Folder metadata for '{folder_name}' is not a dict "
                f"in {catalog_file.name}"
            )

            # Validate folder path formatting
            assert "folder_path" in folder_meta, (
                f"Missing 'folder_path' in folder '{folder_name}' "
                f"in {catalog_file.name}"
            )
            assert isinstance(folder_meta["folder_path"], str), (
                f"'folder_path' is not a string in folder '{folder_name}'"
            )
            assert folder_meta["folder_path"].startswith("/"), (
                f"'folder_path' does not start with '/' in '{folder_name}'"
            )
            assert folder_meta["folder_path"].endswith("/"), (
                f"'folder_path' does not end with '/' in '{folder_name}'"
            )

            # Validate item counting
            assert "item_count" in folder_meta, (
                f"Missing 'item_count' in folder '{folder_name}' in {catalog_file.name}"
            )
            assert isinstance(folder_meta["item_count"], int), (
                f"'item_count' is not an integer in folder '{folder_name}'"
            )
            assert folder_meta["item_count"] >= 0, (
                f"'item_count' is negative in folder '{folder_name}'"
            )

            # Validate list of files exists
            assert "files" in folder_meta, (
                f"Missing 'files' list in folder '{folder_name}' in {catalog_file.name}"
            )
            assert isinstance(folder_meta["files"], list), (
                f"'files' is not a list in folder '{folder_name}'"
            )

            # Invariant check: item count must match files list length
            assert folder_meta["item_count"] == len(folder_meta["files"]), (
                f"Inconsistent metadata: item_count "
                f"({folder_meta['item_count']}) does not match actual "
                f"files list size ({len(folder_meta['files'])}) "
                f"in folder '{folder_name}'"
            )

            # Validate size properties block
            assert "sizes" in folder_meta, (
                f"Missing 'sizes' block in folder '{folder_name}' "
                f"in {catalog_file.name}"
            )
            sizes = folder_meta["sizes"]
            assert isinstance(sizes, dict), (
                f"'sizes' is not a dictionary in folder '{folder_name}'"
            )

            # Verify original sizes exist
            assert "original" in sizes, (
                f"Missing 'original' sizes in folder '{folder_name}' "
                f"in {catalog_file.name}"
            )
            orig = sizes["original"]
            assert isinstance(orig, dict), (
                f"original sizes is not a dict in folder '{folder_name}'"
            )
            for k in ["bytes", "bits", "mb"]:
                assert k in orig, (
                    f"Missing '{k}' in original sizes in folder '{folder_name}'"
                )
                assert isinstance(orig[k], (int, float)), (
                    f"original sizes.{k} is not numeric in folder '{folder_name}'"
                )
                assert orig[k] >= 0, (
                    f"original sizes.{k} is negative in folder '{folder_name}'"
                )

            # Verify optional compressed sizes if present
            if "compressed" in sizes:
                comp = sizes["compressed"]
                assert isinstance(comp, dict), (
                    f"compressed sizes is not a dict in folder '{folder_name}'"
                )
                for k in ["bytes", "bits", "mb"]:
                    assert k in comp, (
                        f"Missing '{k}' in compressed sizes in folder '{folder_name}'"
                    )
                    assert isinstance(comp[k], (int, float)), (
                        f"compressed sizes.{k} is not numeric in folder '{folder_name}'"
                    )
                    assert comp[k] >= 0, (
                        f"compressed sizes.{k} is negative in folder '{folder_name}'"
                    )

            # --- C. Nested File Specifications Verification ---
            for file_item in folder_meta["files"]:
                assert isinstance(file_item, dict), (
                    f"File entry is not a dictionary in folder '{folder_name}'"
                )

                # Verify name, uuid id, and hashing
                assert "name" in file_item, (
                    f"Missing file 'name' in folder '{folder_name}'"
                )
                assert isinstance(file_item["name"], str), (
                    f"file name is not a string in folder '{folder_name}'"
                )
                assert file_item["name"].strip(), (
                    f"file name is empty in folder '{folder_name}'"
                )

                assert "file_id" in file_item, (
                    f"Missing 'file_id' for file '{file_item['name']}'"
                )
                assert isinstance(file_item["file_id"], str), (
                    f"'file_id' is not a string for file '{file_item['name']}'"
                )

                assert "xxhash" in file_item, (
                    f"Missing 'xxhash' checksum for file '{file_item['name']}'"
                )
                assert is_valid_xxhash(file_item["xxhash"]), (
                    f"Invalid xxhash '{file_item['xxhash']}' for "
                    f"file '{file_item['name']}' in {catalog_file.name}"
                )

                # Verify updating timestamp
                assert "last_updated" in file_item, (
                    f"Missing 'last_updated' timestamp for file '{file_item['name']}'"
                )
                assert is_valid_iso_datetime(file_item["last_updated"]), (
                    f"Invalid ISO datetime 'last_updated' "
                    f"'{file_item['last_updated']}' for file "
                    f"'{file_item['name']}'"
                )

                # Verify file-level sizes
                assert "sizes" in file_item, (
                    f"Missing 'sizes' block for file '{file_item['name']}'"
                )
                f_sizes = file_item["sizes"]
                assert isinstance(f_sizes, dict), (
                    f"file sizes is not a dict for file '{file_item['name']}'"
                )

                assert "original" in f_sizes, (
                    f"Missing original sizes for file '{file_item['name']}'"
                )
                f_orig = f_sizes["original"]
                assert isinstance(f_orig, dict), (
                    f"file original sizes is not a dict for file '{file_item['name']}'"
                )
                for k in ["bytes", "bits", "mb"]:
                    assert k in f_orig, (
                        f"Missing '{k}' in original sizes for "
                        f"file '{file_item['name']}'"
                    )
                    assert isinstance(f_orig[k], (int, float)), (
                        f"file original sizes.{k} is not numeric"
                    )
                    assert f_orig[k] >= 0, f"file original sizes.{k} is negative"

                if "compressed" in f_sizes:
                    f_comp = f_sizes["compressed"]
                    assert isinstance(f_comp, dict), (
                        f"file compressed sizes is not a dict "
                        f"for file '{file_item['name']}'"
                    )
                    for k in ["bytes", "bits", "mb"]:
                        assert k in f_comp, (
                            f"Missing '{k}' in compressed sizes "
                            f"for file '{file_item['name']}'"
                        )
                        assert isinstance(f_comp[k], (int, float)), (
                            f"file compressed sizes.{k} is not numeric"
                        )
                        assert f_comp[k] >= 0, f"file compressed sizes.{k} is negative"
