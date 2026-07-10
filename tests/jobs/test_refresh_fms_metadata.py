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

"""Integration tests for the refresh_fms_metadata CLI orchestrator."""

from __future__ import annotations

import sys

from unittest.mock import MagicMock, patch


@patch("entsoe_pipeline.preflight.run_prepare_landing_preflight")
@patch("entsoe_pipeline.preflight.core.check_db.verify_db_readiness")
@patch("entsoe_pipeline.fms_metadata.core.ingest_overview_metadata")
@patch("entsoe_pipeline.fms_metadata.core.ingest_domain_metadata")
@patch("entsoe_pipeline.fms_metadata.core.ingest_all_legacy_metadata")
@patch("entsoe_pipeline.fms_metadata.ingestion.sizes_ingest.ingest_all_catalog_sizes")
def test_refresh_fms_metadata_job_runs_with_test_flag(
    mock_sizes: MagicMock,
    mock_legacy: MagicMock,
    mock_domain: MagicMock,
    mock_overview: MagicMock,
    mock_verify_db: MagicMock,
    mock_preflight: MagicMock,
) -> None:
    """Verify that the refresh job runs and propagates the --test flag.

    Args:
        mock_sizes: Mock sizes builder.
        mock_legacy: Mock legacy crawler.
        mock_domain: Mock active crawler.
        mock_overview: Mock overview crawler.
        mock_verify_db: Mock DB preflight.
        mock_preflight: Mock landing preflight.
    """
    import runpy

    from entsoe_pipeline import REFRESH_FMS_METADATA_PY

    job_path = REFRESH_FMS_METADATA_PY

    # 1. Run CLI for 'prepare' phase
    test_args_prepare = [
        "refresh_fms_metadata.py",
        "--phase",
        "prepare",
        "--test",
    ]
    with patch.object(sys, "argv", test_args_prepare):
        runpy.run_path(str(job_path), run_name="__main__")

    mock_preflight.assert_called_once()
    mock_verify_db.assert_called_once()
    mock_overview.assert_called_once()

    # 2. Run CLI for 'crawl' phase
    test_args_crawl = [
        "refresh_fms_metadata.py",
        "--phase",
        "crawl",
        "--env",
        "IOP",
        "--test",
        "--force",
    ]
    with patch.object(sys, "argv", test_args_crawl):
        runpy.run_path(str(job_path), run_name="__main__")

    # Ensure ingest_domain_metadata was called
    assert mock_domain.call_count > 0
    # Ensure ingest_all_legacy_metadata was NOT called in test mode
    mock_legacy.assert_not_called()

    # 3. Run CLI for 'finalize' phase
    test_args_finalize = [
        "refresh_fms_metadata.py",
        "--phase",
        "finalize",
        "--test",
    ]
    with patch.object(sys, "argv", test_args_finalize):
        runpy.run_path(str(job_path), run_name="__main__")

    mock_sizes.assert_called_once()
