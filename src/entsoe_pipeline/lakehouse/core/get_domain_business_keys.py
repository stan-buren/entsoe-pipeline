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

"""Low-level database schema analysis utilities for Iceberg table keys."""

from __future__ import annotations

import logging

from entsoe_pipeline.config.config_loader import FmsPublicationSchema

logger = logging.getLogger("entsoe_pipeline.lakehouse.core.get_domain_business_keys")


def get_domain_business_keys(publication_schema: FmsPublicationSchema) -> list[str]:
    """Resolves composite business primary keys from FMS publication schema.

    Analyzes schema structures to identify unique key coordinates needed for table
    joins during upsert (merge) operations. Heuristic: selects mandatory
    (required=True) string or timestamp columns, ignoring update metadata.

    Args:
        publication_schema: The parsed FMS domain schema configuration contract.

    Returns:
        list[str]: Column database names composing the composite primary key.
    """
    keys = []
    for col in publication_schema.columns:
        col_type = col.type.lower()
        if col.required and (col_type == "string" or col_type == "timestamp"):
            if col.db_name != "update_time_utc":
                keys.append(col.db_name)

    logger.debug(
        "Resolved business keys for schema '%s': %s",
        publication_schema.name,
        keys,
    )
    return keys
