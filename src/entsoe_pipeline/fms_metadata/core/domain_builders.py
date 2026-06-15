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

"""Core domain selection configuration helpers for ENTSO-E data pipeline."""

from __future__ import annotations

from typing import Any


def build_default_domains_config(
    overview_data: dict[str, Any],
    popular_domains: dict[str, list[str]],
    target_environment: str | None = None,
) -> dict[str, Any]:
    """Builds the default selection mapping for ENTSO-E domains.

    Args:
        overview_data: Full metadata catalog overview structure.
        popular_domains: Registry of popular domain categories and folders.
        target_environment: Optional name of the specific environment to enable (e.g. 'IOP').

    Returns:
        dict[str, Any]: Selection hierarchy mapping each folder to a boolean.
    """
    transformed = {"environments": {}}
    environments = overview_data.get("environments", {})
    target_env = target_environment.upper() if target_environment else None

    for env_name, env_data in environments.items():
        is_env_enabled = (target_env is None) or (env_name.upper() == target_env)
        env_transformed = {"root_directories": []}
        for root_dir in env_data.get("root_directories", []):
            root_dir_name = root_dir.get("name")
            root_dir_transformed: dict[str, Any] = {"name": root_dir_name}

            if "domains" in root_dir:
                domains_transformed = {}
                for domain_name, folders in root_dir["domains"].items():
                    domain_folders = {}
                    for folder in folders:
                        is_popular = is_env_enabled and folder in popular_domains.get(
                            domain_name, []
                        )
                        domain_folders[folder] = is_popular
                    domains_transformed[domain_name] = domain_folders
                root_dir_transformed["domains"] = domains_transformed

            if "folders" in root_dir:
                folders_transformed = {}
                for folder in root_dir["folders"]:
                    folders_transformed[folder] = False
                root_dir_transformed["folders"] = folders_transformed

            env_transformed["root_directories"].append(root_dir_transformed)
        transformed["environments"][env_name] = env_transformed

    return transformed


def build_custom_domains_config(
    overview_data: dict[str, Any],
    selected_domains: list[Any],
    target_environment: str | None = None,
) -> dict[str, Any]:
    """Builds a custom selection mapping for specified domains.

    Args:
        overview_data: Full metadata catalog overview structure.
        selected_domains: List of domain names or nested configurations to enable.
        target_environment: Optional name of the specific environment to enable (e.g. 'IOP').

    Returns:
        dict[str, Any]: Selection hierarchy with specified domains enabled.
    """
    transformed = {"environments": {}}
    environments = overview_data.get("environments", {})
    target_env = target_environment.upper() if target_environment else None

    def get_domain_config(d_name: str) -> Any:
        if isinstance(selected_domains, dict):
            for k, v in selected_domains.items():
                if k.lower() == d_name.lower():
                    return v
            return False
        if isinstance(selected_domains, list):
            for item in selected_domains:
                if isinstance(item, str) and item.lower() == d_name.lower():
                    return True
                if isinstance(item, dict):
                    for k, v in item.items():
                        if k.lower() == d_name.lower():
                            return v
            return False
        return False

    for env_name, env_data in environments.items():
        is_env_enabled = (target_env is None) or (env_name.upper() == target_env)
        env_transformed = {"root_directories": []}
        for root_dir in env_data.get("root_directories", []):
            root_dir_name = root_dir.get("name")
            root_dir_transformed: dict[str, Any] = {"name": root_dir_name}

            if "domains" in root_dir:
                domains_transformed = {}
                for domain_name, folders in root_dir["domains"].items():
                    dom_cfg = get_domain_config(domain_name)
                    domain_folders = {}

                    if not is_env_enabled:
                        for folder in folders:
                            domain_folders[folder] = False
                    elif dom_cfg is True:
                        # Enable all folders in this domain
                        for folder in folders:
                            domain_folders[folder] = True
                    elif isinstance(dom_cfg, list):
                        # Config defines specific folders/files
                        for folder in folders:
                            folder_cfg = False
                            for f_item in dom_cfg:
                                if (
                                    isinstance(f_item, str)
                                    and f_item.lower() == folder.lower()
                                ):
                                    folder_cfg = True
                                    break
                                if isinstance(f_item, dict):
                                    for fk, fv in f_item.items():
                                        if fk.lower() == folder.lower():
                                            folder_cfg = fv
                                            break
                            domain_folders[folder] = folder_cfg
                    else:
                        # Disabled
                        for folder in folders:
                            domain_folders[folder] = False

                    domains_transformed[domain_name] = domain_folders
                root_dir_transformed["domains"] = domains_transformed

            if "folders" in root_dir:
                folders_transformed = {}
                for folder in root_dir["folders"]:
                    # All legacy publications folders are false in standard Custom mode
                    folders_transformed[folder] = False
                root_dir_transformed["folders"] = folders_transformed

            env_transformed["root_directories"].append(root_dir_transformed)
        transformed["environments"][env_name] = env_transformed

    return transformed


