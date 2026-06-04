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

from __future__ import annotations

import logging

from entsoe_pipeline import setup_logging
from entsoe_pipeline.fms_metadata.core import ingest_overview_tree_metadata

# Setup scoped logger strictly to our package namespace to prevent polluting root
logger = logging.getLogger("entsoe_pipeline.fms_metadata.overview_tree_ingest")


def ingest_fms_overview_tree() -> None:
    """Orchestrates FMS local overview tree compilation from local catalogs."""
    logger.info("Initializing local FMS metadata overview tree compilation...")
    ingest_overview_tree_metadata()


if __name__ == "__main__":
    # Setup human-readable console logging on CLI execution
    setup_logging(level=logging.INFO, use_json=False)
    try:
        ingest_fms_overview_tree()
    except Exception:
        logger.exception(
            "Metadata overview tree compilation aborted due to fatal error"
        )
        raise
