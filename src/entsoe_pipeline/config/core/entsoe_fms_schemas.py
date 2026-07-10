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

"""ENTSO-E FMS publications schemas configurations."""

from __future__ import annotations

from dataclasses import dataclass

import yaml

from entsoe_pipeline.config.paths import ENTSOE_FMS_SCHEMAS_YML


@dataclass(frozen=True)
class FmsColumnSchema:
    """Immutable column schema definition from entsoe_fms_schemas.yml.

    Attributes:
        csv_name (str): Original column name in CSV.
        db_name (str): Snake-case column name used in databases.
        type (str): Datatype (string, timestamp, boolean, decimal(18,4), etc.).
        required (bool): Whether this column is mandatory.
        format (str | None): Date/Time format if applicable.
        example (str | None): Example value.
        description (str | None): Description of the column.
    """

    csv_name: str
    db_name: str
    type: str
    required: bool
    format: str | None = None
    example: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class FmsPublicationSchema:
    """Immutable publication schema configuration.

    Attributes:
        name (str): Human-readable name of the publication.
        zendesk_url (str | None): Zendesk reference URL.
        columns (list[FmsColumnSchema]): List of publication column specifications.
    """

    name: str
    zendesk_url: str | None
    columns: list[FmsColumnSchema]


@dataclass(frozen=True)
class EntsoeFmsSchemasConfig:
    """Immutable registry of all ENTSO-E FMS publications.

    Attributes:
        publications (dict[str, FmsPublicationSchema]): Mapping of publication key to its schema.
    """

    publications: dict[str, FmsPublicationSchema]

    @classmethod
    def _from_yaml(cls) -> EntsoeFmsSchemasConfig:
        """Loads and parses the publications schema specification from config/entsoe_fms_schemas.yml.

        Returns:
            EntsoeFmsSchemasConfig: The parsed schemas config object.
        """
        with ENTSOE_FMS_SCHEMAS_YML.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        raw_pubs = data.get("publications", {})
        publications = {}
        for pub_key, pub_val in raw_pubs.items():
            columns = []
            for col in pub_val.get("columns", []):
                columns.append(
                    FmsColumnSchema(
                        csv_name=str(col.get("csv_name", "")),
                        db_name=str(col.get("db_name", "")),
                        type=str(col.get("type", "string")),
                        required=bool(col.get("required", False)),
                        format=col.get("format"),
                        example=str(col.get("example"))
                        if col.get("example") is not None
                        else None,
                        description=col.get("description"),
                    )
                )
            publications[pub_key] = FmsPublicationSchema(
                name=str(pub_val.get("name", "")),
                zendesk_url=pub_val.get("zendesk_url"),
                columns=columns,
            )

        return cls(publications=publications)
