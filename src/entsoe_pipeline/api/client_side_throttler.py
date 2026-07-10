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

This module provides a thread-safe client-side throttler implementing an elastic
Leaky Bucket rate-limiting interval to guarantee smooth, uniform API ingestion
and eliminate micro-burst detection by the ENTSO-E Akamai / Keycloak gateway.
"""

from __future__ import annotations

import logging
import threading
import time

from typing import Any, override

import requests

from entsoe_pipeline.logger.api_observability import fms_api_counter

logger = logging.getLogger("entsoe_pipeline")


class ThrottledSession(requests.Session):
    """A thread-safe requests.Session subclass that enforces uniform request pacing.

    Implements the Leaky Bucket pattern: instead of a sliding window that bursts
    95 requests and then sleeps a full minute, each request is gated by a strict
    minimum inter-request interval (e.g. 0.637s).  If the time since the last
    request already exceeds the interval (because DB writes or parsing took longer),
    no sleep is added — zero idle overhead.

    The interval value is read from ``config/entsoe_api_limits.yml`` via
    ``RateLimitsConfig.fms_min_request_interval_seconds`` and injected at
    construction time, keeping this class free of config-loading logic.

    Attributes:
        min_interval: Minimum seconds to enforce between consecutive FMS requests.
    """

    def __init__(
        self,
        min_interval_seconds: float = 0.637,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initializes the throttler with a pre-calculated minimum request interval.

        Args:
            min_interval_seconds: Seconds to wait between requests. Must equal
                ``period / max_requests`` plus a small jitter buffer (5 ms).
                Source of truth: ``safetimits.fms_min_request_interval_seconds``
                in ``config/entsoe_api_limits.yml``.
            *args: Positional arguments forwarded to ``requests.Session``.
            **kwargs: Keyword arguments forwarded to ``requests.Session``.
        """
        super().__init__(*args, **kwargs)
        self.min_interval = min_interval_seconds

        # Monotonic timestamp of the most recently dispatched FMS request.
        # Initialized to 0.0 so the very first request is never delayed.
        self._last_request_time: float = 0.0

        # Mutex: serializes concurrent threads so the interval is measured
        # accurately even when multiple threads share one session instance.
        self._lock = threading.Lock()

    def _wait_if_needed(self) -> None:
        """Enforces the minimum inter-request interval if pacing is breached.

        Measures elapsed time since the last request.  If less than
        ``min_interval`` has passed, sleeps only the remaining delta.
        Updates ``_last_request_time`` *after* the sleep so the next call
        measures from the actual dispatch moment.
        """
        with self._lock:
            now = time.time()
            elapsed = now - self._last_request_time

            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                # Log only pauses longer than 100 ms to avoid spamming debug logs
                # with sub-millisecond corrections caused by system timer jitter.
                if sleep_time > 0.1:
                    logger.debug(
                        "Leaky Bucket pacer: sleeping %.4f sec to maintain interval.",
                        sleep_time,
                    )
                time.sleep(sleep_time)

            # Record actual dispatch time *after* the sleep
            self._last_request_time = time.time()

    @override
    def send(
        self, request: requests.PreparedRequest, **kwargs: Any
    ) -> requests.Response:
        """Overrides requests.Session.send to inject pacing and collect metrics.

        Args:
            request: The PreparedRequest object to transmit.
            **kwargs: Extensible HTTP keyword options.

        Returns:
            The resolved requests.Response object.
        """
        url = request.url or ""

        # Apply pacing only to FMS infrastructure requests.
        # General ENTSOE XML/REST calls use a separate session and are not throttled here.
        if "fms.tp" in url:
            self._wait_if_needed()

            env = "IOP" if "tp-iop" in url else "PROD"
            body_str = ""
            if request.body:
                if isinstance(request.body, bytes):
                    body_str = request.body.decode("utf-8", errors="ignore")
                else:
                    body_str = str(request.body)

            if "TP_Legacy_Publications" in url or "TP_Legacy_Publications" in body_str:
                category = "TP_Legacy_Publications"
            else:
                category = "TP_export"

            fms_api_counter.increment(env, category)

        return super().send(request, **kwargs)
