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

"""Lakehouse S3 bucket and directory tree initialization routines."""

from __future__ import annotations

from entsoe_pipeline.lakehouse.add_csv_to_iceberg import add_csv_to_iceberg_table
from entsoe_pipeline.lakehouse.generate_tree_for_my_entsoe_domains import (
    generate_tree_for_my_entsoe_domains,
)
from entsoe_pipeline.lakehouse.get_files_to_ingest import (
    IngestibleFile,
    get_incremental_files_to_ingest,
)
from entsoe_pipeline.lakehouse.iceberg_tables import ensure_iceberg_table_exists
from entsoe_pipeline.lakehouse.ingestion_status_db_registry import (
    IngestionAttemptLog,
    commit_ingestion_attempts,
)

__all__ = [
    "IngestibleFile",
    "IngestionAttemptLog",
    "add_csv_to_iceberg_table",
    "commit_ingestion_attempts",
    "ensure_iceberg_table_exists",
    "generate_tree_for_my_entsoe_domains",
    "get_incremental_files_to_ingest",
]
