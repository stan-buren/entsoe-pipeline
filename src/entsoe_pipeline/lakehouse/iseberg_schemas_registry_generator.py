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

"""Schema registry generator script wrapper for the ENTSO-E Iceberg Lakehouse.

This script acts as the high-level executor entry point, importing and executing
the core schema inference logic from entsoe_pipeline.lakehouse.core.
"""

from __future__ import annotations

import logging

from entsoe_pipeline.lakehouse.core.generate_iceberg_schemas import (
    generate_iceberg_schemas_registry,
)

logger = logging.getLogger(
    "entsoe_pipeline.lakehouse.iseberg_schemas_registry_generator"
)


def main() -> None:
    """Main registry generator script entry point."""
    logger.info("Triggering Iceberg Schema Registry Generation...")
    generate_iceberg_schemas_registry()


if __name__ == "__main__":
    main()
