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

import pandas as pd
import requests

from entsoe.files import EntsoeFileClient


class ConfigurableEntsoeFileClient(EntsoeFileClient):
    """A configurable wrapper over the third-party ENTSO-E FMS API Client.

    Allows dynamic injection of API endpoints and Keycloak OAuth2 token URLs,
    enabling seamless switching between IOP (test) and PROD platforms without
    hardcoding any environment-specific routing logic.
    """

    def __init__(
        self,
        username: str | None = None,
        pwd: str | None = None,
        base_url: str | None = None,  # <--- patch param
        token_url: str | None = None,  # <--- patch param
        session: requests.Session | None = None,
        proxies: dict | None = None,
        timeout: int | None = None,
    ):
        # 1. Store custom URLs on the instance BEFORE executing parent constructor.
        # This pre-initialization step is computationally required because the
        # parent constructor (`super().__init__`) immediately triggers a call to
        # `self._update_token()` at the very end of its execution block.
        #
        # Storing `self.token_url` early guarantees that when `_update_token` runs
        # (via polymorphic late-binding lookup during the parent's initialization),
        # it successfully resolves the custom Keycloak token URL instead of
        # raising an AttributeError or falling back prematurely.
        #
        # Storing `self.BASEURL` on the instance level (`self.__dict__`) dynamically
        # overrides the class-level variable `EntsoeFileClient.BASEURL`
        # ("https://fms.tp.entsoe.eu/"). Since Python's attribute lookup resolves
        # instance-level dictionaries before class namespaces, all inherited methods
        # (e.g., `list_folder` or `download_single_file_raw`) will automatically
        # route their HTTP POST requests to our configured active environment
        # endpoint without any code duplication.
        self.token_url = token_url
        self.BASEURL = base_url

        # 2. Call parent constructor.
        # Polymorphism guarantees that parent's init calls our _update_token()
        super().__init__(
            username=username,
            pwd=pwd,
            session=session,
            proxies=proxies,
            timeout=timeout,
        )

    def _update_token(self) -> None:
        """Authenticates against the dynamically configured Keycloak endpoint."""
        # Fallback to standard PROD token URL if no custom URL was injected
        target_token_url = (
            self.token_url
            or "https://keycloak.tp.entsoe.eu/realms/tp/protocol/openid-connect/token"
        )

        r = self.session.post(
            target_token_url,
            data={
                "client_id": "tp-fms-public",
                "grant_type": "password",
                "username": self.username,
                "password": self.pwd,
            },
            proxies=self.proxies,
            timeout=self.timeout,
        )
        r.raise_for_status()
        data = r.json()

        # Update access token and its expiration timestamp
        self.expire = pd.Timestamp.now(tz="Europe/Amsterdam") + pd.Timedelta(
            seconds=data["expires_in"]
        )
        self.access_token = data["access_token"]
