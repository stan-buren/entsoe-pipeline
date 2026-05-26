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

"""ENTSO-E Data Pipeline Custom Exception Hierarchy.

Defines a clean, domain-specific exception hierarchy allowing callers
and orchestrators (like Airflow) to catch, retry, or handle specific errors cleanly.
"""

from __future__ import annotations


class EntsoePipelineError(Exception):
    """Base exception class for all operational failures in the ENTSO-E pipeline."""


class EntsoeConfigurationError(EntsoePipelineError):
    """Raised when configurations or credentials are missing or invalid."""


class EntsoeConnectionError(EntsoePipelineError):
    """Raised when network operations, authentication, or API endpoints fail."""


class EntsoeApiError(EntsoePipelineError):
    """Raised when remote FMS API returns unsuccessful responses or payloads."""


class EntsoeDataValidationError(EntsoePipelineError):
    """Raised when data files fail validation or schema checks."""
