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

"""Configuration loader module for the ENTSO-E data pipeline.

This module provides type-safe, immutable configuration objects by parsing
infrastructure YAML files and loading environment parameters from environment variables.
"""

from __future__ import annotations

import os

from dataclasses import dataclass
from functools import cache
from pathlib import Path

import yaml

from dotenv import load_dotenv


def load_paths_config(project_root: Path) -> dict[str, str]:
    """Loads and parses the centralized paths configuration from paths.yml.

    Args:
        project_root: The project root directory.

    Returns:
        dict[str, str]: Mapped relative path configurations.
    """
    paths_file = project_root / "config" / "paths.yml"
    if not paths_file.exists():
        raise FileNotFoundError(f"Paths configuration file not found at: {paths_file}")
    with paths_file.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# =============================================================================
# ENVIRONMENT & RUNTIME CONFIGURATIONS (Master Config and Helpers)
# =============================================================================


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
class RateLimitsConfig:
    """Immutable rate limit configurations for ENTSO-E API interactions.

    Attributes:
        standard_api_requests_per_minute (int): Max XML/REST API calls in a rolling 60s.
        fms_api_requests_per_minute (int): Max FMS API actions in a rolling 60s.
        ban_duration_seconds (int): Penalty freeze timeout on limit violation.
    """

    standard_api_requests_per_minute: int
    fms_api_requests_per_minute: int
    ban_duration_seconds: int


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
    """

    active_environment: str
    env_config: EntsoeEnvConfig
    limits: RateLimitsConfig
    buckets: BucketsConfig
    region: RegionConfig
    ports: PortsConfig

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
        from entsoe_pipeline.config.paths import (  # noqa: PLC0415
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
            ban_duration_seconds=int(api_overrun.get("duration_seconds", 600)),
        )

        # Load sub-configurations
        buckets = BucketsConfig._from_yaml()
        region = RegionConfig._from_yaml()
        ports = PortsConfig._from_yaml()

        return cls(
            active_environment=active_env,
            env_config=env_config,
            limits=limits,
            buckets=buckets,
            region=region,
            ports=ports,
        )


# =============================================================================
# INFRASTRUCTURE CONFIGURATIONS (Storage, AWS Region, and Network Ports)
# =============================================================================


@dataclass(frozen=True)
class BucketsConfig:
    """Immutable S3 storage bucket configuration.

    Attributes:
        s3_bucket (str): The name of the S3 bucket for raw data storage.
        s3_table_bucket (str): The name of the S3 bucket for Iceberg warehouse tables.
    """

    s3_bucket: str
    s3_table_bucket: str

    @classmethod
    def _from_yaml(cls) -> BucketsConfig:
        """Loads and parses the buckets configuration from bucket.yml.

        Returns:
            BucketsConfig: The loaded buckets configuration.
        """
        from entsoe_pipeline.config.paths import CONFIG_DIR  # noqa: PLC0415

        bucket_file = CONFIG_DIR / "bucket.yml"

        with bucket_file.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        bucket_data = data.get("buckets", {})

        return cls(
            s3_bucket=str(bucket_data.get("s3_bucket", "raw-zone")),
            s3_table_bucket=str(bucket_data.get("s3_table_bucket", "lakehouse")),
        )


@dataclass(frozen=True)
class RegionConfig:
    """Immutable AWS region configuration.

    Attributes:
        aws_region (str): The target AWS region name (e.g., 'us-east-1').
    """

    aws_region: str

    @classmethod
    def _from_yaml(cls) -> RegionConfig:
        """Loads and parses the AWS region configuration from region.yml.

        Returns:
            RegionConfig: The loaded AWS region configuration.
        """
        from entsoe_pipeline.config.paths import CONFIG_DIR  # noqa: PLC0415

        region_file = CONFIG_DIR / "region.yml"

        with region_file.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        region_data = data.get("region", {})

        return cls(
            aws_region=str(region_data.get("aws_region", "us-east-1")),
        )


@dataclass(frozen=True)
class PortsConfig:
    """Immutable infrastructure ports configuration.

    Attributes:
        s3_compatible (int): Port for S3-compatible API.
        iceberg_catalog (int): Port for Apache Iceberg REST Catalog.
    """

    s3_compatible: int
    iceberg_catalog: int

    @classmethod
    def _from_yaml(cls) -> PortsConfig:
        """Loads and parses the ports configuration from ports.yml.

        Returns:
            PortsConfig: A type-safe configuration object.

        Raises:
            FileNotFoundError: If ports.yml is missing.
            yaml.YAMLError: If ports.yml contains invalid syntax.
        """
        from entsoe_pipeline.config.paths import CONFIG_DIR  # noqa: PLC0415

        ports_file = CONFIG_DIR / "ports.yml"

        with ports_file.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        ports_data = data.get("ports", {})

        return cls(
            s3_compatible=int(ports_data.get("s3_compatible", 8333)),
            iceberg_catalog=int(ports_data.get("iceberg_catalog", 8181)),
        )


# =============================================================================
# ENTSO-E FMS DATA DOMAINS CLASSIFIER CONFIGURATION
# =============================================================================


@dataclass(frozen=True)
class ExclusionRule:
    """Immutable sub-rule to dynamically redirect folder domains on contextual overlaps.

    Attributes:
        patterns (list[str]): Key phrases in lowercase that trigger redirect.
        redirect_to (str): Target domain to redirect, if matched.
    """

    patterns: list[str]
    redirect_to: str


@dataclass(frozen=True)
class ClassificationRule:
    """Immutable classification rule mapping key patterns to analytical domains.

    Attributes:
        domain (str): Target data domain (e.g., 'Load', 'Transmission').
        patterns (list[str]): Lowercase keywords to inspect in folder name.
        exclusions (list[ExclusionRule]): Exclusions redirecting domain context.
    """

    domain: str
    patterns: list[str]
    exclusions: list[ExclusionRule]


@dataclass(frozen=True)
class LegacyRule:
    """Immutable classification rule mapping legacy archive specifications.

    Attributes:
        archive (str): Target archive identifier (e.g. 'R3_Archives').
        release_name (str): Official name of the release.
        decommission_status (str): Current status and decommission date description.
        description (str): Business context and information about the release.
        patterns (list[str]): Key phrases in folder name to map to this archive.
    """

    archive: str
    release_name: str
    decommission_status: str
    description: str
    patterns: list[str]


@dataclass(frozen=True)
class ClassifierConfig:
    """Master configuration class representing folder classification rules mapping.

    Attributes:
        domain_order (list[str]): Standardized order list of the data domains.
        fallback_domain (str): Fallback domain identifier on no patterns matched.
        rules (list[ClassificationRule]): Pattern matching and exclusion rules sequence.
        legacy_rules (list[LegacyRule]): Rules defining decommissioned legacy
            publications.
    """

    domain_order: list[str]
    fallback_domain: str
    rules: list[ClassificationRule]
    legacy_rules: list[LegacyRule]

    @classmethod
    def _from_yaml(cls) -> ClassifierConfig:
        """Loads and parses the classifier configuration from entsoe-classifier.yml.

        Returns:
            ClassifierConfig: The loaded classifier configuration.

        Raises:
            FileNotFoundError: If the entsoe-classifier.yml is not present.
        """
        from entsoe_pipeline.config.paths import CLASSIFIER_YML  # noqa: PLC0415

        config_file = CLASSIFIER_YML
        if not config_file.exists():
            raise FileNotFoundError(
                f"Classifier configuration file not found at: {config_file}"
            )

        with config_file.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        domain_order = list(data.get("domain_order", []))
        fallback_domain = str(data.get("fallback_domain", "OtherMarketInformation"))
        raw_rules = data.get("rules", [])

        rules = []
        for r in raw_rules:
            domain = str(r.get("domain", ""))
            patterns = [str(pat) for pat in r.get("patterns", [])]
            raw_exclusions = r.get("exclusions", [])

            exclusions = []
            for exc in raw_exclusions:
                exc_patterns = [str(pat) for pat in exc.get("patterns", [])]
                redirect_to = str(exc.get("redirect_to", ""))
                if redirect_to:
                    exclusions.append(
                        ExclusionRule(patterns=exc_patterns, redirect_to=redirect_to)
                    )

            if domain:
                rules.append(
                    ClassificationRule(
                        domain=domain,
                        patterns=patterns,
                        exclusions=exclusions,
                    )
                )

        raw_legacy_rules = data.get("legacy_rules", [])
        legacy_rules = []
        for lr in raw_legacy_rules:
            archive = str(lr.get("archive", ""))
            release_name = str(lr.get("release_name", ""))
            decommission_status = str(lr.get("decommission_status", ""))
            description = str(lr.get("description", ""))
            patterns = [str(pat) for pat in lr.get("patterns", [])]

            if archive:
                legacy_rules.append(
                    LegacyRule(
                        archive=archive,
                        release_name=release_name,
                        decommission_status=decommission_status,
                        description=description,
                        patterns=patterns,
                    )
                )

        return cls(
            domain_order=domain_order,
            fallback_domain=fallback_domain,
            rules=rules,
            legacy_rules=legacy_rules,
        )


# =============================================================================
# PUBLIC INTERFACE (Cached Singleton Accessors)
# =============================================================================


@cache
def get_config() -> PipelineConfig:
    """Loads and returns the cached PipelineConfig singleton.

    For example:
        config = get_config()
        active_env = config.active_environment
        username = config.env_config.email
        password = config.env_config.password
        raw_bucket = config.buckets.s3_bucket

    Returns:
        PipelineConfig: The loaded pipeline configuration, containing:
            - active_environment (str): Name of active environment (e.g. 'PROD').
            - env_config (EntsoeEnvConfig): Environment credentials and settings:
                - environment_name (str): Active environment identifier.
                - base_url (str): REST or FMS API entry point URL.
                - token_url (str): Keycloak token acquisition URL.
                - token (Optional[str]): Active API token if injected.
                - email (Optional[str]): Authenticating account email.
                - password (Optional[str]): Authenticating account password.
            - limits (RateLimitsConfig): Configured rate limits:
                - standard_api_requests_per_minute (int): Standard API call limit.
                - fms_api_requests_per_minute (int): FMS payload API call limit.
                - ban_duration_seconds (int): Penalty cooldown time on limit violations.
            - buckets (BucketsConfig): S3 storage bucket configuration:
                - s3_bucket (str): Bucket for raw target storage.
                - s3_table_bucket (str): Bucket for Iceberg warehouse tables.
            - region (RegionConfig): AWS region configuration:
                - aws_region (str): Mapped AWS region identifier (e.g., 'us-east-1').
            - ports (PortsConfig): Infrastructure ports configuration:
                - s3_compatible (int): TCP port for S3-compatible storage API.
                - iceberg_catalog (int): TCP port for the Apache Iceberg REST Catalog.
    """
    return PipelineConfig._from_yaml()


def get_buckets_config() -> BucketsConfig:
    """Loads and returns the cached BucketsConfig singleton.

    For example:
        buckets = get_buckets_config()
        raw_bucket = buckets.s3_bucket

    Returns:
        BucketsConfig: The active S3 storage buckets configuration, containing:
            - s3_bucket (str): Bucket for raw target storage.
            - s3_table_bucket (str): Bucket for Iceberg warehouse tables.
    """
    return get_config().buckets


def get_region_config() -> RegionConfig:
    """Loads and returns the cached RegionConfig singleton.

    For example:
        region = get_region_config()
        aws_region = region.aws_region

    Returns:
        RegionConfig: The loaded AWS region configuration, containing:
            - aws_region (str): Mapped AWS region identifier (e.g., 'us-east-1').
    """
    return get_config().region


def get_ports_config() -> PortsConfig:
    """Loads and returns the cached PortsConfig singleton.

    For example:
        ports = get_ports_config()
        s3_port = ports.s3_compatible

    Returns:
        PortsConfig: The active infrastructure networking ports config, containing:
            - s3_compatible (int): TCP port for S3-compatible storage API.
            - iceberg_catalog (int): TCP port for the Apache Iceberg REST Catalog.
    """
    return get_config().ports


def get_env_config() -> EntsoeEnvConfig:
    """Loads and returns the cached EntsoeEnvConfig singleton.

    For example:
        env = get_env_config()
        username = env.email
        password = env.password

    Returns:
        EntsoeEnvConfig: The active environment credentials and settings, containing:
            - environment_name (str): Active environment identifier.
            - base_url (str): REST or FMS API entry point URL.
            - token_url (str): Keycloak token acquisition URL.
            - token (Optional[str]): Active API token if injected.
            - email (Optional[str]): Authenticating account email.
            - password (Optional[str]): Authenticating account password.
    """
    return get_config().env_config


def get_limits_config() -> RateLimitsConfig:
    """Loads and returns the cached RateLimitsConfig singleton.

    For example:
        limits = get_limits_config()
        requests_limit = limits.standard_api_requests_per_minute

    Returns:
        RateLimitsConfig: The active pipeline API rate limit configurations, containing:
            - standard_api_requests_per_minute (int): Standard API call limit.
            - fms_api_requests_per_minute (int): FMS payload API call limit.
            - ban_duration_seconds (int): Penalty cooldown time on limit violations.
    """
    return get_config().limits


@cache
def get_classifier_config() -> ClassifierConfig:
    """Loads and returns the cached ClassifierConfig singleton.

    Returns:
        ClassifierConfig: The loaded classifier configuration, containing:
            - domain_order (list[str]): Categorization domains array.
            - fallback_domain (str): Default fallback classification bucket.
            - rules (list[ClassificationRule]): Crawl rules and exclusions:
                - domain (str): Target domain to evaluate.
                - patterns (list[str]): Match keywords list.
                - exclusions (list[ExclusionRule]): Conflict redirects checklist.
    """
    return ClassifierConfig._from_yaml()


@cache
def get_paths_config() -> dict[str, str]:
    """Loads and returns the cached paths configuration mapping relative path strings.

    Returns:
        dict[str, str]: Mapped relative path configurations from paths.yml.
    """
    from entsoe_pipeline.config.paths import PROJECT_ROOT  # noqa: PLC0415

    return load_paths_config(PROJECT_ROOT)
