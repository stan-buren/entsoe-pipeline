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

"""Configuration loader facade module for the ENTSO-E data pipeline.

This module acts as a clean public facade, importing and exporting all
type-safe, immutable configuration classes from the core package, and
providing cached singleton accessors.
"""

from __future__ import annotations

from functools import cache
from typing import Any

import yaml

from entsoe_pipeline.config.core import (
    BucketsConfig,
    ClassifierConfig,
    CustomConfig,
    EntsoeEnvConfig,
    EntsoeFmsSchemasConfig,
    FmsColumnSchema,  # noqa: F401 — re-exported via __init__.py
    FmsPublicationSchema,  # noqa: F401 — re-exported via __init__.py
    HostsConfig,
    LakehouseConfig,
    LakehouseParquetCodecConfig,
    PipelineConfig,
    PortsConfig,
    RateLimitsConfig,
    RegionConfig,
    UrlsConfig,
    VolumesConfig,
)
from entsoe_pipeline.config.paths import PROJECT_ROOT, load_paths_config


@cache
def get_config() -> PipelineConfig:
    """Loads and returns the cached PipelineConfig singleton.

    For example:
        config = get_config()
        active_env = config.active_environment
        username = config.env_config.email
        password = config.env_config.password
        raw_bucket = config.buckets.s3_landing_bucket

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
                - s3_landing_bucket (str): Bucket for landing raw files.
                - s3_lakehouse_bucket (str): Bucket for Iceberg warehouse tables.
            - region (RegionConfig): AWS region configuration:
                - aws_region (str): Mapped AWS region identifier (e.g., 'us-east-1').
            - ports (PortsConfig): Infrastructure ports configuration:
                - s3_compatible (int): TCP port for S3-compatible storage API.
                - iceberg_catalog (int): TCP port for the Apache Iceberg REST Catalog.
                - master_http (int): TCP port for the SeaweedFS Master HTTP Admin UI.
                - master_grpc (int): TCP port for the SeaweedFS Master gRPC.
                - volume_http (int): TCP port for the SeaweedFS Volume Server HTTP API.
                - filer_http (int): TCP port for the SeaweedFS Filer HTTP interface.
                - filer_grpc (int): TCP port for the SeaweedFS Filer gRPC service.
                - kestra_web (int): TCP port for the Kestra Web UI administration dashboard.
                - kestra_api (int): TCP port for the Kestra API backend services.
            - hosts (HostsConfig): Infrastructure hosts configuration:
                - seaweedfs (str): IP address or domain name of the SeaweedFS server.
                - iceberg_catalog (str): IP address or domain name of the Iceberg REST Catalog.
            - volumes (VolumesConfig): Storage volumes configuration:
                - s3_compatible (str): Physical directory path on the host for local storage.
            - urls (UrlsConfig): Infrastructure URLs configuration:
                - kestra (str): The external/public web URL of the Kestra platform.
    """
    return PipelineConfig._from_yaml()


def get_buckets_config() -> BucketsConfig:
    """Loads and returns the cached BucketsConfig singleton.

    For example:
        buckets = get_buckets_config()
        raw_bucket = buckets.s3_landing_bucket

    Returns:
        BucketsConfig: The active S3 storage buckets configuration, containing:
            - s3_landing_bucket (str): Bucket for landing raw files.
            - s3_lakehouse_bucket (str): Bucket for Iceberg warehouse tables.
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
            - master_http (int): TCP port for the SeaweedFS Master HTTP Admin UI.
            - master_grpc (int): TCP port for the SeaweedFS Master gRPC.
            - volume_http (int): TCP port for the SeaweedFS Volume Server HTTP API.
            - filer_http (int): TCP port for the SeaweedFS Filer HTTP interface.
            - filer_grpc (int): TCP port for the SeaweedFS Filer gRPC service.
            - kestra_web (int): TCP port for the Kestra Web UI administration dashboard.
            - kestra_api (int): TCP port for the Kestra API backend services.
    """
    return get_config().ports


def get_volumes_config() -> VolumesConfig:
    """Loads and returns the cached VolumesConfig singleton.

    For example:
        volumes = get_volumes_config()
        s3_volume = volumes.s3_compatible

    Returns:
        VolumesConfig: The active infrastructure storage volumes config, containing:
            - s3_compatible (str): Physical directory path on the host for local storage.
    """
    return get_config().volumes


def get_urls_config() -> UrlsConfig:
    """Loads and returns the cached UrlsConfig singleton.

    For example:
        urls = get_urls_config()
        kestra_url = urls.kestra

    Returns:
        UrlsConfig: The active infrastructure URLs config, containing:
            - kestra (str): The external/public web URL of the Kestra platform.
    """
    return get_config().urls


