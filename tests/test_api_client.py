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

"""Unit Tests for FMS API client and listing modules.

Verifies create_fms_client factory logic and ls_fms paginated remote listing operations
using the 3A (Arrange, Act, Assert) pattern.
"""

from __future__ import annotations

import os

from unittest.mock import MagicMock, patch

from entsoe_pipeline.api.client import create_fms_client
from entsoe_pipeline.api.ls_fms import ls_fms

# =============================================================================
# 1. UNIT TESTS: CLIENT FACTORY
# =============================================================================


@patch("entsoe_pipeline.api.client.ConfigurableEntsoeFileClient")
@patch("entsoe_pipeline.api.client.get_env_config")
def test_create_fms_client_defaults_to_active_config(
    mock_get_env_config: MagicMock,
    mock_client_class: MagicMock,
) -> None:
    """Verifies create_fms_client defaults to active env when env_name is None."""
    # 1. Arrange
    mock_config = MagicMock()
    mock_config.email = "default@example.com"
    mock_config.password = "default_pwd"  # noqa: S105
    mock_config.base_url = "https://fms.default.eu/"
    mock_config.token_url = "https://keycloak.default.eu/token"  # noqa: S105
    mock_get_env_config.return_value = mock_config

    mock_client_instance = MagicMock()
    mock_client_class.return_value = mock_client_instance

    # 2. Act
    client = create_fms_client()

    # 3. Assert
    mock_get_env_config.assert_called_once()
    mock_client_class.assert_called_once_with(
        username="default@example.com",
        pwd="default_pwd",  # noqa: S106
        base_url="https://fms.default.eu/",
        token_url="https://keycloak.default.eu/token",  # noqa: S106
    )
    assert client == mock_client_instance


@patch("entsoe_pipeline.api.client.ConfigurableEntsoeFileClient")
@patch("entsoe_pipeline.api.client.yaml.safe_load")
@patch("entsoe_pipeline.api.client.CONFIG_DIR")
@patch("entsoe_pipeline.api.client.ENV_FILE")
def test_create_fms_client_resolves_explicit_environment(
    mock_env_file: MagicMock,
    mock_config_dir: MagicMock,
    mock_yaml_load: MagicMock,
    mock_client_class: MagicMock,
) -> None:
    """Verifies create_fms_client resolves explicit environments from YAML/environ."""
    # 1. Arrange
    mock_env_file.exists.return_value = False
    mock_yaml_path = MagicMock()
    mock_yaml_path.exists.return_value = True
    mock_config_dir.__truediv__.return_value = mock_yaml_path

    # Mock environment configuration mapping
    mock_yaml_load.return_value = {
        "environments": {
            "IOP": {
                "base_url": "https://fms.iop.eu/",
                "token_url": "https://keycloak.iop.eu/token",
                "credential_keys": {
                    "email": "IOP_EMAIL",
                    "password": "IOP_PASSWORD",
                },
            }
        }
    }

    mock_client_instance = MagicMock()
    mock_client_class.return_value = mock_client_instance

    # Inject mock credentials into temporary OS environment variables
    mock_creds = {"IOP_EMAIL": "iop-user", "IOP_PASSWORD": "iop-secret"}
    with patch.dict(os.environ, mock_creds):
        # 2. Act
        client = create_fms_client("IOP")

    # 3. Assert
    mock_client_class.assert_called_once_with(
        username="iop-user",
        pwd="iop-secret",  # noqa: S106
        base_url="https://fms.iop.eu/",
        token_url="https://keycloak.iop.eu/token",  # noqa: S106
    )
    assert client == mock_client_instance


# =============================================================================
# 2. UNIT TESTS: FMS NAVIGATION & PAGINATION
# =============================================================================


@patch("entsoe_pipeline.api.ls_fms._fetch_folder_page")
def test_ls_fms_aggregates_multiple_pages_correctly(
    mock_fetch_page: MagicMock,
) -> None:
    """Verifies ls_fms combines and returns folder pages until termination."""
    # 1. Arrange
    mock_client = MagicMock()

    # Page 1 contains 2 elements (equals page_size, so query continues)
    page_1 = {
        "contentItemList": [
            {"name": "ActualTotalLoad_r3"},
            {"name": "EnergyPrices_r3"},
        ]
    }
    # Page 2 contains 1 element (less than page_size 2, so query stops)
    page_2 = {
        "contentItemList": [
            {"name": "Outages_r3"},
        ]
    }
    mock_fetch_page.side_effect = [page_1, page_2]

    # 2. Act
    results = ls_fms(mock_client, "/TP_export/", page_size=2)

    # 3. Assert
    # Verify both pages were fetched sequentially
    assert mock_fetch_page.call_count == 2
    mock_fetch_page.assert_any_call(mock_client, "/TP_export/", 0, 2)
    mock_fetch_page.assert_any_call(mock_client, "/TP_export/", 1, 2)

    # Assert combined results are preserved
    assert len(results) == 3
    assert results == ["ActualTotalLoad_r3", "EnergyPrices_r3", "Outages_r3"]
