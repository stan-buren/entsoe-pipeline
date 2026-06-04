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

"""ENTSO-E Data Pipeline library."""

import entsoe_pipeline.config.paths as _paths

from entsoe_pipeline.config.config_loader import (
    BucketsConfig,
    ClassifierConfig,
    EntsoeEnvConfig,
    PipelineConfig,
    PortsConfig,
    RateLimitsConfig,
    RegionConfig,
    get_buckets_config,
    get_classifier_config,
    get_config,
    get_env_config,
    get_limits_config,
    get_paths_config,
    get_ports_config,
    get_region_config,
)
from entsoe_pipeline.logger import (
    EntsoeApiError,
    EntsoeConfigurationError,
    EntsoeConnectionError,
    EntsoeDataValidationError,
    EntsoePipelineError,
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
    "EntsoeApiError",
    "EntsoeConfigurationError",
    "EntsoeConnectionError",
    "EntsoeDataValidationError",
    "EntsoeEnvConfig",
    "EntsoePipelineError",
    "PipelineConfig",
    "PortsConfig",
    "RateLimitsConfig",
    "RegionConfig",
    "get_buckets_config",
    "get_classifier_config",
    "get_config",
    "get_env_config",
    "get_limits_config",
    "get_paths_config",
    "get_ports_config",
    "get_region_config",
    "setup_logging",
]
__all__.extend(_paths.__all__)
