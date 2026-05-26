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

"""Unit tests for ENTSO-E vendor patches package.

This module verifies that our custom client override behaves correctly under
dynamic configurations, routing requests to the proper endpoints and handling
authentication flows properly.
"""

from unittest.mock import MagicMock

import pandas as pd
import pytest
import requests

from entsoe_pipeline.vendor_patches.entsoe_py import ConfigurableEntsoeFileClient


@pytest.mark.unit
def test_configurable_client_initialization_flow(mocker) -> None:
    """Verify client injects endpoints before executing base constructor.

    This tests the instance-level late binding mechanism, confirming that the
    custom base URL and token URL are stored correctly and override the class-level
    defaults before any parent operations execute.
    """
    # -------------------------------------------------------------------------
    # ARRANGE: Set up custom endpoints and mock out Keycloak token fetching
    # -------------------------------------------------------------------------
    custom_base_url = "https://fms.custom-env.entsoe.eu/"
    custom_token_url = "https://keycloak.custom-env.entsoe.eu/token"  # noqa: S105
    email = "test-user@example.com"
    password = "secret-password"  # noqa: S105

    # We mock _update_token on the class level so that super().__init__ does not
    # make actual network calls during testing
    mock_update_token = mocker.patch.object(
        ConfigurableEntsoeFileClient, "_update_token", return_value=None
    )

    # -------------------------------------------------------------------------
    # ACT: Instantiate our custom patched client wrapper
    # -------------------------------------------------------------------------
    client = ConfigurableEntsoeFileClient(
        username=email,
        pwd=password,
        base_url=custom_base_url,
        token_url=custom_token_url,
    )

    # -------------------------------------------------------------------------
    # ASSERT: Verify endpoints reside in instance dictionary and match expectations
    # -------------------------------------------------------------------------
    assert custom_base_url == client.BASEURL
    assert client.token_url == custom_token_url
    assert client.username == email
    assert client.pwd == password
    assert mock_update_token.called


@pytest.mark.unit
def test_configurable_client_token_update_flow(mocker) -> None:
    """Verify that _update_token issues an HTTP POST to the dynamic token URL.

    This ensures that the authentication payload contains correct grant types,
    credentials, and that the returned OAuth2 access token and expiry timestamp
    are correctly saved on the client instance.
    """
    # -------------------------------------------------------------------------
    # ARRANGE: Setup mocked response for requests.Session.post BEFORE instantiating.
    # -------------------------------------------------------------------------
    # By patching requests.Session.post at the class level before client creation,
    # we allow the real constructor flow to run naturally and execute the actual
    # _update_token logic, routing its authentication HTTP POST straight to our mock.
    # -------------------------------------------------------------------------
    custom_base_url = "https://fms.custom-env.entsoe.eu/"
    custom_token_url = "https://keycloak.custom-env.entsoe.eu/token"  # noqa: S105
    email = "dev-user@entsoe.eu"
    password = "super-secret-dev-pwd"  # noqa: S105

    # Prepare a fake JSON authentication payload mimicking Keycloak
    mock_response = MagicMock(spec=requests.Response)
    mock_response.json.return_value = {
        "access_token": "mocked-jwt-access-token-xyz-123",
        "expires_in": 3600,
    }

    # Patch requests.Session.post to return our mocked response
    mock_post = mocker.patch.object(
        requests.Session, "post", return_value=mock_response
    )

    # -------------------------------------------------------------------------
    # ACT: Instantiate our custom patched client wrapper.
    # -------------------------------------------------------------------------
    # This automatically triggers super().__init__, which calls _update_token()
    # -------------------------------------------------------------------------
    client = ConfigurableEntsoeFileClient(
        username=email,
        pwd=password,
        base_url=custom_base_url,
        token_url=custom_token_url,
    )

    # -------------------------------------------------------------------------
    # ASSERT: Verify that Keycloak HTTP call used custom token URL during init
    # -------------------------------------------------------------------------
    mock_post.assert_called_once_with(
        custom_token_url,
        data={
            "client_id": "tp-fms-public",
            "grant_type": "password",
            "username": email,
            "password": password,
        },
        proxies=None,
        timeout=None,
    )
    mock_response.raise_for_status.assert_called_once()

    assert client.access_token == "mocked-jwt-access-token-xyz-123"  # noqa: S105
    assert isinstance(client.expire, pd.Timestamp)
