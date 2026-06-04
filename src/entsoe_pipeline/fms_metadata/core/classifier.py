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
logger = logging.getLogger("entsoe_pipeline.fms_metadata.core.classifier")


def classify_folder(folder_name: str) -> str:
    """Classifies an ENTSO-E active folder name into its specific analytical domain.

    Utilizes descriptive pattern matching on the folder name string based on
    dynamic rules defined in entsoe-classifier.yml.

    Args:
        folder_name: Remote FMS directory name (e.g. 'ActualTotalLoad_6.1.A_r3').

    Returns:
        The assigned domain name (e.g. 'Load', 'Transmission').
    """
    name_lower = folder_name.lower()
    config = get_classifier_config()

    # Iterate through priority-ordered classification rules
    for rule in config.rules:
        # Check if any main patterns match the folder name
        if any(pat.lower() in name_lower for pat in rule.patterns):
            # Evaluate potential contextual exclusions (redirection sub-rules)
            for exc in rule.exclusions:
                # If exclusions has patterns and any matches,
                # OR if exclusions patterns is empty (match all)
                if not exc.patterns or any(
                    pat.lower() in name_lower for pat in exc.patterns
                ):
                    return exc.redirect_to
            return rule.domain

    # Fallback to the configured default domain on no patterns matched
    logger.debug("Folder '%s' fell back to '%s'", folder_name, config.fallback_domain)
    return config.fallback_domain
