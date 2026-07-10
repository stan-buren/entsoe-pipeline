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

"""ENTSO-E FMS Ingestion Module.

Exposes automated metadata crawler orchestrators and CLI runners.
"""

from __future__ import annotations

from entsoe_pipeline.fms_metadata.ingestion.fms_metadata_ingest import (
    ingest_metadata,
)
from entsoe_pipeline.fms_metadata.ingestion.overview_ingest import (
    ingest_fms_metadata,
)
from entsoe_pipeline.fms_metadata.ingestion.sizes_ingest import (
    ingest_all_catalog_sizes,
)
from entsoe_pipeline.fms_metadata.ingestion.undocumented_folders import (
    generate_undocumented_folders_report,
)
from entsoe_pipeline.fms_metadata.ingestion.unseen_publications import (
    generate_unseen_publications_report,
)

__all__ = [
    "generate_undocumented_folders_report",
    "generate_unseen_publications_report",
    "ingest_all_catalog_sizes",
    "ingest_fms_metadata",
    "ingest_metadata",
]
