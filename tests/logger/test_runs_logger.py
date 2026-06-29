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

"""Unit tests for the RunsLogger context manager."""

from __future__ import annotations

import logging
import uuid

import pytest

from entsoe_pipeline.logger.runs_logger import RunsLogger


def test_runs_logger_initialization_fallback_uuid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that RunsLogger generates a dynamic UUID if Kestra execution ID is absent."""
    # Ensure environment is clean of KESTRA_EXECUTION_ID
    monkeypatch.delenv("KESTRA_EXECUTION_ID", raising=False)

    logger = RunsLogger(job_name="test_fallback", environment="IOP")

    assert logger.run_id is not None
    # Verify it is a valid UUID version 4
    val = uuid.UUID(logger.run_id, version=4)
    assert str(val) == logger.run_id
    assert logger.processed == 0
    assert logger.downloaded == 0
    assert logger.skipped == 0


def test_runs_logger_initialization_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that RunsLogger extracts run_id from KESTRA_EXECUTION_ID if present."""
    test_kestra_id = "kestra-exec-uuid-999"
    monkeypatch.setenv("KESTRA_EXECUTION_ID", test_kestra_id)

    logger = RunsLogger(job_name="test_kestra", environment="PROD")

    assert logger.run_id == test_kestra_id


def test_runs_logger_successful_metrics(caplog) -> None:
    """Verify metrics accumulator updates successfully and logs on enter/exit."""
    caplog.set_level(logging.INFO, logger="entsoe_pipeline")

    with RunsLogger(job_name="test_metrics", environment="IOP") as tracker:
        assert tracker.start_time is not None
        tracker.update_metrics(processed=5, downloaded=2, skipped=3)
        tracker.update_metrics(processed=3, downloaded=1, skipped=2)

    assert tracker.processed == 8
    assert tracker.downloaded == 3
    assert tracker.skipped == 5

    # Check logs
    log_messages = [record.message for record in caplog.records]
    assert any("Starting pipeline run" in msg for msg in log_messages)
    assert any("test_metrics completed successfully" in msg for msg in log_messages)


def test_runs_logger_exception_propagation(caplog) -> None:
    """Verify that RunsLogger logs exceptions on failure and propagates them."""
    caplog.set_level(logging.ERROR, logger="entsoe_pipeline")

    class TestError(Exception):
        pass

    tracker = RunsLogger(job_name="test_failures", environment="IOP")

    def run_body() -> None:
        with tracker:
            tracker.update_metrics(processed=10, downloaded=0, skipped=10)
            raise TestError("Simulated fatal sync error")

    with pytest.raises(TestError):
        run_body()

    # Check that metrics were still recorded
    assert tracker.processed == 10
    assert tracker.downloaded == 0
    assert tracker.skipped == 10

    # Verify log messages contain exception info
    log_records = list(caplog.records)
    assert len(log_records) > 0

    exc_logs = [
        r for r in log_records if r.levelname == "ERROR" or r.levelname == "CRITICAL"
    ]
    assert len(exc_logs) > 0
    assert "test_failures failed" in exc_logs[0].message
    assert exc_logs[0].exc_info is not None
