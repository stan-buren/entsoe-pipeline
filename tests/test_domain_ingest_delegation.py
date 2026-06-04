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

"""Unit Tests for FMS Domain and Overview Ingestion Orchestrators.

Consolidates all metadata ingestion delegation tests into a single parameter-driven
test suite to strictly avoid code duplication across separate test modules.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from entsoe_pipeline.fms_metadata.ingestion.balancing_ingest import (
    ingest_balancing_metadata,
)
from entsoe_pipeline.fms_metadata.ingestion.generation_ingest import (
    ingest_generation_metadata,
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
from entsoe_pipeline.fms_metadata.ingestion.transmission_ingest import (
    ingest_transmission_metadata,
)

if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.mark.parametrize(
    ("ingest_func", "domain_name", "patch_target"),
    (
        (
            ingest_load_metadata,
            "Load",
            "entsoe_pipeline.fms_metadata.ingestion.load_ingest.ingest_domain_metadata",
        ),
        (
            ingest_market_metadata,
            "Market",
            "entsoe_pipeline.fms_metadata.ingestion.market_ingest.ingest_domain_metadata",
        ),
        (
            ingest_generation_metadata,
            "Generation",
            "entsoe_pipeline.fms_metadata.ingestion.generation_ingest.ingest_domain_metadata",
        ),
        (
            ingest_transmission_metadata,
            "Transmission",
            "entsoe_pipeline.fms_metadata.ingestion.transmission_ingest.ingest_domain_metadata",
        ),
        (
            ingest_balancing_metadata,
            "Balancing",
            "entsoe_pipeline.fms_metadata.ingestion.balancing_ingest.ingest_domain_metadata",
        ),
        (
            ingest_outages_metadata,
            "Outages",
            "entsoe_pipeline.fms_metadata.ingestion.outages_ingest.ingest_domain_metadata",
        ),
        (
            ingest_operations_metadata,
            "Operations",
            "entsoe_pipeline.fms_metadata.ingestion.operations_ingest.ingest_domain_metadata",
        ),
        (
            ingest_other_market_information_metadata,
            "OtherMarketInformation",
            "entsoe_pipeline.fms_metadata.ingestion.other_market_information_ingest.ingest_domain_metadata",
        ),
    ),
)
def test_domain_orchestrators_delegate_to_core(
    ingest_func: Callable[[], None],
    domain_name: str,
    patch_target: str,
) -> None:
    """Verifies that orchestrators delegate correctly to core engine.

    Args:
        ingest_func: The specific domain metadata gatherer function.
        domain_name: The expected target domain catalog string.
        patch_target: The module-level import target for mocking.
    """
    # -------------------------------------------------------------------------
    # ARRANGE: Mock the internal ingest call inside the specific module
    # -------------------------------------------------------------------------
    with patch(patch_target) as mock_ingest_core:
        # -------------------------------------------------------------------------
        # ACT: Trigger the specific domain ingestion orchestrator
        # -------------------------------------------------------------------------
        ingest_func()

        # -------------------------------------------------------------------------
        # ASSERT: Verify it delegates cleanly to the core with the correct domain
        # -------------------------------------------------------------------------
        mock_ingest_core.assert_called_once_with(domain_name)


@patch(
    "entsoe_pipeline.fms_metadata.ingestion.overview_ingest.ingest_overview_metadata"
)
def test_ingest_fms_metadata_delegates_to_core(
    mock_ingest_core: MagicMock,
) -> None:
    """Verifies that global orchestrator delegates to core overview crawler."""
    # -------------------------------------------------------------------------
    # ACT: Trigger the global overview metadata crawling process
    # -------------------------------------------------------------------------
    ingest_fms_metadata()

    # -------------------------------------------------------------------------
    # ASSERT: Verify it delegates cleanly to ingest_overview_metadata
    # -------------------------------------------------------------------------
    mock_ingest_core.assert_called_once()
