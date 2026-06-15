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
class ExclusionRule:
    """Immutable sub-rule to dynamically redirect folder domains on overlaps.

    Attributes:
        patterns (list[str]): Key phrases in lowercase that trigger redirect.
        redirect_to (str): Target domain to redirect, if matched.
    """

    patterns: list[str]
    redirect_to: str


@dataclass(frozen=True)
class ClassificationRule:
    """Immutable classification rule mapping patterns to analytical domains.

    Attributes:
        domain (str): Target data domain (e.g., 'Load', 'Transmission').
        patterns (list[str]): Lowercase keywords to inspect in folder name.
        exclusions (list[ExclusionRule]): Exclusions redirecting domain context.
    """

    domain: str
    patterns: list[str]
    exclusions: list[ExclusionRule]


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
class ClassifierConfig:
    """Master configuration class representing folder classification rules.

    Attributes:
        domain_order (list[str]): Standardized order list of the data domains.
        fallback_domain (str): Fallback domain identifier on no patterns matched.
        rules (list[ClassificationRule]): Pattern matching and exclusion rules.
        legacy_rules (list[LegacyRule]): Rules defining legacy archives.
    """

    domain_order: list[str]
    fallback_domain: str
    rules: list[ClassificationRule]
    legacy_rules: list[LegacyRule]

    @classmethod
    def _from_yaml(cls) -> ClassifierConfig:
        """Loads and parses the classifier configuration from entsoe-classifier.yml.

        Returns:
            ClassifierConfig: The loaded classifier configuration.

        Raises:
            FileNotFoundError: If the entsoe-classifier.yml is not present.
        """
        from entsoe_pipeline.config.paths import CLASSIFIER_YML

        config_file = CLASSIFIER_YML
        if not config_file.exists():
            raise FileNotFoundError(
                f"Classifier configuration file not found at: {config_file}"
            )

        with config_file.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        domain_order = list(data.get("domain_order", []))
        fallback_domain = str(data.get("fallback_domain", "OtherMarketInformation"))
        raw_rules = data.get("rules", [])

        rules = []
        for r in raw_rules:
            domain = str(r.get("domain", ""))
            patterns = [str(pat) for pat in r.get("patterns", [])]
            raw_exclusions = r.get("exclusions", [])

            exclusions = []
            for exc in raw_exclusions:
                exc_patterns = [str(pat) for pat in exc.get("patterns", [])]
                redirect_to = str(exc.get("redirect_to", ""))
                if redirect_to:
                    exclusions.append(
                        ExclusionRule(patterns=exc_patterns, redirect_to=redirect_to)
                    )

            if domain:
                rules.append(
                    ClassificationRule(
                        domain=domain,
                        patterns=patterns,
                        exclusions=exclusions,
                    )
                )

        raw_legacy_rules = data.get("legacy_rules", [])
        legacy_rules = []
        for lr in raw_legacy_rules:
            archive = str(lr.get("archive", ""))
            release_name = str(lr.get("release_name", ""))
            decommission_status = str(lr.get("decommission_status", ""))
            description = str(lr.get("description", ""))
            patterns = [str(pat) for pat in lr.get("patterns", [])]

            if archive:
                legacy_rules.append(
                    LegacyRule(
                        archive=archive,
                        release_name=release_name,
                        decommission_status=decommission_status,
                        description=description,
                        patterns=patterns,
                    )
                )

        return cls(
            domain_order=domain_order,
            fallback_domain=fallback_domain,
            rules=rules,
            legacy_rules=legacy_rules,
        )
