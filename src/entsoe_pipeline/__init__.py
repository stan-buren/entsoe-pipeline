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

from entsoe_pipeline.config.config_loader import (
    BucketsConfig,
    EntsoeEnvConfig,
    PipelineConfig,
    PortsConfig,
    RateLimitsConfig,
    RegionConfig,
    get_buckets_config,
    get_config,
    get_env_config,
    get_limits_config,
    get_ports_config,
    get_region_config,
)
from entsoe_pipeline.config.paths import (
    ADR_DIR,
    ADR_TEMPLATE_PATH,
    CONFIG_DIR,
    DATA_DIR,
    ENV_FILE,
    FMS_METADATA_DIR,
    MANUAL_DATA_DIR,
    OVERVIEW_YML,
    PROJECT_ROOT,
    TESTS_DIR,
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

__all__ = [
    # paths
    "ADR_DIR",
    "ADR_TEMPLATE_PATH",
    "CONFIG_DIR",
    "DATA_DIR",
    "ENV_FILE",
    "FMS_METADATA_DIR",
    "MANUAL_DATA_DIR",
    "OVERVIEW_YML",
    "PROJECT_ROOT",
    "TESTS_DIR",
    "BucketsConfig",
    # vendor patches
    "ConfigurableEntsoeFileClient",
    "EntsoeApiError",
    "EntsoeConfigurationError",
    "EntsoeConnectionError",
    "EntsoeDataValidationError",
    "EntsoeEnvConfig",
    "EntsoePipelineError",
    # configs
    "PipelineConfig",
    "PortsConfig",
    "RateLimitsConfig",
    "RegionConfig",
    "get_buckets_config",
    "get_config",
    "get_env_config",
    "get_limits_config",
    "get_ports_config",
    "get_region_config",
    # logger & exceptions
    "setup_logging",
]
