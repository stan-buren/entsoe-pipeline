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

"""ENTSO-E FMS Remote Metadata Discovery and Ingestion Module.

This script acts as a declarative orchestrator for the global FMS overview
metadata gathering process by delegating core logic to the central ingestion engine.
"""

from __future__ import annotations

import logging

from entsoe_pipeline.fms_metadata.core import ingest_overview_metadata
from entsoe_pipeline.logger import setup_logging

# Setup scoped logger strictly to our package namespace to prevent polluting root
logger = logging.getLogger("entsoe_pipeline.fms_metadata.overview_ingest")


def ingest_fms_metadata() -> None:
    """Orchestrates FMS metadata collection from IOP and PROD, updating overview.yml."""
    logger.info("Initializing FMS global overview metadata discovery...")
    ingest_overview_metadata()


if __name__ == "__main__":
    # Configure logging for the pipeline environment prior to execution
    setup_logging(level=logging.INFO, use_json=False)
    try:
        ingest_fms_metadata()
    except Exception:
        logger.exception("Metadata ingestion aborted due to fatal error")
        raise
