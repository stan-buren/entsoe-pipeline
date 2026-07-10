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

from entsoe_pipeline import (
    RunsLogger,
    resolve_active_environment,
    setup_logging,
)
from entsoe_pipeline.io.sync import sync_active_domains
from entsoe_pipeline.preflight import run_ingest_landing_preflight

logger = logging.getLogger("entsoe_pipeline.jobs.ingest_my_entsoe_domains")


def main() -> None:
    """Main job entry point to sync configured active ENTSO-E datasets."""
    setup_logging()

    logger.info("=== STARTING ENTSO-E ACTIVE DOMAINS INGESTION JOB ===")

    try:
        # 1. Execute ingestion preflight (initialize S3 paths and run readiness checks)
        run_ingest_landing_preflight()

        # 3. Resolve target environments from checklist
        from entsoe_pipeline import get_active_domains_config

        checklist = get_active_domains_config()
        environments = checklist.get("environments", {})

        envs_to_sync = []
        for env_name in environments:
            from entsoe_pipeline.io.core.config_parser import extract_active_folders

            if extract_active_folders(env_name, checklist):
                envs_to_sync.append(env_name)

        if not envs_to_sync:
            envs_to_sync = [resolve_active_environment()]

        logger.info("Environments selected for ingestion: %s", envs_to_sync)

        total_processed = 0
        total_downloaded = 0
        total_skipped = 0

        for env in envs_to_sync:
            logger.info("Starting remote file synchronization for environment: %s", env)
            with RunsLogger(
                job_name="ingest_my_entsoe_domains", environment=env
            ) as tracker:
                metrics = sync_active_domains(env, run_id=tracker.run_id)
                tracker.update_metrics(
                    processed=metrics["processed"],
                    downloaded=metrics["downloaded"],
                    skipped=metrics["skipped"],
                )
                total_processed += tracker.processed
                total_downloaded += tracker.downloaded
                total_skipped += tracker.skipped

            logger.info("Finished sync for %s. Metrics: %s", env, metrics)

        print(
            f'::{{"outputs": {{"processed": {total_processed}, '
            f'"downloaded": {total_downloaded}, "skipped": {total_skipped}}}}}::'
        )
        logger.info("=== INGESTION JOB COMPLETED SUCCESSFULLY ===")
    except Exception as e:
        logger.exception("Ingestion job failed with a fatal error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
