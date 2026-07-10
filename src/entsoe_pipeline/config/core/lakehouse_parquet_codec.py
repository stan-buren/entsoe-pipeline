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

"""Immutable configurations class for Lakehouse Parquet Compression and size settings."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import yaml

from entsoe_pipeline.config.paths import LAKEHOUSE_PARQUET_CODEC_YML


@dataclass(frozen=True)
class ParquetWriteProperties:
    """Parquet write properties configuration.

    Attributes:
        compression_codec: The compression codec (e.g., 'zstd', 'snappy').
        compression_level: Compression level (relevant for ZSTD).
        target_parquet_size_bytes: Target output Parquet file size in bytes.
    """

    compression_codec: str
    compression_level: int
    target_parquet_size_bytes: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ParquetWriteProperties:
        """Constructs ParquetWriteProperties from dictionary."""
        return cls(
            compression_codec=str(data.get("compression_codec", "zstd")),
            compression_level=int(data.get("compression_level", 3)),
            target_parquet_size_bytes=int(
                data.get("target_parquet_size_bytes", 268435456)
            ),
        )


@dataclass(frozen=True)
class LakehouseParquetCodecConfig:
    """Immutable lakehouse parquet write and codec properties.

    Attributes:
        purge_raw_after_transform: Whether raw CSV files should be deleted after ETL.
        write_properties: Default Parquet write settings.
        publication_overrides: Per-publication dictionary overrides.
    """

    purge_raw_after_transform: bool
    write_properties: ParquetWriteProperties
    publication_overrides: dict[str, ParquetWriteProperties] = field(
        default_factory=dict
    )

    @classmethod
    def _from_yaml(cls) -> LakehouseParquetCodecConfig:
        """Loads and parses the lakehouse parquet configurations from YAML.

        Returns:
            LakehouseParquetCodecConfig: The immutable config object.
        """
        if not LAKEHOUSE_PARQUET_CODEC_YML.exists():
            raise FileNotFoundError(
                f"Lakehouse parquet codec configuration not found at: {LAKEHOUSE_PARQUET_CODEC_YML}"
            )

        with LAKEHOUSE_PARQUET_CODEC_YML.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        lakehouse_data = data.get("lakehouse", {})
        write_props_data = lakehouse_data.get("write_properties", {})
        overrides_data = lakehouse_data.get("publication_overrides", {})

        write_properties = ParquetWriteProperties.from_dict(write_props_data)

        publication_overrides = {}
        for pub_name, pub_data in overrides_data.items():
            # Inherit defaults and update with specific overrides
            merged = {**write_props_data, **pub_data}
            publication_overrides[pub_name] = ParquetWriteProperties.from_dict(merged)

        return cls(
            purge_raw_after_transform=bool(
                lakehouse_data.get("purge_raw_after_transform", False)
            ),
            write_properties=write_properties,
            publication_overrides=publication_overrides,
        )
