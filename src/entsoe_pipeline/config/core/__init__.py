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
    ClassificationRule,
    ClassifierConfig,
    ExclusionRule,
    LegacyRule,
)
from entsoe_pipeline.config.core.hosts import HostsConfig
from entsoe_pipeline.config.core.limits import RateLimitsConfig
from entsoe_pipeline.config.core.pipeline import EntsoeEnvConfig, PipelineConfig
from entsoe_pipeline.config.core.ports import PortsConfig
from entsoe_pipeline.config.core.project_root import find_project_root
from entsoe_pipeline.config.core.region import RegionConfig
from entsoe_pipeline.config.core.switch import switch_environment
from entsoe_pipeline.config.core.warning import CustomConfig

__all__ = [
    "BucketsConfig",
    "ClassificationRule",
    "ClassifierConfig",
    "CustomConfig",
    "EntsoeEnvConfig",
    "ExclusionRule",
    "HostsConfig",
    "LegacyRule",
    "PipelineConfig",
    "PortsConfig",
    "RateLimitsConfig",
    "RegionConfig",
    "find_project_root",
    "switch_environment",
]
