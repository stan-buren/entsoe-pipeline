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

"""FMS Ingestion Engine for computing human-friendly raw data sizes catalogs."""

from __future__ import annotations

import argparse
import logging

from pathlib import Path

from entsoe_pipeline import (
    SIZES_DIR,
    setup_logging,
)
from entsoe_pipeline.fms_metadata.core import compile_sizes_report
from entsoe_pipeline.logger import save_yaml_with_observability

# Setup scoped logger strictly to our package namespace to prevent polluting root.
logger = logging.getLogger("entsoe_pipeline.fms_metadata.ingestion.sizes_ingest")


def ingest_iop_tp_export_sizes(
    physical_catalog_dir: Path | None = None,
    sizes_dir: Path | None = None,
) -> None:
    """Ingests and ranks raw metadata sizes for the IOP Active TP_export directory.

    Args:
        physical_catalog_dir: Unused, kept for backward compatibility.
        sizes_dir: Optional custom sizes output directory.
    """
    del physical_catalog_dir
    logger.info("Ingesting raw data sizes for: IOP active domains (TP_export)...")
    output_path = (sizes_dir or SIZES_DIR) / "iop_tp_export.yml"

    report = compile_sizes_report(env_name="iop", root_dir="TP_export")

    save_yaml_with_observability(
        output_path=output_path,
        payload=report,
        generator_script_name="src/entsoe_pipeline/fms_metadata/ingestion/sizes_ingest.py",
    )
    logger.info("Saved IOP active sizes report to: %s", output_path)


def ingest_iop_tp_legacy_publications_sizes(
    physical_catalog_dir: Path | None = None,
    sizes_dir: Path | None = None,
) -> None:
    """Ingests and ranks raw metadata sizes for the IOP Legacy publications directory.

    Args:
        physical_catalog_dir: Unused, kept for backward compatibility.
        sizes_dir: Optional custom sizes output directory.
    """
    del physical_catalog_dir
    logger.info(
        "Ingesting raw data sizes for: IOP legacy domains (TP_Legacy_Publications)..."
    )
    output_path = (sizes_dir or SIZES_DIR) / "iop_tp_legacy_publications.yml"

    report = compile_sizes_report(env_name="iop", root_dir="TP_Legacy_Publications")

    save_yaml_with_observability(
        output_path=output_path,
        payload=report,
        generator_script_name="src/entsoe_pipeline/fms_metadata/ingestion/sizes_ingest.py",
    )
    logger.info("Saved IOP legacy sizes report to: %s", output_path)


def ingest_prod_tp_export_sizes(
    physical_catalog_dir: Path | None = None,
    sizes_dir: Path | None = None,
) -> None:
    """Ingests and ranks raw metadata sizes for the PROD Active TP_export directory.

    Args:
        physical_catalog_dir: Unused, kept for backward compatibility.
        sizes_dir: Optional custom sizes output directory.
    """
    del physical_catalog_dir
    logger.info("Ingesting raw data sizes for: PROD active domains (TP_export)...")
    output_path = (sizes_dir or SIZES_DIR) / "prod_tp_export.yml"

    report = compile_sizes_report(env_name="prod", root_dir="TP_export")

    save_yaml_with_observability(
        output_path=output_path,
        payload=report,
        generator_script_name="src/entsoe_pipeline/fms_metadata/ingestion/sizes_ingest.py",
    )
    logger.info("Saved PROD active sizes report to: %s", output_path)


def ingest_prod_tp_legacy_publications_sizes(
    physical_catalog_dir: Path | None = None,
    sizes_dir: Path | None = None,
) -> None:
    """Ingests and ranks raw metadata sizes for the PROD Legacy publications directory.

    Args:
        physical_catalog_dir: Unused, kept for backward compatibility.
        sizes_dir: Optional custom sizes output directory.
    """
    del physical_catalog_dir
    logger.info(
        "Ingesting raw data sizes for: PROD legacy domains (TP_Legacy_Publications)..."
    )
    output_path = (sizes_dir or SIZES_DIR) / "prod_tp_legacy_publications.yml"

    report = compile_sizes_report(env_name="prod", root_dir="TP_Legacy_Publications")

    save_yaml_with_observability(
        output_path=output_path,
        payload=report,
        generator_script_name="src/entsoe_pipeline/fms_metadata/ingestion/sizes_ingest.py",
    )
    logger.info("Saved PROD legacy sizes report to: %s", output_path)


def ingest_all_catalog_sizes(
    physical_catalog_dir: Path | None = None,
    sizes_dir: Path | None = None,
) -> None:
    """Orchestrates ingestion of all 4 human-friendly size reports.

    Args:
        physical_catalog_dir: Unused, kept for backward compatibility.
        sizes_dir: Optional custom sizes output directory.
    """
    del physical_catalog_dir
    logger.info("Executing comprehensive FMS raw metadata sizes ingestion...")
    ingest_iop_tp_export_sizes(sizes_dir=sizes_dir)
    ingest_iop_tp_legacy_publications_sizes(sizes_dir=sizes_dir)
    ingest_prod_tp_export_sizes(sizes_dir=sizes_dir)
    ingest_prod_tp_legacy_publications_sizes(sizes_dir=sizes_dir)
    logger.info("Successfully completed all sizes reports ingestion.")


def main() -> None:
    """CLI execution entrypoint."""
    setup_logging()
    parser = argparse.ArgumentParser(
        description="Compile human-friendly metadata reports detailing raw file sizes per domain."
    )
    parser.add_argument(
        "--target",
        choices=[
            "iop-tp-export",
            "iop-tp-legacy",
            "prod-tp-export",
            "prod-tp-legacy",
            "all",
        ],
        default="all",
        help="Specify which size report to rebuild. Defaults to rebuilding all.",
    )
    args = parser.parse_args()

    if args.target == "iop-tp-export":
        ingest_iop_tp_export_sizes()
    elif args.target == "iop-tp-legacy":
        ingest_iop_tp_legacy_publications_sizes()
    elif args.target == "prod-tp-export":
        ingest_prod_tp_export_sizes()
    elif args.target == "prod-tp-legacy":
        ingest_prod_tp_legacy_publications_sizes()
    else:
        ingest_all_catalog_sizes()


if __name__ == "__main__":
    main()