def build_extended_domains_config(
    overview_data: dict[str, Any],
    enabled_domains: list[str],
    enabled_legacy_folders: list[str],
    target_environment: str | None = None,
) -> dict[str, Any]:
    """Builds an extended selection mapping with granular folder-level control.

    Args:
        overview_data: Full metadata catalog overview structure.
        enabled_domains: Domains under TP_export to enable (e.g. ['Load']).
        enabled_legacy_folders: Legacy publication folders to enable.
        target_environment: Optional name of the specific environment to enable (e.g. 'IOP').

    Returns:
        dict[str, Any]: Selection hierarchy with specified domains and folders enabled.
    """
    transformed = {"environments": {}}
    environments = overview_data.get("environments", {})
    target_env = target_environment.upper() if target_environment else None

    for env_name, env_data in environments.items():
        is_env_enabled = (target_env is None) or (env_name.upper() == target_env)
        env_transformed = {"root_directories": []}
        for root_dir in env_data.get("root_directories", []):
            root_dir_name = root_dir.get("name")
            root_dir_transformed: dict[str, Any] = {"name": root_dir_name}

            if "domains" in root_dir:
                domains_transformed = {}
                for domain_name, folders in root_dir["domains"].items():
                    is_domain_enabled = is_env_enabled and (
                        domain_name in enabled_domains
                    )
                    domain_folders = {}
                    for folder in folders:
                        domain_folders[folder] = is_domain_enabled
                    domains_transformed[domain_name] = domain_folders
                root_dir_transformed["domains"] = domains_transformed

            if "folders" in root_dir:
                folders_transformed = {}
                for folder in root_dir["folders"]:
                    is_folder_enabled = is_env_enabled and (
                        folder in enabled_legacy_folders
                    )
                    folders_transformed[folder] = is_folder_enabled
                root_dir_transformed["folders"] = folders_transformed

            env_transformed["root_directories"].append(root_dir_transformed)
        transformed["environments"][env_name] = env_transformed

    return transformed


def build_domains_checklist(
    template_data: dict[str, Any],
    overview_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Processes active domains configuration checklist template.

    Args:
        template_data: Loaded YAML checklist configuration template.
        overview_data: Metadata catalog overview. Required if template_data
          is high-level and needs dynamic construction.

    Returns:
        dict[str, Any]: Fully constructed active domains selection checklist.

    Raises:
        ValueError: If config format is invalid or overview_data is missing when needed.
    """
    if "environments" in template_data:
        return template_data

    if not overview_data:
        raise ValueError(
            "overview_data is required to dynamically construct high-level domains checklists."
        )

    target_env = template_data.get("environment")

    if "popular_domains" in template_data:
        return build_default_domains_config(
            overview_data,
            template_data["popular_domains"],
            target_environment=target_env,
        )

    if "selected_domains" in template_data:
        return build_custom_domains_config(
            overview_data,
            template_data["selected_domains"],
            target_environment=target_env,
        )

    if "enabled_domains" in template_data or "enabled_legacy_folders" in template_data:
        enabled_domains = template_data.get("enabled_domains", [])
        enabled_legacy_folders = template_data.get("enabled_legacy_folders", [])
        return build_extended_domains_config(
            overview_data,
            enabled_domains,
            enabled_legacy_folders,
            target_environment=target_env,
        )

    raise ValueError(
        "Invalid checklist template configuration format. "
        "Must define one of: 'environments', 'popular_domains', "
        "'selected_domains', 'enabled_domains', or 'enabled_legacy_folders'."
    )
