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

"""Unit tests for the ENTSO-E FMS CSV ingestion CLI job runner.

Validates that the ingest_fms_data script correctly parses parameters and
handles execution errors cleanly.
"""

import sys

from typing import Any

import pytest

from jobs.ingest_fms_data import main


def test_ingest_job_success(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify job runner successfully invokes ingestion core on valid args."""
    # -------------------------------------------------------------------------
    # ARRANGE: Mock the ingestion function and configure CLI arguments
    # -------------------------------------------------------------------------
    called_args: dict[str, Any] = {}

    def mock_ingest_folder(folder_name: str, force_reload: bool) -> None:
        called_args["folder_name"] = folder_name
        called_args["force_reload"] = force_reload

    monkeypatch.setattr("jobs.ingest_fms_data.ingest_folder", mock_ingest_folder)
    monkeypatch.setattr(
        sys, "argv", ["ingest_fms_data.py", "--folder", "CustomFolder", "--force"]
    )

    # -------------------------------------------------------------------------
    # ACT: Run the job main method
    # -------------------------------------------------------------------------
    main()

    # -------------------------------------------------------------------------
    # ASSERT: Verify proper arguments were parsed and passed to ingestion core
    # -------------------------------------------------------------------------
    assert called_args["folder_name"] == "CustomFolder"
    assert called_args["force_reload"] is True

    captured = capsys.readouterr()
    assert "Commencing ingestion for folder: CustomFolder" in captured.out
    assert "Ingestion finished successfully!" in captured.out


def test_ingest_job_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify that ingest_fms_data job runner handles runtime errors gracefully.

    This ensures that when an error occurs during ETL processing, the runner prints
    a meaningful diagnostic message to stderr and exits with code 1.
    """

    # -------------------------------------------------------------------------
    # ARRANGE: Mock the ingestion function to throw an exception, setup arguments
    # -------------------------------------------------------------------------
    def mock_ingest_folder_error(
        folder_name: str,  # noqa: ARG001
        force_reload: bool,  # noqa: ARG001
    ) -> None:
        raise ValueError("Simulated network catalog timeout")

    monkeypatch.setattr("jobs.ingest_fms_data.ingest_folder", mock_ingest_folder_error)
    monkeypatch.setattr(sys, "argv", ["ingest_fms_data.py", "--folder", "FailFolder"])

    # -------------------------------------------------------------------------
    # ACT & ASSERT: Expect SystemExit(1) on failure and verify stderr message
    # -------------------------------------------------------------------------
    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1

    captured = capsys.readouterr()
    assert "Simulated network catalog timeout" in captured.err
