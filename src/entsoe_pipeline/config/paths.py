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


import typing

from entsoe_pipeline.config.core.project_root import find_project_root

# Dynamically load all path constants using config_loader SSOT
PROJECT_ROOT = find_project_root()
PATHS_YML = PROJECT_ROOT / "config" / "paths.yml"

from entsoe_pipeline.config.config_loader import load_paths_config  # noqa: E402

_paths_data = load_paths_config(PROJECT_ROOT)

# Populate module namespace dynamically to establish SSOT exports
for _key, _rel_val in _paths_data.items():
    globals()[_key] = PROJECT_ROOT / _rel_val

# Expose constants for package-wide utilization
__all__ = ["PROJECT_ROOT"]
__all__.extend(list(_paths_data.keys()))


def __getattr__(name: str) -> typing.Any:
    """Allow dynamic attributes for static type checkers."""
    if name in __all__:
        return globals().get(name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
