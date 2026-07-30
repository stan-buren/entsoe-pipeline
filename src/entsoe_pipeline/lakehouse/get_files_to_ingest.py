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

"""Incremental file discovery and strict contract resolution gateway.

This module implements the "Early Binding via Rich Data Contract" pattern.
It retrieves pending files from the landing registry database, resolves physical S3
folder names into formal schema contracts (fms_name) via the central domains classifier,
enforces security boundaries (Fail-Fast logic), and groups files by their target schemas.
"""

from __future__ import annotations

import logging

from dataclasses import dataclass

from entsoe_pipeline.config.config_loader import get_classifier_config
from entsoe_pipeline.db import fetch_incremental_files_from_db

logger = logging.getLogger("entsoe_pipeline.lakehouse.get_files_to_ingest")

# Large datasets that we bypass during early development phases to optimize runtime cost
_GIANT_BYPASS_DOMAIN_CONTRACT = "OfferedTransferCapacitiesContinuousEvolution_11.1_r3"


@dataclass(frozen=True)
class IngestibleFile:
    """Rich Data Contract representing a file in S3 landing zone pending integration.

    Attributes:
        s3_key: Physical path URI of the object in S3 (e.g. 'iop/TP_export/Domain/...').
        xxhash: Unique content signature used for Change Data Capture (CDC).
        file_size_bytes: Size of the raw file in bytes, used for dynamic coalesce scaling.
        logical_domain: Folder directory name representing business domain on S3.
        fms_name: Strict data contract schema identifier (key in entsoe_fms_schemas.yml).
    """

    s3_key: str
    xxhash: str
    file_size_bytes: int
    logical_domain: str
    fms_name: str


def get_incremental_files_to_ingest() -> dict[str, list[IngestibleFile]]:
    """Discovers pending landing zone files and maps them to strict schema contracts.

    Performs the following steps:
    1. Fetches raw file records from the PostgreSQL landing registry database.
    2. Parses the physical domain folder from S3 keys.
    3. Resolves the folder to its formal schema contract (fms_name) using the classifier.
    4. Evaluates contract validity (Fail-Fast Gate: skips unclassified files).
    5. Filters out bypassed giant historical domains.
    6. Groups the files by their schema contract (fms_name) to support single-table batch writes.

    Returns:
        dict[str, list[IngestibleFile]]: Files grouped by target fms_name schema contract.
    """
    logger.info("Requesting raw pending files from core database module...")
    db_rows = fetch_incremental_files_from_db()

    # Load the central classification rules (Data Contract SSOT)
    classifier = get_classifier_config()

    ingestible_by_contract: dict[str, list[IngestibleFile]] = {}

    for row in db_rows:
        s3_key: str = row[0]
        xxhash: str = row[1]
        file_size_bytes: int = row[2]

        parts = s3_key.strip("/").split("/")
        if len(parts) < 4:
            logger.warning(
                "Skipping malformed S3 key path in landing registry: %s", s3_key
            )
            continue

        # Physical path pattern: {environment}/{active_folder}/{segment2}/{segment3}/...
        # Two cases:
        #   Hierarchical: parts[2] = domain (e.g. "Market") → match parts[3] against fms_name
        #   Flat:         parts[2] = direct classifier key (e.g. "OtherMarketInformation")
        logical_domain = parts[2]
        item_candidate = parts[3] if len(parts) >= 4 else None
        fms_name: str | None = None

        # Hierarchical: parts[2] is a top-level domain group
        if logical_domain in classifier.domains and item_candidate:
            for item in classifier.domains[logical_domain].values():
                if item.fms_name == item_candidate:
                    fms_name = item.fms_name
                    break
            # Version suffix fallback: EnergyPrices_12.1.D_r3.1 → EnergyPrices_12.1.D_r3
            if not fms_name:
                for item in classifier.domains[logical_domain].values():
                    if item_candidate.startswith(item.fms_name):
                        fms_name = item.fms_name
                        logger.debug(
                            "Version suffix resolved: '%s' → '%s'",
                            item_candidate,
                            fms_name,
                        )
                        break

        # Flat fallback: parts[2] is a direct key in some domain group
        if not fms_name:
            for domain_group in classifier.domains.values():
                if logical_domain in domain_group:
                    fms_name = domain_group[logical_domain].fms_name
                    break

        # Fail-Fast Gate: reject unmapped or unclassified S3 folder contents immediately
        if not fms_name:
            logger.warning(
                "Gateway Security Warning: Folder '%s' is not classified in entsoe_domains_classifier.yml. "
                "Bypassing file %s to prevent table corruption.",
                logical_domain,
                s3_key,
            )
            continue

        # Skip heavy historical bypass domains to preserve developer sandbox constraints
        if fms_name == _GIANT_BYPASS_DOMAIN_CONTRACT:
            continue

        file_obj = IngestibleFile(
            s3_key=s3_key,
            xxhash=xxhash,
            file_size_bytes=file_size_bytes,
            logical_domain=logical_domain,
            fms_name=fms_name,
        )

        ingestible_by_contract.setdefault(fms_name, []).append(file_obj)

    logger.info(
        "Ingestible files processed. Total unique contracts to ingest: %d (excluding %s).",
        len(ingestible_by_contract),
        _GIANT_BYPASS_DOMAIN_CONTRACT,
    )

    return ingestible_by_contract
