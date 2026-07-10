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

"""Unit Tests for FMS Metadata Ingestion Consolidated CLI."""

from __future__ import annotations

import sys

from unittest.mock import MagicMock, patch

import pytest

from entsoe_pipeline.fms_metadata.ingestion.fms_metadata_ingest import (
    ingest_metadata,
    main,
)


@patch(
    "entsoe_pipeline.fms_metadata.ingestion.fms_metadata_ingest.get_stale_domain_folders"
)
@patch(
    "entsoe_pipeline.fms_metadata.ingestion.fms_metadata_ingest.get_stale_legacy_folders"
)
@patch(
    "entsoe_pipeline.fms_metadata.ingestion.fms_metadata_ingest.ingest_domain_metadata"
)
@patch(
    "entsoe_pipeline.fms_metadata.ingestion.fms_metadata_ingest.ingest_all_legacy_metadata"
)
def test_ingest_metadata_orchestrates_correctly(
    mock_legacy: MagicMock,
    mock_domain: MagicMock,
    mock_get_stale_legacy: MagicMock,
    mock_get_stale_domain: MagicMock,
) -> None:
    """Verify ingest_metadata routes inputs to core orchestrators with filtered folders."""
    mock_get_stale_domain.return_value = ["folder1"]
    mock_get_stale_legacy.return_value = ["legacy_folder1"]

    # Act 1: Single domain
    ingest_metadata(domain="Load", env="IOP")
    mock_get_stale_domain.assert_called_once_with("Load", "IOP", False)
    mock_domain.assert_called_once_with(
        domain_name="Load", env="IOP", folders=["folder1"]
    )
    mock_legacy.assert_not_called()

    # Reset mocks
    mock_domain.reset_mock()
    mock_legacy.reset_mock()
    mock_get_stale_domain.reset_mock()
    mock_get_stale_legacy.reset_mock()

    # Act 2: Legacy
    ingest_metadata(domain="Legacy", env="PROD")
    assert mock_get_stale_legacy.call_count == 3
    mock_domain.assert_not_called()
    mock_legacy.assert_called_once_with(
        env="PROD", folders=["legacy_folder1", "legacy_folder1", "legacy_folder1"]
    )

    # Reset mocks
    mock_domain.reset_mock()
    mock_legacy.reset_mock()
    mock_get_stale_domain.reset_mock()
    mock_get_stale_legacy.reset_mock()

    # Act 3: ALL
    ingest_metadata(domain="ALL", env="IOP")
    assert mock_get_stale_domain.call_count > 0
    assert mock_domain.call_count > 0
    assert mock_get_stale_legacy.call_count == 3
    mock_legacy.assert_called_once_with(
        env="IOP", folders=["legacy_folder1", "legacy_folder1", "legacy_folder1"]
    )


def test_ingest_metadata_raises_on_unknown_domain() -> None:
    """Verify ingest_metadata raises ValueError on unknown domains."""
    with pytest.raises(ValueError, match="Unknown domain"):
        ingest_metadata(domain="UnknownDomainNameStuff", env="IOP")


@patch("entsoe_pipeline.fms_metadata.ingestion.fms_metadata_ingest.ingest_metadata")
def test_main_cli_entrypoint(mock_ingest: MagicMock) -> None:
    """Verify main parsing and parameter mapping.

    Args:
        mock_ingest: Mock ingest_metadata runner.
    """
    test_args = [
        "fms_metadata_ingest.py",
        "--domain",
        "Load",
        "--env",
        "IOP",
        "--force",
    ]
    with patch.object(sys, "argv", test_args):
        main()

    mock_ingest.assert_called_once_with(
        domain="Load", env="IOP", is_test=False, is_force=True
    )


@patch(
    "entsoe_pipeline.fms_metadata.ingestion.fms_metadata_ingest.resolve_active_environment"
)
@patch(
    "entsoe_pipeline.fms_metadata.ingestion.fms_metadata_ingest.get_stale_domain_folders"
)
@patch(
    "entsoe_pipeline.fms_metadata.ingestion.fms_metadata_ingest.ingest_domain_metadata"
)
def test_ingest_metadata_resolves_env_if_none(
    mock_ingest_domain: MagicMock,
    mock_get_stale: MagicMock,
    mock_resolve_env: MagicMock,
) -> None:
    """Verify ingest_metadata resolves environment dynamically when omitted."""
    mock_resolve_env.return_value = "IOP"
    mock_get_stale.return_value = ["folder1"]
    ingest_metadata(domain="Load", env=None)
    mock_resolve_env.assert_called_once()
    mock_ingest_domain.assert_called_once_with(
        domain_name="Load", env="IOP", folders=["folder1"]
    )


@patch("entsoe_pipeline.fms_metadata.ingestion.fms_metadata_ingest.ingest_metadata")
def test_main_cli_fails_and_raises(mock_ingest: MagicMock) -> None:
    """Verify main propagates exception and logs error on failures."""
    mock_ingest.side_effect = RuntimeError("Mock Failure")
    test_args = ["fms_metadata_ingest.py", "--domain", "Load"]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(RuntimeError, match="Mock Failure"):
            main()


@patch(
    "entsoe_pipeline.fms_metadata.ingestion.fms_metadata_ingest.get_stale_domain_folders"
)
@patch(
    "entsoe_pipeline.fms_metadata.ingestion.fms_metadata_ingest.get_stale_legacy_folders"
)
@patch(
    "entsoe_pipeline.fms_metadata.ingestion.fms_metadata_ingest.ingest_domain_metadata"
)
@patch(
    "entsoe_pipeline.fms_metadata.ingestion.fms_metadata_ingest.ingest_all_legacy_metadata"
)
def test_ingest_metadata_test_mode(
    mock_legacy: MagicMock,
    mock_domain: MagicMock,
    mock_get_legacy: MagicMock,
    mock_get_domain: MagicMock,
) -> None:
    """Verify test mode filters heavy domains and skips legacy."""
    mock_get_domain.return_value = ["folder1"]
    mock_get_legacy.return_value = ["legacy_folder1"]

    # Act 1: domain ALL in test mode
    ingest_metadata(domain="ALL", env="IOP", is_test=True)
    # Check that it did NOT call legacy
    mock_legacy.assert_not_called()
    # Check that only allowed light domains are called
    called_domains = [
        call.kwargs.get("domain_name") for call in mock_domain.call_args_list
    ]
    allowed_domains = ["Load", "Generation", "OtherMarketInformation"]
    for d in called_domains:
        assert d in allowed_domains
    assert len(called_domains) > 0

    # Reset
    mock_domain.reset_mock()
    mock_legacy.reset_mock()
    mock_get_domain.reset_mock()
    mock_get_legacy.reset_mock()

    # Act 2: legacy domain in test mode (should skip/no-op)
    ingest_metadata(domain="Legacy", env="IOP", is_test=True)
    mock_legacy.assert_not_called()

    # Act 3: specific non-light domain in test mode raises ValueError
    with pytest.raises(ValueError, match="Cannot ingest domain"):
        ingest_metadata(domain="Transmission", env="IOP", is_test=True)


@patch("entsoe_pipeline.fms_metadata.ingestion.fms_metadata_ingest.ingest_metadata")
def test_main_cli_test_arg(mock_ingest: MagicMock) -> None:
    """Verify test argument parsing in main."""
    test_args = [
        "fms_metadata_ingest.py",
        "--domain",
        "ALL",
        "--env",
        "IOP",
        "--test",
    ]
    with patch.object(sys, "argv", test_args):
        main()

    mock_ingest.assert_called_once_with(
        domain="ALL", env="IOP", is_test=True, is_force=False
    )
