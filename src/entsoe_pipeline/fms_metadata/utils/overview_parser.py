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

"""Parser module for the ENTSO-E FMS overview.yml catalog.

Responsible for reading the structured overview manifest and resolving active
folder listings for analytical domains dynamically across platforms, as well as
parsing filenames representation ranges.
"""

from __future__ import annotations

import re

from typing import Any

import yaml

from entsoe_pipeline import get_classifier_config
from entsoe_pipeline.config.paths import OVERVIEW_YML


def get_domain_folders(domain_name: str, env_name: str) -> list[str]:
    """Dynamically retrieves folder names for a domain from overview.yml.

    Args:
        domain_name: The target ENTSO-E data domain (e.g. 'Load', 'Generation').
        env_name: The platform environment target name ('IOP' or 'PROD').

    Returns:
        list[str]: Sorted list of remote folder names mapped to the domain.

    Raises:
        FileNotFoundError: If the overview.yml catalog file does not exist.
        ValueError: If the environment key or root directory is not present.
    """
    if not OVERVIEW_YML.exists():
        raise FileNotFoundError(
            f"Overview catalog file not found at: {OVERVIEW_YML}. "
            "Please run overview_ingest first."
        )

    with OVERVIEW_YML.open("r", encoding="utf-8") as f:
        overview = yaml.safe_load(f) or {}

    environments = overview.get("environments", {})
    # Match environment case-insensitively to tolerate 'prod' vs 'Prod' vs 'PROD'
    env_key = next((k for k in environments if k.upper() == env_name.upper()), None)
    if not env_key:
        raise ValueError(
            f"Environment '{env_name}' not found in overview.yml environments: "
            f"{list(environments.keys())}"
        )

    root_directories = environments[env_key].get("root_directories", [])
    # Locate TP_export folder which holds categorized active domains
    tp_export = next(
        (d for d in root_directories if d.get("name") == "TP_export"),
        None,
    )
    if not tp_export:
        raise ValueError(
            f"Active root directory 'TP_export' not found under environment "
            f"'{env_key}' in overview.yml."
        )

    domains = tp_export.get("domains", {})
    # Match domain case-insensitively to tolerate 'load' vs 'Load'
    domain_key = next((k for k in domains if k.lower() == domain_name.lower()), None)
    if not domain_key:
        return []

    return domains[domain_key]


def get_legacy_archive_folders(archive_name: str, env_name: str) -> list[str]:
    """Dynamically retrieves and filters folder names for a legacy archive.

    Resolves active folder listings for legacy publications, matching folders
    against the patterns declared in the entsoe-classifier.yml rules.

    Args:
        archive_name: Target legacy archive name (e.g. 'R3_Archives').
        env_name: Platform environment target name ('IOP' or 'PROD').

    Returns:
        list[str]: Sorted list of remote folder names mapped to the archive.

    Raises:
        FileNotFoundError: If the overview.yml catalog file does not exist.
        ValueError: If the environment key or legacy folders list is missing.
    """
    if not OVERVIEW_YML.exists():
        raise FileNotFoundError(
            f"Overview catalog file not found at: {OVERVIEW_YML}. "
            "Please run overview_ingest first."
        )

    with OVERVIEW_YML.open("r", encoding="utf-8") as f:
        overview = yaml.safe_load(f) or {}

    environments = overview.get("environments", {})
    env_key = next((k for k in environments if k.upper() == env_name.upper()), None)
    if not env_key:
        raise ValueError(
            f"Environment '{env_name}' not found in overview.yml environments: "
            f"{list(environments.keys())}"
        )

    root_directories = environments[env_key].get("root_directories", [])
    tp_legacy = next(
        (d for d in root_directories if d.get("name") == "TP_Legacy_Publications"),
        None,
    )
    if not tp_legacy:
        raise ValueError(
            f"Legacy root directory 'TP_Legacy_Publications' not found under "
            f"environment '{env_key}' in overview.yml."
        )

    folders = tp_legacy.get("folders", [])

    # Find the corresponding legacy archive rule
    config = get_classifier_config()
    rule = next(
        (r for r in config.legacy_rules if r.archive.lower() == archive_name.lower()),
        None,
    )
    if not rule:
        return []

    matched_folders = [
        folder
        for folder in folders
        if any(pat.lower() in folder.lower() for pat in rule.patterns)
    ]

    # R1 works as a fallback too, if we have folders that didn't match R2/R3 patterns
    if rule.archive == "R1_Archives_CSV_XML":
        # Find all folders that do NOT match R2 or R3 rules
        r2_rule = next(
            (r for r in config.legacy_rules if r.archive == "R2_Archives"), None
        )
        r3_rule = next(
            (r for r in config.legacy_rules if r.archive == "R3_Archives"), None
        )
        r2_pats = r2_rule.patterns if r2_rule else []
        r3_pats = r3_rule.patterns if r3_rule else []

        for folder in folders:
            if folder in matched_folders:
                continue
            matches_r2 = any(pat.lower() in folder.lower() for pat in r2_pats)
            matches_r3 = any(pat.lower() in folder.lower() for pat in r3_pats)
            if not matches_r2 and not matches_r3:
                matched_folders.append(folder)

    return sorted(set(matched_folders))


def parse_months_range(files: list[dict[str, Any]]) -> str:
    """Parses file names to find the oldest and newest months represented.

    Matches patterns like 'YYYY_MM' within filenames, sorts them, and formats
    the overall range.

    Args:
        files: List of file dictionaries containing file names.

    Returns:
        str: Represented date range (e.g., '2015_12 to 2026_12').
    """
    pattern = re.compile(r"(\d{4}_\d{2})")
    months = [match.group(1) for f in files if (match := pattern.search(f["name"]))]

    if not months:
        return "Unknown"

    months.sort()
    return f"{months[0]} to {months[-1]}"
