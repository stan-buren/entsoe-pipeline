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

"""CLI job runner for the ENTSO-E FMS CSV ingestion pipeline.

This module provides a command-line interface to execute the ETL batch ingestion
process. It handles folder parameter parsing, optional forced reload commands,
and error handling during execution.

Typical usage example:

  $ python jobs/ingest_fms_data.py --folder EnergyPrices_12.1.D_r3 --force
"""

import argparse
import sys

from pathlib import Path

# Appends the project root to system paths to allow entsoe_pipeline imports.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from entsoe_pipeline.ingestion.batch_fms_csv import ingest_folder  # noqa: E402


def main() -> None:
    """Parses command-line arguments and triggers the FMS CSV ingestion."""
    parser = argparse.ArgumentParser(
        description=(
            "Ingest ENTSO-E FMS CSV raw data to S3 Parquet & Apache Iceberg tables."
        )
    )
    parser.add_argument(
        "--folder",
        type=str,
        default="EnergyPrices_12.1.D_r3",
        help="Target folder name on the FMS server or simulated data folder.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Force ingestion: bypass Tier 1 check, overwrite S3 Parquet, and"
            " reload Iceberg table."
        ),
    )

    args = parser.parse_args()

    print(
        f"[ETL-START] Commencing ingestion for folder: {args.folder}"
        f" (force={args.force})"
    )
    try:
        ingest_folder(folder_name=args.folder, force_reload=args.force)
        print("[ETL-COMPLETE] Ingestion finished successfully!")
    except Exception as e:
        print(
            f"[ETL-FAILED] Fatal error encountered during ETL execution: {e}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
