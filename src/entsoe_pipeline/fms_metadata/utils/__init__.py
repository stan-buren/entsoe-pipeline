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

"""ENTSO-E FMS Metadata Utilities Subpackage.

Provides helper components for catalog parsing, serialization, and schema
transformation.
"""

from __future__ import annotations

from entsoe_pipeline.fms_metadata.utils.crawler import crawl_metadata_folder
from entsoe_pipeline.fms_metadata.utils.overview_parser import (
    get_domain_folders,
    parse_months_range,
)
from entsoe_pipeline.fms_metadata.utils.serializer import (
    save_fms_catalog,
    save_yaml_catalog,
)
from entsoe_pipeline.fms_metadata.utils.transformer import (
    compile_env_stats,
    compile_folder_metadata,
    map_raw_fms_item,
)

__all__ = [
    "compile_env_stats",
    "compile_folder_metadata",
    "crawl_metadata_folder",
    "get_domain_folders",
    "map_raw_fms_item",
    "parse_months_range",
    "save_fms_catalog",
    "save_yaml_catalog",
]
