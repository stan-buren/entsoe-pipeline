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

"""ENTSO-E physical metadata database core queries and transactional writes."""

from __future__ import annotations

from entsoe_pipeline.db.core.query_for_landing_files_pending_integration import (
    fetch_incremental_files_from_db,
)
from entsoe_pipeline.db.core.write_ingestion_status import (
    write_ingestion_attempts_to_db,
)

__all__ = [
    "fetch_incremental_files_from_db",
    "write_ingestion_attempts_to_db",
]
