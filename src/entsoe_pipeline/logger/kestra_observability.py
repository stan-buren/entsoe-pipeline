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

"""Kestra-specific custom metrics observability integration helper.

Exposes lightweight functions to push custom metrics (counters, timers)
from execution containers back to the Kestra orchestrator.
"""

from __future__ import annotations

import json


def send_kestra_counter(
    name: str, value: int, tags: dict[str, str] | None = None
) -> None:
    """Sends a custom counter metric to Kestra via stdout JSON stream.

    Args:
        name: Unique name of the counter metric.
        value: Integer count value to increment/add.
        tags: Optional metadata key-value tags for categorization.
    """
    payload = {
        "metrics": [
            {
                "name": name,
                "type": "counter",
                "value": value,
                "tags": tags or {},
            }
        ]
    }
    print(f"::{json.dumps(payload)}::")
