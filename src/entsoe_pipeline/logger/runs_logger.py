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

"""ENTSO-E Data Pipeline Execution Run Logger.

Provides a public facade context manager to track pipeline execution runs,
delegating actual logic and calculations to the core tracker package.
"""

from __future__ import annotations

from datetime import datetime
from types import TracebackType

from entsoe_pipeline.logger.core.runs_tracker import RunsTrackerCore


class RunsLogger:
    """A facade context manager that orchestrates logging and metrics aggregation.

    Delegates underlying UUID fallbacks, time execution durational calculations,
    and stdout/exception logging calls to the private RunsTrackerCore implementation.
    """

    def __init__(self, job_name: str, environment: str) -> None:
        """Initializes the RunsLogger proxy, delegating configuration setup to core.

        Args:
            job_name: Name of the executed process.
            environment: Execution environment context.
        """
        self._tracker = RunsTrackerCore(job_name, environment)

    @property
    def run_id(self) -> str:
        """Gets the active execution correlation ID."""
        return self._tracker.run_id

    @property
    def processed(self) -> int:
        """Gets the count of processed files."""
        return self._tracker.processed

    @property
    def downloaded(self) -> int:
        """Gets the count of downloaded files."""
        return self._tracker.downloaded

    @property
    def skipped(self) -> int:
        """Gets the count of skipped files."""
        return self._tracker.skipped

    @property
    def start_time(self) -> datetime | None:
        """Gets the start timestamp of the run."""
        return self._tracker.start_time

    def __enter__(self) -> RunsLogger:
        """Enters execution context tracking."""
        self._tracker.start()
        return self

    def update_metrics(self, processed: int, downloaded: int, skipped: int) -> None:
        """Appends metrics to execution tracker.

        Args:
            processed: Number of processed files.
            downloaded: Number of successfully downloaded files.
            skipped: Number of skipped files.
        """
        self._tracker.add_metrics(processed, downloaded, skipped)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        """Concludes execution context tracking, logging exit status.

        Propagates exceptions to standard system handlers (returns False).
        """
        return self._tracker.stop(exc_type, exc_val, exc_tb)
