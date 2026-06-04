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

"""Unit Tests for FMS Core Ingestion Orchestration Engine.

Verifies the central metadata gathering and catalog serialization flows
for active FMS domains using the 3A pattern.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from entsoe_pipeline.fms_metadata.core.domain import ingest_domain_metadata


@patch("entsoe_pipeline.fms_metadata.core.domain.save_fms_catalog")
@patch("entsoe_pipeline.fms_metadata.core.domain.list_folder_raw_items")
@patch("entsoe_pipeline.fms_metadata.core.domain.create_fms_client")
@patch("entsoe_pipeline.fms_metadata.core.domain.get_domain_folders")
def test_ingest_domain_metadata_orchestrates_flow(
    mock_get_folders: MagicMock,
    mock_create_client: MagicMock,
    mock_list_items: MagicMock,
    mock_save_catalog: MagicMock,
) -> None:
    """Verifies that ingest_domain_metadata orchestrates FMS ingestion from IOP/PROD."""
    # -------------------------------------------------------------------------
    # ARRANGE: Mock CLI folder resolve and raw API JSON endpoints
    # -------------------------------------------------------------------------
    mock_get_folders.return_value = ["ActualTotalLoad_r3"]
    mock_client = MagicMock()
    mock_create_client.return_value = mock_client
    mock_list_items.return_value = [
        {
            "name": "2026_05_Load.csv",
            "fileId": "uuid-1",
            "size": 100,
            "originalSize": 200,
            "lastUpdatedTimestamp": "2026-05-28T12:00:00Z",
        }
    ]

    # -------------------------------------------------------------------------
    # ACT: Trigger the core multi-environment metadata pipeline for a domain
    # -------------------------------------------------------------------------
    ingest_domain_metadata("Load")

    # -------------------------------------------------------------------------
    # ASSERT: Verify environments are crawled and catalogs are serialized
    # -------------------------------------------------------------------------
    assert mock_get_folders.call_count == 2
    assert mock_create_client.call_count == 2
    assert mock_list_items.call_count == 4
    assert mock_save_catalog.call_count == 2
