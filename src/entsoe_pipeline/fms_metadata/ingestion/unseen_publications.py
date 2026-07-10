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

"""Orchestrates detection of unseen active publications from the local overview catalog.

Compares physical folders recorded in overview.yml against the domain classifier
configuration, identifying any configured publications that are missing from FMS.
"""

from __future__ import annotations

import logging

import yaml

from entsoe_pipeline import OVERVIEW_YML, get_classifier_config
from entsoe_pipeline.config.paths import ACTIVE_FMS_METADATA_DIR
from entsoe_pipeline.fms_metadata.utils.serializer import save_yaml_catalog
from entsoe_pipeline.logger import setup_logging
from entsoe_pipeline.logger.core.generated_at import get_generated_at_timestamp

# Setup scoped logger strictly to our package namespace to prevent polluting root
logger = logging.getLogger("entsoe_pipeline.fms_metadata.unseen_publications")


def generate_unseen_publications_report() -> None:
    """Generates the unseen publications drift report based on local overview catalog."""
    logger.info("Starting unseen publications drift detection from local catalog...")

    if not OVERVIEW_YML.exists():
        raise FileNotFoundError(
            f"Local FMS overview catalog not found at: {OVERVIEW_YML}. "
            "Please run overview ingestion first."
        )

    # 1. Load active directories discovered on FTP from overview catalog
    with open(OVERVIEW_YML, encoding="utf-8") as f:
        overview_data = yaml.safe_load(f) or {}

    all_active_folders = set()
    environments = overview_data.get("environments", {})
    for env_meta in environments.values():
        for root_dir in env_meta.get("root_directories", []):
            if root_dir.get("name") == "TP_export":
                for domain_folders in root_dir.get("domains", {}).values():
                    all_active_folders.update(domain_folders)

    # 2. Identify which fms_names in classifier matched the FTP folders
    config = get_classifier_config()
    matched_fms_names = set()

    for folder in sorted(all_active_folders):
        folder_lower = folder.lower()
        for domain, items in config.domains.items():
            for key, item in items.items():
                fms_prefix = item.fms_name.lower()
                if folder_lower.startswith(fms_prefix):
                    matched_fms_names.add(item.fms_name)
                    break

    # 3. Identify unseen publications (Zendesk-only, missing from FMS directories)
    unseen_publications = []
    for domain, items in config.domains.items():
        for key, item in items.items():
            if item.fms_name not in matched_fms_names:
                unseen_publications.append(
                    {
                        "domain": domain,
                        "key": key,
                        "name": item.name,
                        "fms_name": item.fms_name,
                    }
                )

    # 4. Save report using paths SSOT
    ACTIVE_FMS_METADATA_DIR.mkdir(parents=True, exist_ok=True)
    report_file = ACTIVE_FMS_METADATA_DIR / "unseen_publications.yml"

    logger.info(
        "Found %d unseen publications. Saving report to: %s",
        len(unseen_publications),
        report_file,
    )
    save_yaml_catalog(
        report_file,
        {
            "generated_at": get_generated_at_timestamp(),
            "item_count": len(unseen_publications),
            "publications": unseen_publications,
        },
    )


if __name__ == "__main__":
    setup_logging()
    try:
        generate_unseen_publications_report()
    except Exception:
        logger.exception("Unseen publications report generation failed")
