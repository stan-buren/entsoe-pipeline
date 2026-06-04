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

from entsoe_pipeline.fms_metadata.core.classifier import classify_folder
from entsoe_pipeline.fms_metadata.core.domain import ingest_domain_metadata
from entsoe_pipeline.fms_metadata.core.generation_data import get_generation_timestamp
from entsoe_pipeline.fms_metadata.core.legacy import ingest_legacy_metadata
from entsoe_pipeline.fms_metadata.core.overview import ingest_overview_metadata
from entsoe_pipeline.fms_metadata.core.overview_tree import (
    ingest_overview_tree_metadata,
)

__all__ = [
    "classify_folder",
    "get_generation_timestamp",
    "ingest_domain_metadata",
    "ingest_legacy_metadata",
    "ingest_overview_metadata",
    "ingest_overview_tree_metadata",
]
