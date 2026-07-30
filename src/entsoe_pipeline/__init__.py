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

"""ENTSO-E Data Pipeline library.

This library provides core components, configuration loaders, S3 I/O sync,
logger setups, and Apache Spark integrations for the ENTSO-E metadata pipeline.

All repository and workspace paths are dynamically resolved and bound to this
package namespace, acting as the Single Source of Truth (SSOT). You can import
these path constants directly from the package:

Typical usage example:

  from entsoe_pipeline import PROJECT_ROOT, DATA_DIR, CONFIG_DIR
  print(f"Project root is: {PROJECT_ROOT}")
  print(f"Data directory: {DATA_DIR}")
"""

import typing

import entsoe_pipeline.config.paths as _paths

from entsoe_pipeline.config.config_loader import (
    BucketsConfig,
    ClassifierConfig,
    CustomConfig,
    EntsoeEnvConfig,
    EntsoeFmsSchemasConfig,
    FmsColumnSchema,
    FmsPublicationSchema,
    HostsConfig,
    LakehouseConfig,
    LakehouseParquetCodecConfig,
    PipelineConfig,
    PortsConfig,
    RateLimitsConfig,
    RegionConfig,
    UrlsConfig,
    VolumesConfig,
    get_active_domains_config,
    get_buckets_config,
    get_classifier_config,
    get_config,
    get_crawler_config,
    get_custom_config,
    get_db_schema_config,
    get_env_config,
    get_fms_extensions,
    get_fms_schemas_config,
    get_hosts_config,
    get_lakehouse_config,
    get_lakehouse_parquet_codec_config,
    get_landing_bucket_schema,
    get_limits_config,
    get_namespaces_config,
    get_paths_config,
    get_ports_config,
    get_region_config,
    get_spark_config,
    get_urls_config,
    get_volumes_config,
)
from entsoe_pipeline.config.env_resolver import resolve_active_environment
from entsoe_pipeline.lakehouse import (
    IngestibleFile,
    IngestionAttemptLog,
    add_csv_to_iceberg_table,
    commit_ingestion_attempts,
    ensure_iceberg_table_exists,
    get_incremental_files_to_ingest,
)
from entsoe_pipeline.logger import (
    EntsoeApiError,
    EntsoeConfigurationError,
    EntsoeConnectionError,
    EntsoeDataValidationError,
    EntsoePipelineError,
    RunsLogger,
    fms_api_counter,
    save_json_with_observability,
    save_yaml_with_observability,
    send_kestra_counter,
    setup_logging,
)
from entsoe_pipeline.spark import (
    build_spark_session,
    read_landing_csv_dataset,
)
from entsoe_pipeline.vendor_patches.entsoe_py import ConfigurableEntsoeFileClient

# Dynamically bind all path constants to package namespace
for _name in _paths.__all__:
    globals()[_name] = getattr(_paths, _name)

__all__ = [
    "BucketsConfig",
    "ClassifierConfig",
    "ConfigurableEntsoeFileClient",
    "CustomConfig",
    "EntsoeApiError",
    "EntsoeConfigurationError",
    "EntsoeConnectionError",
    "EntsoeDataValidationError",
    "EntsoeEnvConfig",
    "EntsoeFmsSchemasConfig",
    "EntsoePipelineError",
    "FmsColumnSchema",
    "FmsPublicationSchema",
    "HostsConfig",
    "IngestibleFile",
    "IngestionAttemptLog",
    "LakehouseConfig",
    "LakehouseParquetCodecConfig",
    "PipelineConfig",
    "PortsConfig",
    "RateLimitsConfig",
    "RegionConfig",
    "RunsLogger",
    "UrlsConfig",
    "VolumesConfig",
    "add_csv_to_iceberg_table",
    "commit_ingestion_attempts",
    "ensure_iceberg_table_exists",
    "fms_api_counter",
    "get_active_domains_config",
    "get_buckets_config",
    "get_classifier_config",
    "get_config",
    "get_crawler_config",
    "get_custom_config",
    "get_db_schema_config",
    "get_env_config",
    "get_fms_extensions",
    "get_fms_schemas_config",
    "get_hosts_config",
    "get_incremental_files_to_ingest",
    "get_lakehouse_config",
    "get_lakehouse_parquet_codec_config",
    "get_landing_bucket_schema",
    "get_limits_config",
    "get_namespaces_config",
    "get_paths_config",
    "get_ports_config",
    "get_region_config",
    "get_spark_config",
    "get_urls_config",
    "get_volumes_config",
    "resolve_active_environment",
    "save_json_with_observability",
    "save_yaml_with_observability",
    "send_kestra_counter",
    "setup_logging",
]
__all__.extend(_paths.__all__)


def __getattr__(name: str) -> typing.Any:
    """Allow dynamic attributes for static type checkers."""
    if name in __all__:
        return globals().get(name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
