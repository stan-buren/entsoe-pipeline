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

"""ENTSO-E Data Pipeline Observability & Logging Domain.

Exposes centralized logger configurations and domain exception hierarchies.
"""

from __future__ import annotations

from entsoe_pipeline.logger.api_observability import fms_api_counter
from entsoe_pipeline.logger.exceptions import (
    EntsoeApiError,
    EntsoeConfigurationError,
    EntsoeConnectionError,
    EntsoeDataValidationError,
    EntsoePipelineError,
)
from entsoe_pipeline.logger.json_observability import save_json_with_observability
from entsoe_pipeline.logger.kestra_observability import send_kestra_counter
from entsoe_pipeline.logger.logger_config import setup_logging
from entsoe_pipeline.logger.runs_logger import RunsLogger
from entsoe_pipeline.logger.yml_observability import save_yaml_with_observability

__all__ = [
    "EntsoeApiError",
    "EntsoeConfigurationError",
    "EntsoeConnectionError",
    "EntsoeDataValidationError",
    "EntsoePipelineError",
    "RunsLogger",
    "fms_api_counter",
    "save_json_with_observability",
    "save_yaml_with_observability",
    "send_kestra_counter",
    "setup_logging",
]
