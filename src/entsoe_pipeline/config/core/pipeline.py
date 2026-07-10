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

"""Orchestrator and composite configuration module for the ENTSO-E data pipeline.

This module defines the root master configuration class, `PipelineConfig`, which
acts as a composite configuration object. It orchestrates the loading of all
specialized sub-configurations (such as S3 buckets, AWS regions, network ports,
hosts, and rate limits) into a single, unified, type-safe configuration tree.
It also parses active environment specifications and credential bindings.

Typical usage example:

    config = PipelineConfig._from_yaml()
    print(f"Active env: {config.active_environment}")
    print(f"Landing bucket: {config.buckets.s3_landing_bucket}")
"""

from __future__ import annotations

import os

from dataclasses import dataclass

import yaml

from dotenv import load_dotenv

from entsoe_pipeline.config.core.buckets import BucketsConfig
from entsoe_pipeline.config.core.hosts import HostsConfig
from entsoe_pipeline.config.core.lakehouse import LakehouseConfig
from entsoe_pipeline.config.core.limits import RateLimitsConfig
from entsoe_pipeline.config.core.ports import PortsConfig
from entsoe_pipeline.config.core.region import RegionConfig
from entsoe_pipeline.config.core.urls import UrlsConfig
from entsoe_pipeline.config.core.volumes import VolumesConfig
from entsoe_pipeline.logger.core.warning import CustomConfig


@dataclass(frozen=True)
class EntsoeEnvConfig:
    """Immutable configuration for active ENTSO-E deployment platform environment.

    Attributes:
        environment_name (str): Active environment identifier (e.g., 'PROD', 'IOP').
        base_url (str): The entry point URL for the REST or FMS endpoints.
        token_url (str): The Keycloak identity provider token URL.
        token (str | None): Injected access token, if defined.
        email (str | None): Injected email credential, if defined.
        password (str | None): Injected password credential, if defined.
    """

    environment_name: str
    base_url: str
    token_url: str
    token: str | None
    email: str | None
    password: str | None


@dataclass(frozen=True)
class PipelineConfig:
    """Master pipeline configuration representing active runtime properties.

    Attributes:
        active_environment (str): The currently active environment name.
        env_config (EntsoeEnvConfig): Environment API endpoints and credentials.
        limits (RateLimitsConfig): Rate limit constraints.
        buckets (BucketsConfig): S3 storage bucket configuration.
        region (RegionConfig): AWS region configuration.
        ports (PortsConfig): Networking ports configuration.
        hosts (HostsConfig): Networking hosts configuration.
        volumes (VolumesConfig): Storage volumes configuration.
    """

    active_environment: str
    env_config: EntsoeEnvConfig
    limits: RateLimitsConfig
    buckets: BucketsConfig
    region: RegionConfig
    ports: PortsConfig
    hosts: HostsConfig
    volumes: VolumesConfig
    urls: UrlsConfig
    custom: CustomConfig
    lakehouse: LakehouseConfig

    @classmethod
    def _from_yaml(cls) -> PipelineConfig:
        """Loads environment configuration and populates type-safe configs.

        It parses the environment.yml structure, automatically loads local process
        environment variables via python-dotenv (.env), retrieves values mapped to
        credential keys, and builds a verified configuration tree.

        Returns:
            PipelineConfig: The fully parsed and initialized configuration object.

        Raises:
            FileNotFoundError: If environment.yml is missing.
            KeyError: If the active environment configuration cannot be located.
            ValueError: If required structure keys are absent or invalid.
        """
        from entsoe_pipeline.config.paths import (
            API_LIMITS_YML,
            CONFIG_DIR,
            ENV_FILE,
        )

        # Load local .env environment variables into os.environ if present.
        # We explicitly use the SSOT env path for safety.
        env_file = ENV_FILE
        if env_file.exists():
            load_dotenv(dotenv_path=env_file, override=True)
        else:
            load_dotenv(override=True)  # Fallback to standard automatic lookup

        config_path = CONFIG_DIR / "enviroment.yml"
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with config_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        active_env = data.get("active_environment")
        if not active_env:
            raise ValueError("Missing 'active_environment' parameter in configuration.")

        environments = data.get("environments", {})
        if active_env not in environments:
            raise KeyError(
                f"Configured environment '{active_env}' is missing from the "
                f"'environments' mapping registry."
            )

        env_payload = environments[active_env]
        base_url = env_payload.get("base_url")
        token_url = env_payload.get("token_url")
        if not base_url or not token_url:
            raise ValueError(
                f"Active environment '{active_env}' configuration must contain both "
                f"'base_url' and 'token_url'."
            )

        # Retrieve mapped environment secrets from process environment
        credential_keys = env_payload.get("credential_keys", {})

        # Use key names to query active system context
        raw_token_var = credential_keys.get("token")
        raw_email_var = credential_keys.get("email")
        raw_pwd_var = credential_keys.get("password")

        token = os.environ.get(raw_token_var) if raw_token_var else None
        email = os.environ.get(raw_email_var) if raw_email_var else None
        password = os.environ.get(raw_pwd_var) if raw_pwd_var else None

        env_config = EntsoeEnvConfig(
            environment_name=active_env,
            base_url=base_url,
            token_url=token_url,
            token=token,
            email=email,
            password=password,
        )

        # Parse limits from our dedicated SSOT API limits configuration file
        if not API_LIMITS_YML.exists():
            raise FileNotFoundError(
                f"API limits configuration file not found at: {API_LIMITS_YML}"
            )

        with API_LIMITS_YML.open(encoding="utf-8") as f:
            limits_data = yaml.safe_load(f) or {}

        safetimits = limits_data.get("safetimits", {})
        api_overrun = limits_data.get("api_overrun_limits_ban", {})

        limits = RateLimitsConfig(
            standard_api_requests_per_minute=int(
                safetimits.get("api_requests_per_minute", 390)
            ),
            fms_api_requests_per_minute=int(
                safetimits.get("fms_api_requests_per_minute", 95)
            ),
            fms_min_request_interval_seconds=float(
                safetimits.get("fms_min_request_interval_seconds", 0.637)
            ),
            ban_duration_seconds=int(api_overrun.get("duration_seconds", 600)),
        )

        # Load sub-configurations
        buckets = BucketsConfig._from_yaml()
        region = RegionConfig._from_yaml()
        ports = PortsConfig._from_yaml()
        hosts = HostsConfig._from_yaml()
        volumes = VolumesConfig._from_yaml()
        urls = UrlsConfig._from_yaml()
        custom = CustomConfig._from_yaml()
        lakehouse = LakehouseConfig._from_yaml()

        return cls(
            active_environment=active_env,
            env_config=env_config,
            limits=limits,
            buckets=buckets,
            region=region,
            ports=ports,
            hosts=hosts,
            volumes=volumes,
            urls=urls,
            custom=custom,
            lakehouse=lakehouse,
        )
