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

"""ENTSO-E folder classification configuration parser and schema definitions.

This module provides the declarative schema models to parse the folder
classification rules and legacy archive specifications from `entsoe-classifier.yml`.
These rules map active folder names from the ENTSO-E FMS (File Management System)
transparency platform to business-specific analytical domains.

Typical usage example:

    config = ClassifierConfig._from_yaml()
    for rule in config.rules:
        print(f"Domain {rule.domain} patterns: {rule.patterns}")
"""

from __future__ import annotations

from dataclasses import dataclass

import yaml


@dataclass(frozen=True)
class LegacyRule:
    """Immutable classification rule mapping legacy archive specifications.

    Attributes:
        archive (str): Target archive identifier (e.g. 'R3_Archives').
        release_name (str): Official name of the release.
        decommission_status (str): Current status and decommission description.
        description (str): Business context and information about the release.
        patterns (list[str]): Key phrases in folder name to map to this archive.
    """

    archive: str
    release_name: str
    decommission_status: str
    description: str
    patterns: list[str]


@dataclass(frozen=True)
class ClassifierItem:
    """Immutable data item schema representing a specific publications folder configuration."""

    name: str
    fms_name: str


@dataclass(frozen=True)
class ClassifierConfig:
    """Master configuration class representing folder classification rules.

    Attributes:
        domain_order (list[str]): Standardized order list of the data domains.
        fallback_domain (str): Fallback domain identifier on no patterns matched.
        domains (dict[str, dict[str, ClassifierItem]]): Structured mapping of domains to folders.
        legacy_rules (list[LegacyRule]): Rules defining legacy archives.
    """

    domain_order: list[str]
    fallback_domain: str
    domains: dict[str, dict[str, ClassifierItem]]
    legacy_rules: list[LegacyRule]

    @classmethod
    def _from_yaml(cls) -> ClassifierConfig:
        """Loads and parses the classifier configurations.

        Returns:
            ClassifierConfig: The loaded classifier configuration.

        Raises:
            FileNotFoundError: If the configuration files are not present.
        """
        from entsoe_pipeline.config.paths import CLASSIFIER_YML, LEGACY_CLASSIFIER_YML

        if not CLASSIFIER_YML.exists():
            raise FileNotFoundError(
                f"Classifier configuration file not found at: {CLASSIFIER_YML}"
            )
        if not LEGACY_CLASSIFIER_YML.exists():
            raise FileNotFoundError(
                f"Legacy classifier configuration file not found at: {LEGACY_CLASSIFIER_YML}"
            )

        with CLASSIFIER_YML.open(encoding="utf-8") as f:
            domains_data = yaml.safe_load(f) or {}

        with LEGACY_CLASSIFIER_YML.open(encoding="utf-8") as f:
            legacy_data = yaml.safe_load(f) or {}

        raw_domains = domains_data.get("domains", {})
        domains = {}
        for domain, items in raw_domains.items():
            domains[domain] = {}
            for key, val in items.items():
                domains[domain][key] = ClassifierItem(
                    name=str(val.get("name", "")),
                    fms_name=str(val.get("fms_name", "")),
                )

        domain_order = list(domains.keys())
        fallback_domain = "OtherMarketInformation"

        raw_archives = legacy_data.get("archives", {})
        legacy_rules = []
        for archive_name, archive_info in raw_archives.items():
            release_name = str(archive_info.get("release_name", ""))
            decommission_status = str(archive_info.get("decommission_status", ""))
            description = str(archive_info.get("description", ""))
            raw_pubs = archive_info.get("publications", {})
            patterns = [
                str(pub.get("fms_name", ""))
                for pub in raw_pubs.values()
                if pub.get("fms_name")
            ]

            legacy_rules.append(
                LegacyRule(
                    archive=archive_name,
                    release_name=release_name,
                    decommission_status=decommission_status,
                    description=description,
                    patterns=patterns,
                )
            )

        return cls(
            domain_order=domain_order,
            fallback_domain=fallback_domain,
            domains=domains,
            legacy_rules=legacy_rules,
        )
