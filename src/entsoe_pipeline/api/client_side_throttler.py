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

"""Client-side request rate limiter for the ENTSO-E API.

This module provides a thread-safe client-side throttler implementing the sliding
window log algorithm to prevent Keycloak/FMS token bans.
"""

from __future__ import annotations

import logging
import threading
import time

from collections import deque
from typing import Any, override

import requests

# Obtain a logger scoped to our package namespace (observability rule A)
logger = logging.getLogger("entsoe_pipeline")


class ThrottledSession(requests.Session):
    """A thread-safe requests.Session subclass that enforces client-side rate limits.

    Inheriting from requests.Session allows seamless injection as a drop-in
    replacement into existing API clients like ConfigurableEntsoeFileClient.

    Attributes:
        max_requests: An integer representing the maximum number of requests
            allowed within the sliding window period.
        period: A float/integer duration of the sliding window in seconds.
    """

    def __init__(
        self,
        max_requests: int = 95,
        period_seconds: int = 60,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initializes the throttler session with the specified rate limits.

        Args:
            max_requests: The maximum number of requests allowed in the period.
            period_seconds: The duration of the sliding window in seconds.
            *args: Positional arguments forwarded to requests.Session.
            **kwargs: Keyword arguments forwarded to requests.Session.
        """
        super().__init__(*args, **kwargs)
        self.max_requests = max_requests
        self.period = period_seconds

        # Deque containing float timestamps of past requests within the window
        self._timestamps: deque[float] = deque()

        # Reusable lock to guarantee thread safety during parallel execution
        self._lock = threading.Lock()

    def _wait_if_needed(self) -> None:
        """Verifies current rate limit consumption and blocks threads if necessary.

        Locks the deque, purges stale timestamps that fall outside the active
        sliding window, and performs dynamic sleeping if the threshold is met.
        """
        with self._lock:
            now = time.time()

            # Evict stale timestamps that are older than our sliding window period
            while self._timestamps and now - self._timestamps[0] > self.period:
                self._timestamps.popleft()

            # If the window capacity is exhausted, block the thread until a slot opens
            if len(self._timestamps) >= self.max_requests:
                sleep_time = self.period - (now - self._timestamps[0])

                if sleep_time > 0:
                    # Comply with logging Rule B: Avoid f-strings inside log parameters
                    logger.warning(
                        "Client-side rate limit reached (%d requests per %d seconds). "
                        "Throttling active: sleeping for %.2f seconds to prevent "
                        "API ban.",
                        self.max_requests,
                        self.period,
                        sleep_time,
                    )
                    time.sleep(sleep_time)

                # Reset standard current time anchor after waking up
                now = time.time()

                # Re-evict any now-stale records after the sleep pause
                while self._timestamps and now - self._timestamps[0] > self.period:
                    self._timestamps.popleft()

            # Record the successful dispatch timestamp
            self._timestamps.append(now)

    @override
    def send(
        self, request: requests.PreparedRequest, **kwargs: Any
    ) -> requests.Response:
        """Overrides the main requests.Session.send method as a Single Source of Truth.

        Args:
            request: The PreparedRequest object to transmit.
            **kwargs: Extensible HTTP keyword options.

        Returns:
            The resolved requests.Response object.
        """
        self._wait_if_needed()
        return super().send(request, **kwargs)
