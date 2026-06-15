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

"""Job orchestrator script to ingest active ENTSO-E domains into the landing zone."""

import logging
import sys

from entsoe_pipeline import get_config, setup_logging
from entsoe_pipeline.io.sync import sync_active_domains
from entsoe_pipeline.lakehouse.generate_tree_for_my_entsoe_domains import (
    generate_tree_for_my_entsoe_domains,
)

logger = logging.getLogger("entsoe_pipeline.jobs.ingest_my_entsoe_domains")


def main() -> None:
    """Main job entry point to sync configured active ENTSO-E datasets."""
    setup_logging()

    logger.info("=== STARTING ENTSO-E ACTIVE DOMAINS INGESTION JOB ===")

    try:
        # 1. Automatically initialize active S3 directories
        logger.info("Initializing active S3 folder structures...")
        generate_tree_for_my_entsoe_domains()

        # 2. Run pre-flight readiness checks
        logger.info("Running pre-flight readiness checks...")
        import pytest

        exit_code = pytest.main(["-v", "tests/jobs", "--no-cov"])
        if exit_code != 0:
            logger.error(
                "Pre-flight readiness checks failed with exit code %s.", exit_code
            )
            sys.exit(1)
        logger.info("Pre-flight checks passed successfully.")

        # 3. Run remote file synchronization
        config = get_config()
        active_env = config.active_environment
        logger.info("Active environment selected: %s", active_env)

        metrics = sync_active_domains(active_env)

        logger.info("Sync metrics: %s", metrics)
        logger.info("=== INGESTION JOB COMPLETED SUCCESSFULLY ===")
    except Exception as e:
        logger.exception("Ingestion job failed with a fatal error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
