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

"""Core configuration classes and schemas package."""

from entsoe_pipeline.config.core.buckets import BucketsConfig
from entsoe_pipeline.config.core.classifier import (
    ClassifierConfig,
    LegacyRule,
)
from entsoe_pipeline.config.core.entsoe_fms_schemas import (
    EntsoeFmsSchemasConfig,
    FmsColumnSchema,
    FmsPublicationSchema,
)
from entsoe_pipeline.config.core.hosts import HostsConfig
from entsoe_pipeline.config.core.lakehouse import LakehouseConfig
from entsoe_pipeline.config.core.lakehouse_parquet_codec import (
    LakehouseParquetCodecConfig,
)
from entsoe_pipeline.config.core.limits import RateLimitsConfig
from entsoe_pipeline.config.core.namespaces import NamespacesConfig
from entsoe_pipeline.config.core.pipeline import EntsoeEnvConfig, PipelineConfig
from entsoe_pipeline.config.core.ports import PortsConfig
from entsoe_pipeline.config.core.project_root import find_project_root
from entsoe_pipeline.config.core.region import RegionConfig
from entsoe_pipeline.config.core.spark import SparkConfig
from entsoe_pipeline.config.core.switch import switch_environment
from entsoe_pipeline.config.core.urls import UrlsConfig
from entsoe_pipeline.config.core.volumes import VolumesConfig
from entsoe_pipeline.logger.core.warning import CustomConfig

__all__ = [
    "BucketsConfig",
    "ClassifierConfig",
    "CustomConfig",
    "EntsoeEnvConfig",
    "EntsoeFmsSchemasConfig",
    "FmsColumnSchema",
    "FmsPublicationSchema",
    "HostsConfig",
    "LakehouseConfig",
    "LakehouseParquetCodecConfig",
    "LegacyRule",
    "NamespacesConfig",
    "PipelineConfig",
    "PortsConfig",
    "RateLimitsConfig",
    "RegionConfig",
    "SparkConfig",
    "UrlsConfig",
    "VolumesConfig",
    "find_project_root",
    "switch_environment",
]
