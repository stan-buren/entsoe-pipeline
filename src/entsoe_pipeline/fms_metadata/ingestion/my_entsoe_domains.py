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

"""Orchestrates generation of the active domains configuration checklist."""

from __future__ import annotations

import yaml

from entsoe_pipeline import (
    MY_ENTSOE_DOMAINS_CUSTOM_DIR,
    MY_ENTSOE_DOMAINS_DEFAULT_TEMPLATE_YML,
    MY_ENTSOE_DOMAINS_EXAMPLES_DIR,
    MY_ENTSOE_DOMAINS_YML,
    OVERVIEW_YML,
    get_custom_config,
)
from entsoe_pipeline.fms_metadata.core import build_domains_checklist


def generate_my_entsoe_domains() -> None:
    """Loads templates and environment configurations to write active domains checklist.

    Depending on the selected active mode (Default, Custom, or Example), loads
    the corresponding template file, dynamically expands it using overview metadata
    if necessary, and saves the final checklist to the configuration directory.

    Raises:
        FileNotFoundError: If a required template or the overview file is missing.
        ValueError: If active_mode or config file contents are invalid or unrecognized.
    """
    # 1. Load active mode configuration
    config = get_custom_config()
    active_mode = config.active_mode
    config_name = config.config_name

    # 2. Resolve template path based on active mode
    if active_mode == "Default":
        template_path = MY_ENTSOE_DOMAINS_DEFAULT_TEMPLATE_YML
    elif active_mode == "Custom":
        if not config_name:
            raise ValueError(
                "config_name must be defined in config_env/my_entsoe_domains.yml "
                "when active_mode is 'Custom'"
            )
        template_path = MY_ENTSOE_DOMAINS_CUSTOM_DIR / f"{config_name}.yml"
    elif active_mode == "Example":
        if not config_name:
            raise ValueError(
                "config_name must be defined in config_env/my_entsoe_domains.yml "
                "when active_mode is 'Example'"
            )
        template_path = MY_ENTSOE_DOMAINS_EXAMPLES_DIR / f"{config_name}.yml"
    else:
        raise ValueError(
            f"Unrecognized active_mode: '{active_mode}'. Expected 'Default', "
            f"'Custom', or 'Example'."
        )

    # 3. Read template configuration file.
    # For Default mode, if the template file does not exist, we treat it as empty and fall back
    # to loading entsoe_popular_domains.yml example to build it dynamically.
    template_data = {}
    if active_mode == "Default" and not template_path.exists():
        fallback_path = MY_ENTSOE_DOMAINS_EXAMPLES_DIR / "entsoe_popular_domains.yml"
        if not fallback_path.exists():
            raise FileNotFoundError(
                f"Default template not found at {template_path} and fallback "
                f"popular domains config not found at {fallback_path}"
            )
        with fallback_path.open(encoding="utf-8") as f:
            template_data = yaml.safe_load(f) or {}
    else:
        if not template_path.exists():
            raise FileNotFoundError(
                f"Active domains template config not found at: {template_path}"
            )
        with template_path.open(encoding="utf-8") as f:
            template_data = yaml.safe_load(f) or {}

    # If default template is completely empty, try fallback to entsoe_popular_domains.yml
    if active_mode == "Default" and not template_data:
        fallback_path = MY_ENTSOE_DOMAINS_EXAMPLES_DIR / "entsoe_popular_domains.yml"
        if fallback_path.exists():
            with fallback_path.open(encoding="utf-8") as f:
                template_data = yaml.safe_load(f) or {}

    # 4. Load overview_data only if the template configuration requires dynamic expansion
    overview_data = None
    if "environments" not in template_data:
        if not OVERVIEW_YML.exists():
            raise FileNotFoundError(
                f"Overview catalog file not found at: {OVERVIEW_YML}. "
                "Please run overview_ingest first."
            )
        with OVERVIEW_YML.open(encoding="utf-8") as f:
            overview_data = yaml.safe_load(f) or {}

    # 5. Build dynamic active domains checklist
    transformed = build_domains_checklist(template_data, overview_data)

    # 6. Save final checklist to target path using YAML observability facade
    from entsoe_pipeline.logger.yml_observability import save_yaml_with_observability

    save_yaml_with_observability(
        MY_ENTSOE_DOMAINS_YML,
        transformed,
        is_my_entsoe_domains=True,
    )


if __name__ == "__main__":
    generate_my_entsoe_domains()
