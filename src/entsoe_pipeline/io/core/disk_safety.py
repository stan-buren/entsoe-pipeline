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

"""Operational disk space resource validation operations."""

from __future__ import annotations

import logging
import shutil

from pathlib import Path

logger = logging.getLogger("entsoe_pipeline.io.core.disk_safety")


def verify_free_disk_space(
    target_dir: Path,
    size_bytes: int,
    safety_margin_mb: int = 100,
) -> None:
    """Verifies that the target directory has sufficient free space.

    Ensures that the free storage space is greater than the safety margin
    and enough to comfortably house the download.

    Args:
        target_dir: The directory on disk to evaluate.
        size_bytes: The size of the file being processed.
        safety_margin_mb: Minimum baseline safety margin in Megabytes.

    Raises:
        EntsoePipelineError: If free capacity falls below thresholds.
    """
    _total, _used, free = shutil.disk_usage(target_dir)
    margin_bytes = safety_margin_mb * 1024 * 1024
    required_bytes = max(margin_bytes, size_bytes * 2)

    if free < required_bytes:
        logger.error(
            "Insufficient local disk space on %s. Free: %d bytes, Required safety margin: %d bytes.",
            target_dir,
            free,
            required_bytes,
        )
        from entsoe_pipeline.logger.exceptions import EntsoePipelineError

        raise EntsoePipelineError(
            f"Insufficient local disk space on {target_dir}. "
            f"Free: {free} bytes, Required safety margin: {required_bytes} bytes."
        )
