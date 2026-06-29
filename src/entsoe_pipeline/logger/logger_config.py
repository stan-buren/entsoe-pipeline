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

"""ENTSO-E Data Pipeline Logging Configuration Module.

Provides centralized, package-scoped logging configurations ensuring structured
and machine-readable outputs without polluting the global root logger namespace.
"""

from __future__ import annotations

import logging
import sys

from entsoe_pipeline.logger.core.json_formatter import JsonFormatter

# =============================================================================
# PUBLIC INTERFACES (Logger Instantiation & Configuration)
# =============================================================================


def setup_logging(
    level: int = logging.INFO,
    use_json: bool = False,
) -> None:
    """Configures the package-level logger named 'entsoe_pipeline'.

    Attaches a standard stdout stream handler and sets either a structured
    human-readable text formatter or a machine-readable JSON formatter. Disables
    log propagation upward to avoid duplication and third-party library clutter.

    Args:
        level: The logging severity threshold (e.g., logging.INFO).
        use_json: If True, uses the JsonFormatter; otherwise uses a clean text format.
    """
    logger = logging.getLogger("entsoe_pipeline")
    logger.setLevel(level)

    # Prevent adding handlers multiple times upon repeated initialization calls
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)

        if use_json:
            formatter = JsonFormatter()
        else:
            formatter = logging.Formatter(
                fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
            )

        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Crucial: Stop logs from bubbling up to the Root Logger.
        # This isolates our pipeline logging from verbose third-party dependencies.
        logger.propagate = False