def get_hosts_config() -> HostsConfig:
    """Loads and returns the cached HostsConfig singleton.

    For example:
        hosts = get_hosts_config()
        storage_host = hosts.seaweedfs

    Returns:
        HostsConfig: The active infrastructure networking hosts config, containing:
            - seaweedfs (str): IP address or domain name of the SeaweedFS server.
            - iceberg_catalog (str): IP address or domain name of the Apache Iceberg REST Catalog.
    """
    return get_config().hosts


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
            - domains (dict[str, dict[str, ClassifierItem]]): Map of domains and items.
            - legacy_rules (list[LegacyRule]): Rules defining legacy archives.
    """
    return ClassifierConfig._from_yaml()


@cache
def get_paths_config() -> dict[str, str]:
    """Loads and returns the cached paths configuration mapping relative path strings.

    Returns:
        dict[str, str]: Mapped relative path configurations from paths.yml.
    """
    return load_paths_config(PROJECT_ROOT)


def get_custom_config() -> CustomConfig:
    """Loads and returns the cached CustomConfig singleton.

    Returns:
        CustomConfig: The active custom active mode configuration.
    """
    return get_config().custom


def get_lakehouse_config() -> LakehouseConfig:
    """Loads and returns the cached LakehouseConfig singleton.

    Returns:
        LakehouseConfig: The active Lakehouse configuration.
    """
    return get_config().lakehouse


@cache
def get_landing_bucket_schema() -> list[str]:
    """Loads and returns the list of folder paths from the landing_folders_schema database table.

    Returns:
        list[str]: Registered landing bucket directory paths.
    """
    from sqlalchemy import create_engine, select

    from entsoe_pipeline.db import build_metadata, get_db_url

    engine = create_engine(get_db_url())
    db_metadata = build_metadata()
    landing_folders_schema = db_metadata.tables["landing_folders_schema"]

    with engine.connect() as conn:
        stmt = select(landing_folders_schema.c.s3_folder_path)
        rows = conn.execute(stmt).fetchall()
    return [row[0] for row in rows]


@cache
def get_active_domains_config() -> dict[str, Any]:
    """Loads and returns the active domains raw configuration registry.

    Returns:
        dict[str, Any]: Cached dictionary mapping of domains configuration.
    """
    from entsoe_pipeline.config.paths import MY_ENTSOE_DOMAINS_YML

    if not MY_ENTSOE_DOMAINS_YML.exists():
        raise FileNotFoundError(
            f"Active domains configuration registry not found at: {MY_ENTSOE_DOMAINS_YML}. "
            "Please generate the domains checklist first."
        )

    with MY_ENTSOE_DOMAINS_YML.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@cache
def get_fms_extensions() -> list[str]:
    """Loads and returns the cached list of supported FMS file extensions.

    Returns:
        list[str]: Supported FMS file extensions.
    """
    from entsoe_pipeline.config.paths import FMS_EXTENSIONS_YML

    if not FMS_EXTENSIONS_YML.exists():
        raise FileNotFoundError(
            f"FMS file extensions configuration not found at: {FMS_EXTENSIONS_YML}"
        )

    with FMS_EXTENSIONS_YML.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return [str(ext) for ext in data.get("allowed_extensions", [])]


@cache
def get_db_schema_config() -> dict[str, Any]:
    """Loads and returns the database schema configuration from DB_SCHEMA_YML.

    Returns:
        dict[str, Any]: Database schema configuration.
    """
    from entsoe_pipeline.config.paths import DB_SCHEMA_YML

    if not DB_SCHEMA_YML.exists():
        raise FileNotFoundError(
            f"Database schema configuration not found at: {DB_SCHEMA_YML}"
        )

    with DB_SCHEMA_YML.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@cache
def get_crawler_config() -> dict[str, Any]:
    """Loads and returns the FMS crawler strategy configuration from FMS_CRAWLER_YML.

    Returns:
        dict[str, Any]: Crawler configuration including freshness thresholds.
    """
    from entsoe_pipeline.config.paths import FMS_CRAWLER_YML

    if not FMS_CRAWLER_YML.exists():
        raise FileNotFoundError(
            f"FMS crawler configuration not found at: {FMS_CRAWLER_YML}"
        )

    with FMS_CRAWLER_YML.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@cache
def get_fms_schemas_config() -> EntsoeFmsSchemasConfig:
    """Loads and returns the cached EntsoeFmsSchemasConfig singleton.

    Returns:
        EntsoeFmsSchemasConfig: Configured schema specifications.
    """
    return EntsoeFmsSchemasConfig._from_yaml()


@cache
def get_lakehouse_parquet_codec_config() -> LakehouseParquetCodecConfig:
    """Loads and returns the cached LakehouseParquetCodecConfig singleton.

    Returns:
        LakehouseParquetCodecConfig: The Parquet writes and compaction settings.
    """
    return LakehouseParquetCodecConfig._from_yaml()
