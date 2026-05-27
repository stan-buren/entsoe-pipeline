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

"""Unit Tests for FMS Metadata Ingestion Module.

Verifies folder domain classification, structured environment metadata crawling,
and YAML serialization logic using the 3A (Arrange, Act, Assert) pattern.
"""

from __future__ import annotations

from unittest.mock import MagicMock, mock_open, patch

import pytest
import yaml

from entsoe_pipeline.fms_metadata.overview_ingest import (
    classify_folder,
    fetch_environment_metadata,
    ingest_fms_metadata,
)

# =============================================================================
# 1. UNIT TESTS: DOMAIN CLASSIFICATION LOGIC
# =============================================================================


@pytest.mark.parametrize(
    ("folder_name", "expected_domain"),
    (
        ("ActualTotalLoad_6.1.A_r3", "Load"),
        ("YearAheadForecastMargin_8.1_r3", "Load"),
        ("ActualGenerationOutputPerGenerationUnit_16.1.A_r3", "Generation"),
        ("ProductionAndGenerationUnits_r3", "Generation"),
        ("InstalledGenerationCapacityPerProductionUnit_14.1.B_r3", "Generation"),
        ("UnavailabilityOfOffshoreGrid_10.1.C_r3", "Outages"),
        ("CrossBorderCapacityForDcLinksIntradayTransferLimits_11.3_r3", "Transmission"),
        ("PhysicalFlows_12.1.G_r3", "Transmission"),
        ("AggregatedBalancingEnergyBids_12.3.E_r3", "Balancing"),
        ("ImbalancePrices_17.1.G_r3", "Balancing"),
        ("EnergyPrices_12.1.D_r3", "Market"),
        ("AuctionRevenue_12.1.A_r3", "Market"),
        ("Algorithm_12.3.K_r3", "Operations"),
        ("ApprovedMethodologies_12.3.J_r3", "Operations"),
        ("RedispatchingCrossBorder_13.1.A_r3.1", "Operations"),
        ("Export_log_r3.csv", "OtherMarketInformation"),
        ("UnexpectedFolder_r3", "OtherMarketInformation"),
    ),
)
def test_classify_folder_returns_correct_domain(
    folder_name: str,
    expected_domain: str,
) -> None:
    """Verifies folder names are correctly classified into domain buckets."""
    # -------------------------------------------------------------------------
    # ARRANGE
    # -------------------------------------------------------------------------
    # Parameters are arranged via pytest.mark.parametrize

    # -------------------------------------------------------------------------
    # ACT
    # -------------------------------------------------------------------------
    actual_domain = classify_folder(folder_name)

    # -------------------------------------------------------------------------
    # ASSERT
    # -------------------------------------------------------------------------
    assert actual_domain == expected_domain


# =============================================================================
# 2. UNIT TESTS: METADATA HARVESTING
# =============================================================================


@patch("entsoe_pipeline.fms_metadata.overview_ingest.ls_fms")
@patch("entsoe_pipeline.fms_metadata.overview_ingest.create_fms_client")
def test_fetch_environment_metadata_crawls_and_groups_folders(
    mock_create_client: MagicMock,
    mock_ls_fms: MagicMock,
) -> None:
    """Verifies folder listing, sorting, and classification."""
    # -------------------------------------------------------------------------
    # ARRANGE
    # -------------------------------------------------------------------------
    mock_client = MagicMock()
    mock_create_client.return_value = mock_client

    # Set up mock ls_fms responses:
    # first call returns active folders, second call returns legacy folders
    mock_ls_fms.side_effect = [
        [
            "ActualTotalLoad_6.1.A_r3",
            "EnergyPrices_12.1.D_r3",
            "UnavailabilityOfOffshoreGrid_10.1.C_r3",
        ],
        ["BalanceManagementCsv_r1", "OutagesXml_r1"],
    ]

    # -------------------------------------------------------------------------
    # ACT
    # -------------------------------------------------------------------------
    metadata = fetch_environment_metadata("IOP")

    # -------------------------------------------------------------------------
    # ASSERT
    # -------------------------------------------------------------------------
    assert metadata["description"] == "ENTSO-E Integration/Test Platform"

    root_dirs = metadata["root_directories"]
    assert len(root_dirs) == 2

    # Assert Active Folders (/TP_export/)
    active_dir = root_dirs[0]
    assert active_dir["name"] == "TP_export"
    assert active_dir["item_count"] == 3
    assert "Load" in active_dir["domains"]
    assert "Market" in active_dir["domains"]
    assert "Outages" in active_dir["domains"]
    assert active_dir["domains"]["Load"] == ["ActualTotalLoad_6.1.A_r3"]
    assert active_dir["domains"]["Market"] == ["EnergyPrices_12.1.D_r3"]
    outages = active_dir["domains"]["Outages"]
    assert outages == ["UnavailabilityOfOffshoreGrid_10.1.C_r3"]

    # Assert Legacy Folders (/TP_Legacy_Publications/)
    legacy_dir = root_dirs[1]
    assert legacy_dir["name"] == "TP_Legacy_Publications"
    assert legacy_dir["item_count"] == 2
    assert legacy_dir["folders"] == ["BalanceManagementCsv_r1", "OutagesXml_r1"]


# =============================================================================
# 3. UNIT TESTS: YAML SERIALIZATION
# =============================================================================


@patch("entsoe_pipeline.fms_metadata.overview_ingest.OVERVIEW_YML")
@patch("entsoe_pipeline.fms_metadata.overview_ingest.fetch_environment_metadata")
def test_ingest_fms_metadata_persists_to_yaml(
    mock_fetch_metadata: MagicMock,
    mock_overview_yml: MagicMock,
) -> None:
    """Verifies that orchestration crawls IOP/PROD and dumps to YAML."""
    # -------------------------------------------------------------------------
    # ARRANGE
    # -------------------------------------------------------------------------
    dummy_iop = {"description": "IOP description", "root_directories": []}
    dummy_prod = {"description": "Prod description", "root_directories": []}
    mock_fetch_metadata.side_effect = [dummy_iop, dummy_prod]

    m_open = mock_open()
    mock_overview_yml.open = m_open

    # -------------------------------------------------------------------------
    # ACT
    # -------------------------------------------------------------------------
    ingest_fms_metadata()

    # -------------------------------------------------------------------------
    # ASSERT
    # -------------------------------------------------------------------------
    # Ensure both environment crawlers were triggered
    assert mock_fetch_metadata.call_count == 2
    mock_fetch_metadata.assert_any_call("IOP")
    mock_fetch_metadata.assert_any_call("PROD")

    # Verify that the SSOT YAML file was opened for writing
    mock_overview_yml.open.assert_called_once_with("w", encoding="utf-8")

    # Retrieve the string written to the file stream
    written_data = "".join(call[0][0] for call in m_open().write.call_args_list)

    # Assert serialized content is a valid YAML representation
    parsed_yaml = yaml.safe_load(written_data)
    assert "environments" in parsed_yaml
    assert parsed_yaml["environments"]["IOP"] == dummy_iop
    assert parsed_yaml["environments"]["Prod"] == dummy_prod
