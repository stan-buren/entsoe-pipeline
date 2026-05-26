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

from __future__ import annotations

import os

import yaml

from dotenv import load_dotenv

from entsoe_pipeline.config.config_loader import get_env_config
from entsoe_pipeline.config.paths import CONFIG_DIR, ENV_FILE
from entsoe_pipeline.vendor_patches.entsoe_py import ConfigurableEntsoeFileClient

# =============================================================================
# CLIENT FACTORY INTERFACES
# =============================================================================


def create_fms_client(env_name: str | None = None) -> ConfigurableEntsoeFileClient:
    """Creates and authenticates a client for the specified environment.

    If no environment name is provided, it defaults to the globally configured
    active environment from environment.yml.

    Args:
        env_name: Optional environment identifier ('IOP' or 'PROD').

    Returns:
        An authenticated and fully configured ConfigurableEntsoeFileClient instance.

    Raises:
        FileNotFoundError: If the environment configuration file is missing.
        ValueError: If required credentials or URLs are missing.
    """
    # 1. If no specific environment is requested, delegate to the active default config
    if env_name is None:
        active_config = get_env_config()
        return ConfigurableEntsoeFileClient(
            username=active_config.email,
            pwd=active_config.password,
            base_url=active_config.base_url,
            token_url=active_config.token_url,
        )

    # 2. Otherwise, load the config file manually to switch environments dynamically
    env_file = ENV_FILE
    if env_file.exists():
        load_dotenv(dotenv_path=env_file, override=True)
    else:
        load_dotenv(override=True)

    config_path = CONFIG_DIR / "enviroment.yml"
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with config_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    environments = data.get("environments", {})
    if env_name not in environments:
        raise ValueError(
            f"Requested environment '{env_name}' is missing "
            "from the configuration registry."
        )

    env_payload = environments[env_name]
    base_url = env_payload.get("base_url")
    token_url = env_payload.get("token_url")

    if not base_url or not token_url:
        raise ValueError(
            f"Environment '{env_name}' must configure both 'base_url' and 'token_url'."
        )

    credential_keys = env_payload.get("credential_keys", {})
    raw_email_var = credential_keys.get("email")
    raw_pwd_var = credential_keys.get("password")

    email = os.environ.get(raw_email_var) if raw_email_var else None
    password = os.environ.get(raw_pwd_var) if raw_pwd_var else None

    if not email or not password:
        raise ValueError(
            f"Credentials not found in environment variables for '{env_name}'. "
            f"Please check your .env settings."
        )

    return ConfigurableEntsoeFileClient(
        username=email,
        pwd=password,
        base_url=base_url,
        token_url=token_url,
    )
