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

"""ENTSO-E vendor patches package for entsoe-py.

This package provides custom extensions and overrides for the third-party
'entsoe-py' library to support dynamic environment routing.

Specifically, it exposes the `ConfigurableEntsoeFileClient` which overrides
and replaces the standard `EntsoeFileClient` from `entsoe.files`. This is
done to eliminate hardcoded Keycloak identity provider token URLs and FMS
base API endpoints, enabling seamless switching between IOP (test) and PROD platforms.

Typical usage example:

    from entsoe_pipeline import get_config
    from entsoe_pipeline.vendor_patches.entsoe_py import ConfigurableEntsoeFileClient

    # Load validated type-safe configuration and populate credentials from .env
    config = get_config()

    # Instantiate the client with dynamic endpoints and loaded credentials
    client = ConfigurableEntsoeFileClient(
        username=config.env_config.email,
        pwd=config.env_config.password,
        base_url=config.env_config.base_url,
        token_url=config.env_config.token_url,
    )
"""

from .client import ConfigurableEntsoeFileClient

__all__ = ["ConfigurableEntsoeFileClient"]
