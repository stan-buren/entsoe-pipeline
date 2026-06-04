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

Exposes automated metadata crawler orchestrators.
"""

from entsoe_pipeline.fms_metadata.ingestion.balancing_ingest import (
    ingest_balancing_metadata,
)
from entsoe_pipeline.fms_metadata.ingestion.generation_ingest import (
    ingest_generation_metadata,
)
from entsoe_pipeline.fms_metadata.ingestion.legacy_ingest import (
    ingest_all_legacy_metadata,
)
from entsoe_pipeline.fms_metadata.ingestion.load_ingest import ingest_load_metadata
from entsoe_pipeline.fms_metadata.ingestion.market_ingest import ingest_market_metadata
from entsoe_pipeline.fms_metadata.ingestion.operations_ingest import (
    ingest_operations_metadata,
)
from entsoe_pipeline.fms_metadata.ingestion.other_market_information_ingest import (
    ingest_other_market_information_metadata,
)
from entsoe_pipeline.fms_metadata.ingestion.outages_ingest import (
    ingest_outages_metadata,
)
from entsoe_pipeline.fms_metadata.ingestion.overview_ingest import ingest_fms_metadata
from entsoe_pipeline.fms_metadata.ingestion.overview_tree_ingest import (
    ingest_fms_overview_tree,
)
from entsoe_pipeline.fms_metadata.ingestion.transmission_ingest import (
    ingest_transmission_metadata,
)

__all__ = [
    "ingest_all_legacy_metadata",
    "ingest_balancing_metadata",
    "ingest_fms_metadata",
    "ingest_fms_overview_tree",
    "ingest_generation_metadata",
    "ingest_load_metadata",
    "ingest_market_metadata",
    "ingest_operations_metadata",
    "ingest_other_market_information_metadata",
    "ingest_outages_metadata",
    "ingest_transmission_metadata",
]
