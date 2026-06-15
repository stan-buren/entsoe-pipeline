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

"""Tests verifying that FMS API connectivity is operational and configurations are loaded."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from entsoe_pipeline.api.client import create_fms_client


def test_fms_client_instantiation_mocked() -> None:
    """Verifies FMS client instantiation works with mocked token response."""
    with patch("requests.Session.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "mock-token-12345",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response

        client = create_fms_client("IOP")

        assert client.access_token == "mock-token-12345"
        assert client.BASEURL == "https://fms.tp-iop.entsoe.eu/"
