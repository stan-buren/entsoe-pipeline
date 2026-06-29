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
    HostsConfig,
    LakehouseConfig,
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
    get_custom_config,
    get_env_config,
    get_hosts_config,
    get_lakehouse_config,
    get_landing_bucket_schema,
    get_limits_config,
    get_paths_config,
    get_ports_config,
    get_region_config,
    get_urls_config,
    get_volumes_config,
)
from entsoe_pipeline.config.env_resolver import resolve_active_environment
from entsoe_pipeline.logger import (
    EntsoeApiError,
    EntsoeConfigurationError,
    EntsoeConnectionError,
    EntsoeDataValidationError,
    EntsoePipelineError,
    RunsLogger,
    save_json_with_observability,
    save_yaml_with_observability,
    setup_logging,
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
    "EntsoePipelineError",
    "HostsConfig",
    "LakehouseConfig",
    "PipelineConfig",
    "PortsConfig",
    "RateLimitsConfig",
    "RegionConfig",
    "RunsLogger",
    "UrlsConfig",
    "VolumesConfig",
    "get_active_domains_config",
    "get_buckets_config",
    "get_classifier_config",
    "get_config",
    "get_custom_config",
    "get_env_config",
    "get_hosts_config",
    "get_lakehouse_config",
    "get_landing_bucket_schema",
    "get_limits_config",
    "get_paths_config",
    "get_ports_config",
    "get_region_config",
    "get_urls_config",
    "get_volumes_config",
    "resolve_active_environment",
    "save_json_with_observability",
    "save_yaml_with_observability",
    "setup_logging",
]
__all__.extend(_paths.__all__)


def __getattr__(name: str) -> typing.Any:
    """Allow dynamic attributes for static type checkers."""
    if name in __all__:
        return globals().get(name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
