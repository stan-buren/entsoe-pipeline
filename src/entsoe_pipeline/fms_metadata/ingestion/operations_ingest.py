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

"""ENTSO-E FMS Operations Domain Metadata Ingestion Module.

This script acts as a declarative orchestrator for the Operations domain metadata
ingestion process by delegating core logic to the central ingestion engine.
"""

from __future__ import annotations

import logging

from entsoe_pipeline import setup_logging
from entsoe_pipeline.fms_metadata.core import ingest_domain_metadata

# Setup scoped logger strictly to our package namespace to prevent polluting root
logger = logging.getLogger("entsoe_pipeline.fms_metadata.operations_ingest")


def ingest_operations_metadata(env: str | None = None) -> None:
    """Orchestrates metadata gathering for Operations domain.

    Crawls folders across both IOP and PROD environments.
    """
    logger.info("Initializing metadata gathering for Operations domain folders...")
    ingest_domain_metadata("Operations", env)


if __name__ == "__main__":
    setup_logging()
    ingest_operations_metadata()
