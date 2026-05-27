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

"""Unit Tests for Observability & Logging Domain.

Verifies JsonFormatter serialization, setup_logging configurations, and custom
pipeline exception class hierarchies using the 3A pattern.
"""

from __future__ import annotations

import json
import logging
import sys

from entsoe_pipeline.logger import (
    EntsoeApiError,
    EntsoeConfigurationError,
    EntsoeConnectionError,
    EntsoeDataValidationError,
    EntsoePipelineError,
    setup_logging,
)
from entsoe_pipeline.logger.logger_config import JsonFormatter

# =============================================================================
# 1. UNIT TESTS: EXCEPTIONS HIERARCHY
# =============================================================================


def test_exceptions_hierarchical_inheritance() -> None:
    """Verifies that all custom errors properly inherit from EntsoePipelineError."""
    # -------------------------------------------------------------------------
    # ARRANGE
    # -------------------------------------------------------------------------
    config_err = EntsoeConfigurationError("config failure")
    conn_err = EntsoeConnectionError("connection timeout")
    api_err = EntsoeApiError("bad endpoint response")
    val_err = EntsoeDataValidationError("invalid csv layout")

    # -------------------------------------------------------------------------
    # ACT & ASSERT
    # -------------------------------------------------------------------------
    assert isinstance(config_err, EntsoePipelineError)
    assert isinstance(conn_err, EntsoePipelineError)
    assert isinstance(api_err, EntsoePipelineError)
    assert isinstance(val_err, EntsoePipelineError)

    assert issubclass(EntsoeConfigurationError, EntsoePipelineError)
    assert issubclass(EntsoeConnectionError, EntsoePipelineError)
    assert issubclass(EntsoeApiError, EntsoePipelineError)
    assert issubclass(EntsoeDataValidationError, EntsoePipelineError)


# =============================================================================
# 2. UNIT TESTS: JSON FORMATTER
# =============================================================================


def test_json_formatter_serializes_log_records_to_json() -> None:
    """Verifies that JsonFormatter formats standard attributes into valid JSON."""
    # -------------------------------------------------------------------------
    # ARRANGE
    # -------------------------------------------------------------------------
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="entsoe_pipeline.test",
        level=logging.INFO,
        pathname="test_logger.py",
        lineno=42,
        msg="Test loading of %d records from %s",
        args=(500, "IOP"),
        exc_info=None,
    )

    # -------------------------------------------------------------------------
    # ACT
    # -------------------------------------------------------------------------
    json_str = formatter.format(record)
    parsed = json.loads(json_str)

    # -------------------------------------------------------------------------
    # ASSERT
    # -------------------------------------------------------------------------
    assert parsed["logger"] == "entsoe_pipeline.test"
    assert parsed["level"] == "INFO"
    assert parsed["message"] == "Test loading of 500 records from IOP"
    assert "timestamp" in parsed


def test_json_formatter_includes_extra_context_fields() -> None:
    """Verifies that custom fields supplied via extra logger context are captured."""
    # -------------------------------------------------------------------------
    # ARRANGE
    # -------------------------------------------------------------------------
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="entsoe_pipeline.test",
        level=logging.WARNING,
        pathname="test_logger.py",
        lineno=50,
        msg="Data quality validation failed",
        args=(),
        exc_info=None,
    )
    # Inject context variables simulating logger.warning("...", extra=...)
    record.dataset = "Outages"
    record.execution_date = "2026-05-26"

    # -------------------------------------------------------------------------
    # ACT
    # -------------------------------------------------------------------------
    json_str = formatter.format(record)
    parsed = json.loads(json_str)

    # -------------------------------------------------------------------------
    # ASSERT
    # -------------------------------------------------------------------------
    assert parsed["level"] == "WARNING"
    assert parsed["dataset"] == "Outages"
    assert parsed["execution_date"] == "2026-05-26"


# =============================================================================
# 3. UNIT TESTS: LOGGER CONFIGURATION SETUP
# =============================================================================


def test_setup_logging_configures_package_level_logger() -> None:
    """Verifies setup_logging configures logger with proper handler and formatter."""
    # -------------------------------------------------------------------------
    # ARRANGE
    # -------------------------------------------------------------------------
    logger = logging.getLogger("entsoe_pipeline")
    # Reset logger handlers to guarantee test isolation
    logger.handlers.clear()

    # -------------------------------------------------------------------------
    # ACT
    # -------------------------------------------------------------------------
    setup_logging(level=logging.DEBUG, use_json=True)

    # -------------------------------------------------------------------------
    # ASSERT
    # -------------------------------------------------------------------------
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 1
    assert logger.propagate is False

    handler = logger.handlers[0]
    assert isinstance(handler, logging.StreamHandler)
    assert handler.stream == sys.stdout
    assert isinstance(handler.formatter, JsonFormatter)

    # Cleanup to avoid global state pollution
    logger.handlers.clear()
