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

"""Core execution run tracking and duration calculation logic."""

from __future__ import annotations

import logging
import os
import uuid

from datetime import UTC, datetime
from types import TracebackType

from entsoe_pipeline.logger.api_observability import fms_api_counter

logger = logging.getLogger("entsoe_pipeline.logger.runs_logger")


class RunsTrackerCore:
    """Core tracking implementation for execution runs.

    Encapsulates all calculations, time tracking, UUID resolution, and exception logging.
    """

    def __init__(self, job_name: str, environment: str) -> None:
        """Initializes tracking configuration and resolves the execution correlation ID.

        Args:
            job_name: Name of the executed process.
            environment: Execution environment.
        """
        self.job_name = job_name
        self.environment = environment
        self.run_id = os.environ.get("KESTRA_EXECUTION_ID") or str(uuid.uuid4())
        self.processed = 0
        self.downloaded = 0
        self.skipped = 0
        self.start_time: datetime | None = None

    def start(self) -> None:
        """Records startup timestamp and logs run initialization."""
        self.start_time = datetime.now(UTC)
        logger.info(
            "Starting pipeline run %s for job %s in environment %s",
            self.run_id,
            self.job_name,
            self.environment,
        )

    def add_metrics(self, processed: int, downloaded: int, skipped: int) -> None:
        """Aggregates metrics counters.

        Args:
            processed: Count of processed files.
            downloaded: Count of downloaded files.
            skipped: Count of skipped files.
        """
        self.processed += processed
        self.downloaded += downloaded
        self.skipped += skipped

    def stop(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        _exc_tb: TracebackType | None,
    ) -> bool:
        """Calculates durations, logs execution exit status, and handles exceptions.

        Always returns False to ensure exceptions propagate up the stack.
        """
        if self.start_time is None:
            duration_secs = 0.0
        else:
            duration_secs = (datetime.now(UTC) - self.start_time).total_seconds()

        if exc_type is not None:
            logger.exception(
                "Job %s failed after %.2f seconds in environment %s. Run ID: %s. Error: %s",
                self.job_name,
                duration_secs,
                self.environment,
                self.run_id,
                exc_val,
            )
        else:
            logger.info(
                "Job %s completed successfully in %.2f seconds. Run ID: %s. "
                "Metrics: {processed: %d, downloaded: %d, skipped: %d}",
                self.job_name,
                duration_secs,
                self.run_id,
                self.processed,
                self.downloaded,
                self.skipped,
            )

        # Log and reset FMS API request stats if any requests were made
        stats = fms_api_counter.get_stats()
        total_requests = sum(stats.values())
        if total_requests > 0:
            logger.info(
                "FMS API Request Statistics: {"
                "IOP Export: %d, IOP Legacy: %d, "
                "Prod Export: %d, Prod Legacy: %d"
                "}",
                stats["iop_export"],
                stats["iop_legacy"],
                stats["prod_export"],
                stats["prod_legacy"],
            )
            fms_api_counter.reset()

        # Always return False so exceptions are propagated up
        return False
