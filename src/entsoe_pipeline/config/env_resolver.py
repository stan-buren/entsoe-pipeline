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

# ruff: noqa: S110
"""Single Source of Truth for environment resolution logic.

Resolves the active target environment based on checklist configuration
or environment fallbacks.
"""

from __future__ import annotations

import yaml


def resolve_active_environment() -> str:
    """Resolves the environment to use, preferring the one from my_entsoe_domains.yml if defined.

    Returns:
        str: Resolved active environment name ('IOP' or 'PROD').
    """
    from entsoe_pipeline.config.config_loader import get_config
    from entsoe_pipeline.config.paths import CONFIG_DIR, MY_ENTSOE_DOMAINS_YML

    if MY_ENTSOE_DOMAINS_YML.exists():
        try:
            with MY_ENTSOE_DOMAINS_YML.open(encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            env = data.get("environment")
            if env:
                return str(env).upper()
        except Exception:
            pass

    try:
        return get_config().active_environment
    except Exception:
        pass

    # Fallback to direct file loading if config loader fails or is uninitialized
    config_path = CONFIG_DIR / "enviroment.yml"
    if config_path.exists():
        try:
            with config_path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            env = data.get("active_environment")
            if env:
                return str(env).upper()
        except Exception:
            pass

    return "PROD"
