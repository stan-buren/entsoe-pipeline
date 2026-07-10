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

"""Low-level I/O core operations package."""

from entsoe_pipeline.io.core.config_parser import extract_active_folders
from entsoe_pipeline.io.core.disk_safety import verify_free_disk_space
from entsoe_pipeline.io.core.file_selector import select_files_to_sync
from entsoe_pipeline.io.core.fms_operations import (
    download_raw_zip_from_fms,
    extract_csv_bytes_from_zip,
)
from entsoe_pipeline.io.core.idempotency import (
    check_idempotency,
    register_downloaded_file,
)
from entsoe_pipeline.io.core.path_resolver import resolve_target_mappings
from entsoe_pipeline.io.core.s3_operations import (
    s3_object_exists,
    upload_local_file_to_s3,
)

__all__ = [
    "check_idempotency",
    "download_raw_zip_from_fms",
    "extract_active_folders",
    "extract_csv_bytes_from_zip",
    "register_downloaded_file",
    "resolve_target_mappings",
    "s3_object_exists",
    "select_files_to_sync",
    "upload_local_file_to_s3",
    "verify_free_disk_space",
]
