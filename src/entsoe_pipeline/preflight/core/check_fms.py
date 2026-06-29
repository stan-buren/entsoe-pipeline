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

"""ENTSO-E FMS API connectivity and authentication health checks."""

from __future__ import annotations

import logging

from entsoe_pipeline.api.client import create_fms_client

logger = logging.getLogger("entsoe_pipeline.preflight.core.check_fms")


def verify_fms_readiness(env_name: str | None = None) -> None:
    """Verifies FMS client instantiation and authentication connectivity.

    Args:
        env_name: Optional environment identifier ('IOP' or 'PROD').

    Raises:
        RequestException: If authentication request to Keycloak fails.
        ValueError: If configuration credentials or URLs are missing.
    """
    # Instantiating the client automatically triggers Keycloak token acquisition.
    # If the endpoint is down or credentials are bad, it raises an exception immediately.
    create_fms_client(env_name)
