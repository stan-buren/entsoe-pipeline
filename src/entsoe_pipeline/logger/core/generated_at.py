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

"""Module to generate standardized ISO 8601 UTC timestamp."""

from datetime import UTC, datetime


def get_generated_at_timestamp() -> str:
    """Generates the standardized ISO 8601 UTC execution timestamp.

    Returns:
        str: Standard ISO timestamp string (e.g., '2026-05-29T12:00:00Z').
    """
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
