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

"""ENTSO-E FMS Legacy Publications Metadata Ingestion Module.

This script acts as a declarative orchestrator for all three historical legacy
releases (R1, R2, and R3) metadata ingestion by delegating core crawling and
cataloging logic to the central legacy ingestion engine.
"""

from __future__ import annotations

import logging

from entsoe_pipeline import setup_logging
from entsoe_pipeline.fms_metadata.core import ingest_legacy_metadata

logger = logging.getLogger("entsoe_pipeline.fms_metadata.legacy_ingest")


def ingest_all_legacy_metadata() -> None:
    """Orchestrates metadata gathering for all three historical legacy releases."""
    logger.info("Initializing metadata gathering for FMS Legacy Archives...")

    logger.info("Gathering Release 3 Archives (R3) metadata...")
    ingest_legacy_metadata("R3_Archives")

    logger.info("Gathering Release 2 Archives (R2) metadata...")
    ingest_legacy_metadata("R2_Archives")

    logger.info("Gathering Release 1 Archives (R1 CSV/XML) metadata...")
    ingest_legacy_metadata("R1_Archives_CSV_XML")

    logger.info("=== LEGACY METADATA INGESTION SUCCESSFULLY COMPLETED ===")


if __name__ == "__main__":
    # Setup console logging
    setup_logging(level=logging.INFO, use_json=False)
    ingest_all_legacy_metadata()
