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

"""ENTSO-E active folder data domain classification logic.

Utilizes descriptive pattern matching on the folder name string to assign
active folders to one of the 8 core ENTSO-E data domains using dynamic rules
loaded from entsoe-classifier.yml.
"""

from __future__ import annotations

import logging

from entsoe_pipeline import get_classifier_config

# Setup scoped logger strictly to our package namespace to prevent polluting root
logger = logging.getLogger("entsoe_pipeline.fms_metadata.core.domain_classifier")


def classify_folder(folder_name: str) -> str:
    """Classifies an ENTSO-E active folder name into its specific analytical domain.

    Matches folder_name against known fms_name prefixes in our domains mapping configuration.
    If not matched, falls back to legacy check or default fallback domain.

    Args:
        folder_name: Remote FMS directory name (e.g. 'ActualTotalLoad_6.1.A_r3').

    Returns:
        The assigned domain name (e.g. 'Load', 'Transmission').
    """
    config = get_classifier_config()
    folder_name_lower = folder_name.lower()

    # 1. Iterate through domains and items to check for a starting prefix match
    for domain, items in config.domains.items():
        for item in items.values():
            fms_prefix = item.fms_name.lower()
            if folder_name_lower.startswith(fms_prefix):
                return domain

    # 2. Fallback to default domain
    logger.debug(
        "Folder '%s' did not match any domain prefix. Falling back to '%s'",
        folder_name,
        config.fallback_domain,
    )
    return config.fallback_domain
