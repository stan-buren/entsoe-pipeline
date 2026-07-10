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

"""Unit tests for the FMS API requests observability tracker."""

from __future__ import annotations

import logging

import requests

from entsoe_pipeline import RunsLogger, fms_api_counter
from entsoe_pipeline.api.client_side_throttler import ThrottledSession
from entsoe_pipeline.logger.api_observability import ApiRequestCounter


def test_api_request_counter_increment_and_reset() -> None:
    """Verify ApiRequestCounter counts requests by env/category and resets correctly."""
    # Arrange
    counter = ApiRequestCounter()

    # Act
    counter.increment("IOP", "TP_export")
    counter.increment("iop", "TP_export")
    counter.increment("IOP", "TP_Legacy_Publications")
    counter.increment("PROD", "TP_export")
    counter.increment("prod", "TP_Legacy_Publications")
    counter.increment("PROD", "TP_Legacy_Publications")

    stats = counter.get_stats()

    # Assert
    assert stats["iop_export"] == 2
    assert stats["iop_legacy"] == 1
    assert stats["prod_export"] == 1
    assert stats["prod_legacy"] == 2

    # Reset
    counter.reset()
    stats_reset = counter.get_stats()
    assert all(val == 0 for val in stats_reset.values())


def test_runs_logger_logs_api_request_stats(caplog) -> None:
    """Verify RunsLogger writes API request stats to logger on exit if requests exist."""
    logging.getLogger("entsoe_pipeline").propagate = True
    caplog.set_level(logging.INFO, logger="entsoe_pipeline")

    # Arrange
    fms_api_counter.reset()
    fms_api_counter.increment("PROD", "TP_export")

    # Act
    with RunsLogger(job_name="test_api_stats_job", environment="PROD"):
        pass

    # Assert
    log_messages = [record.message for record in caplog.records]
    assert any("FMS API Request Statistics" in msg for msg in log_messages)
    assert any("Prod Export: 1" in msg for msg in log_messages)

    # Counter should be reset
    stats = fms_api_counter.get_stats()
    assert all(val == 0 for val in stats.values())


def test_throttled_session_intercepts_and_counts_fms_requests(monkeypatch) -> None:
    """Verify ThrottledSession.send intercepts FMS HTTP requests and counts them."""
    # Arrange
    fms_api_counter.reset()
    session = ThrottledSession(min_interval_seconds=0.01)

    # Mock actual requests.Session.send to not hit real network
    mock_response = requests.Response()
    mock_response.status_code = 200
    monkeypatch.setattr(requests.Session, "send", lambda *args, **kwargs: mock_response)

    # Act 1: FMS PROD Export request
    req1 = requests.PreparedRequest()
    req1.url = "https://fms.tp.entsoe.eu/listFolder"
    req1.body = b'{"path": "/TP_export/Load"}'
    session.send(req1)

    # Act 2: FMS IOP Legacy request
    req2 = requests.PreparedRequest()
    req2.url = "https://fms.tp-iop.entsoe.eu/listFolder"
    req2.body = b'{"path": "/TP_Legacy_Publications/Load"}'
    session.send(req2)

    # Act 3: Keycloak/non-FMS request (should be ignored by counter)
    req3 = requests.PreparedRequest()
    req3.url = "https://keycloak.tp.entsoe.eu/token"
    session.send(req3)

    # Assert
    stats = fms_api_counter.get_stats()
    assert stats["prod_export"] == 1
    assert stats["iop_legacy"] == 1
    assert stats["iop_export"] == 0
    assert stats["prod_legacy"] == 0
