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

"""FMS API Observability and requests tracking module."""

from __future__ import annotations

import logging

from threading import Lock

logger = logging.getLogger("entsoe_pipeline.logger.api_observability")


class ApiRequestCounter:
    """Thread-safe counter for FMS API request statistics."""

    def __init__(self) -> None:
        """Initializes the request statistics counter."""
        self._lock = Lock()
        self.iop_export = 0
        self.iop_legacy = 0
        self.prod_export = 0
        self.prod_legacy = 0

    def increment(self, env: str, category: str) -> None:
        """Increments the appropriate request counter.

        Args:
            env: Environment name ('IOP' or 'PROD').
            category: Directory category ('TP_export' or 'TP_Legacy_Publications').
        """
        env_upper = env.upper()
        cat_lower = category.lower()

        with self._lock:
            if "IOP" in env_upper:
                if "legacy" in cat_lower:
                    self.iop_legacy += 1
                else:
                    self.iop_export += 1
            else:
                if "legacy" in cat_lower:
                    self.prod_legacy += 1
                else:
                    self.prod_export += 1

    def get_stats(self) -> dict[str, int]:
        """Returns a snapshot of the current stats.

        Returns:
            dict[str, int]: Snapped metrics.
        """
        with self._lock:
            return {
                "iop_export": self.iop_export,
                "iop_legacy": self.iop_legacy,
                "prod_export": self.prod_export,
                "prod_legacy": self.prod_legacy,
            }

    def reset(self) -> None:
        """Resets all metrics to zero."""
        with self._lock:
            self.iop_export = 0
            self.iop_legacy = 0
            self.prod_export = 0
            self.prod_legacy = 0


# Global singleton instance for tracking active run FMS requests
fms_api_counter = ApiRequestCounter()
