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

"""ENTSO-E FMS Core Metadata Ingestion Engine Package.

Provides unified, modular orchestrators for active data domains classification,
global overview manifest discovery, and deep metadata cataloging.
"""

from __future__ import annotations

from entsoe_pipeline.fms_metadata.core.domain_classifier import classify_folder
from entsoe_pipeline.fms_metadata.core.domain_metadata_crawler import (
    ingest_domain_metadata,
)
from entsoe_pipeline.fms_metadata.core.ftp_map_collector import ingest_overview_metadata
from entsoe_pipeline.fms_metadata.core.job_config_builder import (
    build_custom_domains_config,
    build_default_domains_config,
    build_domains_checklist,
    build_extended_domains_config,
)
from entsoe_pipeline.fms_metadata.core.legacy_metadata_crawler import (
    ingest_all_legacy_metadata,
    ingest_legacy_metadata,
)
from entsoe_pipeline.fms_metadata.core.sizes import compile_sizes_report
from entsoe_pipeline.logger.core.generated_at import (
    get_generated_at_timestamp as get_generation_timestamp,
)
from entsoe_pipeline.logger.core.warning import (
    get_my_entsoe_domains_warning,
    get_yaml_warning,
)

__all__ = [
    "build_custom_domains_config",
    "build_default_domains_config",
    "build_domains_checklist",
    "build_extended_domains_config",
    "classify_folder",
    "compile_sizes_report",
    "get_generation_timestamp",
    "get_my_entsoe_domains_warning",
    "get_yaml_warning",
    "ingest_all_legacy_metadata",
    "ingest_domain_metadata",
    "ingest_legacy_metadata",
    "ingest_overview_metadata",
]
