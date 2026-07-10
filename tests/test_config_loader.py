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

"""Unit and integration tests for the composed config loader.

This module validates the behavior of the PipelineConfig loader, ensuring
proper parsing of configuration files, dynamic environment variable resolution,
fallback defaults, caching behaviors, and exact delegation identity.
All tests are structured under the 3A (Arrange, Act, Assert) pattern.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml

import entsoe_pipeline.config.paths as paths


@pytest.fixture(name="db_env")
def fixture_db_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    db_file = tmp_path / "test_metadata.db"
    url = f"sqlite:///{db_file}"
    monkeypatch.setenv("DATABASE_URL", url)
    return url


from entsoe_pipeline import (
    PortsConfig,
    UrlsConfig,
    get_active_domains_config,
    get_buckets_config,
    get_config,
    get_env_config,
    get_fms_extensions,
    get_hosts_config,
    get_lakehouse_config,
    get_landing_bucket_schema,
    get_limits_config,
    get_ports_config,
    get_region_config,
    get_urls_config,
)


def _create_mock_configs(
    config_dir: Path,
    active_env: str = "IOP",
    ports_data: dict | None = None,
    buckets_data: dict | None = None,
    region_data: dict | None = None,
    hosts_data: dict | None = None,
    urls_data: dict | None = None,
    volumes_data: dict | None = None,
    lakehouse_data: dict | None = None,
) -> None:
    """Helper to populate an isolated config directory with test configurations."""
    # Write environment.yml
    env_file = config_dir / "enviroment.yml"
    mock_env = {
        "active_environment": active_env,
        "environments": {
            "IOP": {
                "base_url": "https://fms.iop-env.entsoe.eu/",
                "token_url": "https://keycloak.iop-env.entsoe.eu/token",
                "credential_keys": {
                    "token": "IOP_API_TOKEN",
                    "email": "IOP_API_EMAIL",
                    "password": "IOP_API_PASSWORD",
                },
            }
        },
        "limits": {
            "standard_api_requests_per_minute": 200,
            "fms_api_requests_per_minute": 50,
            "ban_duration_seconds": 300,
        },
    }
    with env_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump(mock_env, f)

    # Write ports.yml
    ports_file = config_dir / "ports.yml"
    with ports_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump({"ports": ports_data if ports_data is not None else {}}, f)

    # Write bucket.yml
    bucket_file = config_dir / "bucket.yml"
    with bucket_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump({"buckets": buckets_data if buckets_data is not None else {}}, f)

    # Write region.yml
    region_file = config_dir / "region.yml"
    with region_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump({"region": region_data if region_data is not None else {}}, f)

    # Write hosts.yml
    hosts_file = config_dir / "hosts.yml"
    with hosts_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump({"hosts": hosts_data if hosts_data is not None else {}}, f)

    # Write urls.yml
    urls_file = config_dir / "urls.yml"
    with urls_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump({"urls": urls_data if urls_data is not None else {}}, f)

    # Write volumes.yml
    volumes_file = config_dir / "volumes.yml"
    with volumes_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump({"volumes": volumes_data if volumes_data is not None else {}}, f)

    # Write lakehouse.yml
    lakehouse_file = config_dir / "lakehouse.yml"
    with lakehouse_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            {"lakehouse": lakehouse_data if lakehouse_data is not None else {}}, f
        )


@pytest.fixture(autouse=True)
def clear_config_caches() -> Iterator[None]:
    """Fixture to clear configuration caches before and after each test."""
    get_config.cache_clear()
    get_landing_bucket_schema.cache_clear()
    get_active_domains_config.cache_clear()
    yield
    get_config.cache_clear()
    get_landing_bucket_schema.cache_clear()
    get_active_domains_config.cache_clear()


@pytest.fixture(autouse=True)
def mock_api_limits(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Fixture to mock API limits dynamically for all config loader tests."""
    limits_dir = tmp_path / "limits_mock"
    limits_dir.mkdir(parents=True, exist_ok=True)
    limits_file = limits_dir / "entsoe_api_limits.yml"

    mock_limits = {
        "safetimits": {
            "api_requests_per_minute": 200,
            "fms_api_requests_per_minute": 50,
        },
        "api_overrun_limits_ban": {
            "duration_seconds": 300,
            "duration_minutes": 5,
        },
        "limits": {
            "api_requests_per_minute": 400,
            "fms_api_requests_per_minute": 100,
        },
    }

    with limits_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump(mock_limits, f)

    monkeypatch.setattr(paths, "API_LIMITS_YML", limits_file)


# =============================================================================
# 1. UNIT TESTS: PORTS CONFIG CONSTRUCTOR
# =============================================================================


def test_ports_config_creation() -> None:
    """Verify that PortsConfig fields are correctly initialized via constructor."""
    # -------------------------------------------------------------------------
    # ARRANGE: Define target port values
    # -------------------------------------------------------------------------
    s3_port = 9000
    catalog_port = 8000
    m_http = 9333
    m_grpc = 19333
    v_http = 8080
    f_http = 8888
    f_grpc = 18888
    k_web = 8082
    k_api = 8083
    db_port = 5432

    # -------------------------------------------------------------------------
    # ACT: Instantiate PortsConfig directly
    # -------------------------------------------------------------------------
    config = PortsConfig(
        s3_compatible=s3_port,
        iceberg_catalog=catalog_port,
        master_http=m_http,
        master_grpc=m_grpc,
        volume_http=v_http,
        filer_http=f_http,
        filer_grpc=f_grpc,
        kestra_web=k_web,
        kestra_api=k_api,
        database=db_port,
    )

    # -------------------------------------------------------------------------
    # ASSERT: Verify matching field values
    # -------------------------------------------------------------------------
    assert config.s3_compatible == s3_port
    assert config.iceberg_catalog == catalog_port
    assert config.master_http == m_http
    assert config.master_grpc == m_grpc
    assert config.volume_http == v_http
    assert config.filer_http == f_http
    assert config.filer_grpc == f_grpc
    assert config.kestra_web == k_web
    assert config.kestra_api == k_api
    assert config.database == db_port


# =============================================================================
# 2. UNIT TESTS: URLS CONFIG CONSTRUCTOR
# =============================================================================


def test_urls_config_creation() -> None:
    """Verify that UrlsConfig fields are correctly initialized via constructor."""
    # -------------------------------------------------------------------------
    # ARRANGE: Define target URL values
    # -------------------------------------------------------------------------
    k_url = "https://kestra.test.org/"

    # -------------------------------------------------------------------------
    # ACT: Instantiate UrlsConfig directly
    # -------------------------------------------------------------------------
    config = UrlsConfig(kestra=k_url)

    # -------------------------------------------------------------------------
    # ASSERT: Verify matching field values
    # -------------------------------------------------------------------------
    assert config.kestra == k_url


# =============================================================================
# 3. UNIT TESTS: PIPELINE CONFIGURATION LOADER
# =============================================================================


def test_get_config_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verify get_config successfully parses all configuration files."""
    # -------------------------------------------------------------------------
    # ARRANGE: Set up dynamic path overrides, environment files, and credentials
    # -------------------------------------------------------------------------
    temp_config_dir = tmp_path / "config"
    temp_config_dir.mkdir()

    custom_ports = {
        "s3_compatible": 9999,
        "iceberg_catalog": 7777,
        "master_http": 9334,
        "master_grpc": 19334,
        "volume_http": 8081,
        "filer_http": 8889,
        "filer_grpc": 18889,
        "kestra_web": 8084,
        "kestra_api": 8085,
    }
    custom_buckets = {
        "s3_landing_bucket": "custom-raw",
        "s3_lakehouse_bucket": "custom-lake",
    }
    custom_region = {"aws_region": "eu-west-1"}
    custom_hosts = {"seaweedfs": "custom-sw", "iceberg_catalog": "custom-ic"}
    custom_urls = {"kestra": "https://kestra.mock.ru"}

    _create_mock_configs(
        temp_config_dir,
        ports_data=custom_ports,
        buckets_data=custom_buckets,
        region_data=custom_region,
        hosts_data=custom_hosts,
        urls_data=custom_urls,
    )

    monkeypatch.setenv("IOP_API_TOKEN", "mock-token")
    monkeypatch.setenv("IOP_API_EMAIL", "mock-email")
    monkeypatch.setenv("IOP_API_PASSWORD", "mock-pwd")

    monkeypatch.setattr(paths, "CONFIG_DIR", temp_config_dir)

    # Write a mock .env file to verify parsing from the custom path is covered
    env_file = temp_config_dir / ".env"
    env_file.write_text("IOP_API_TOKEN=mock-token", encoding="utf-8")
    monkeypatch.setattr(paths, "ENV_FILE", env_file)

    # -------------------------------------------------------------------------
    # ACT: Retrieve composed PipelineConfig
    # -------------------------------------------------------------------------
    config = get_config()

    # -------------------------------------------------------------------------
    # ASSERT: Verify all properties were successfully parsed and structured
    # -------------------------------------------------------------------------
    assert config.active_environment == "IOP"
    assert config.limits.standard_api_requests_per_minute == 200
    assert config.limits.fms_api_requests_per_minute == 50
    assert config.limits.ban_duration_seconds == 300

    assert config.env_config.token == "mock-token"
    assert config.env_config.email == "mock-email"
    assert config.env_config.password == "mock-pwd"
    assert config.env_config.base_url == "https://fms.iop-env.entsoe.eu/"

    assert config.ports.s3_compatible == 9999
    assert config.ports.iceberg_catalog == 7777
    assert config.ports.master_http == 9334
    assert config.ports.master_grpc == 19334
    assert config.ports.volume_http == 8081
    assert config.ports.filer_http == 8889
    assert config.ports.filer_grpc == 18889
    assert config.ports.kestra_web == 8084
    assert config.ports.kestra_api == 8085
    assert config.buckets.s3_landing_bucket == "custom-raw"
    assert config.buckets.s3_lakehouse_bucket == "custom-lake"
    assert config.region.aws_region == "eu-west-1"
    assert config.hosts.seaweedfs == "custom-sw"
    assert config.hosts.iceberg_catalog == "custom-ic"
    assert config.urls.kestra == "https://kestra.mock.ru"


def test_get_config_caching_and_delegation_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify that get_config is cached and getters return identical references."""
    # -------------------------------------------------------------------------
    # ARRANGE: Set up isolated mocks and override environment variables
    # -------------------------------------------------------------------------
    temp_config_dir = tmp_path / "config"
    temp_config_dir.mkdir()
    _create_mock_configs(temp_config_dir)

    monkeypatch.setattr(paths, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(paths, "ENV_FILE", temp_config_dir / ".env")

    # -------------------------------------------------------------------------
    # ACT: Retrieve master configs and delegate references
    # -------------------------------------------------------------------------
    config_1 = get_config()
    config_2 = get_config()

    buckets_ref = get_buckets_config()
    region_ref = get_region_config()
    ports_ref = get_ports_config()
    hosts_ref = get_hosts_config()
    urls_ref = get_urls_config()
    env_ref = get_env_config()
    limits_ref = get_limits_config()
    lakehouse_ref = get_lakehouse_config()

    # -------------------------------------------------------------------------
    # ASSERT: Verify caching identity and delegation references
    # -------------------------------------------------------------------------
    # Test referential caching identity
    assert config_1 is config_2

    # Test delegation property identity matches exactly
    assert buckets_ref is config_1.buckets
    assert region_ref is config_1.region
    assert ports_ref is config_1.ports
    assert hosts_ref is config_1.hosts
    assert urls_ref is config_1.urls
    assert env_ref is config_1.env_config
    assert limits_ref is config_1.limits
    assert lakehouse_ref is config_1.lakehouse


def test_get_config_sub_configs_fallback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify get_config parses default fallbacks when optional files are empty."""
    # -------------------------------------------------------------------------
    # ARRANGE: Force empty dictionary values to evaluate defaults
    # -------------------------------------------------------------------------
    temp_config_dir = tmp_path / "config"
    temp_config_dir.mkdir()

    _create_mock_configs(
        temp_config_dir,
        ports_data={},
        buckets_data={},
        region_data={},
        hosts_data={},
        urls_data={},
    )

    monkeypatch.setattr(paths, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(paths, "ENV_FILE", temp_config_dir / ".env")

    # -------------------------------------------------------------------------
    # ACT: Load configuration hierarchy
    # -------------------------------------------------------------------------
    config = get_config()

    # -------------------------------------------------------------------------
    # ASSERT: Validate all fallback configurations are active
    # -------------------------------------------------------------------------
    assert config.ports.s3_compatible == 8333
    assert config.ports.iceberg_catalog == 8181
    assert config.ports.master_http == 9333
    assert config.ports.master_grpc == 19333
    assert config.ports.volume_http == 8080
    assert config.ports.filer_http == 8888
    assert config.ports.filer_grpc == 18888
    assert config.ports.kestra_web == 8082
    assert config.ports.kestra_api == 8083
    assert config.buckets.s3_landing_bucket == "landing-zone"
    assert config.buckets.s3_lakehouse_bucket == "lakehouse"
    assert config.region.aws_region == "us-east-1"
    assert config.hosts.seaweedfs == "localhost"
    assert config.hosts.iceberg_catalog == "localhost"
    assert config.urls.kestra == "http://localhost:8082/"


def test_get_config_missing_hosts_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify get_config raises FileNotFoundError if hosts.yml is missing."""
    # -------------------------------------------------------------------------
    # ARRANGE: Write mocks, then delete hosts.yml
    # -------------------------------------------------------------------------
    temp_config_dir = tmp_path / "config"
    temp_config_dir.mkdir()
    _create_mock_configs(temp_config_dir)

    (temp_config_dir / "hosts.yml").unlink()

    monkeypatch.setattr(paths, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(paths, "ENV_FILE", temp_config_dir / ".env")

    # -------------------------------------------------------------------------
    # ACT & ASSERT: Verify FileNotFoundError raises on missing hosts file
    # -------------------------------------------------------------------------
    with pytest.raises(FileNotFoundError):
        get_config()


def test_get_config_missing_urls_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify get_config raises FileNotFoundError if urls.yml is missing."""
    # -------------------------------------------------------------------------
    # ARRANGE: Write mocks, then delete urls.yml
    # -------------------------------------------------------------------------
    temp_config_dir = tmp_path / "config"
    temp_config_dir.mkdir()
    _create_mock_configs(temp_config_dir)

    (temp_config_dir / "urls.yml").unlink()

    monkeypatch.setattr(paths, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(paths, "ENV_FILE", temp_config_dir / ".env")

    # -------------------------------------------------------------------------
    # ACT & ASSERT: Verify FileNotFoundError raises on missing urls file
    # -------------------------------------------------------------------------
    with pytest.raises(FileNotFoundError):
        get_config()


def test_get_config_missing_ports_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify get_config raises FileNotFoundError if ports.yml is missing."""
    # -------------------------------------------------------------------------
    # ARRANGE: Write mocks, then delete ports.yml
    # -------------------------------------------------------------------------
    temp_config_dir = tmp_path / "config"
    temp_config_dir.mkdir()
    _create_mock_configs(temp_config_dir)

    (temp_config_dir / "ports.yml").unlink()

    monkeypatch.setattr(paths, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(paths, "ENV_FILE", temp_config_dir / ".env")

    # -------------------------------------------------------------------------
    # ACT & ASSERT: Verify FileNotFoundError raises on missing ports file
    # -------------------------------------------------------------------------
    with pytest.raises(FileNotFoundError):
        get_config()


def test_get_config_missing_bucket_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify get_config raises FileNotFoundError if bucket.yml is missing."""
    # -------------------------------------------------------------------------
    # ARRANGE: Write mocks, then delete bucket.yml
    # -------------------------------------------------------------------------
    temp_config_dir = tmp_path / "config"
    temp_config_dir.mkdir()
    _create_mock_configs(temp_config_dir)

    (temp_config_dir / "bucket.yml").unlink()

    monkeypatch.setattr(paths, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(paths, "ENV_FILE", temp_config_dir / ".env")

    # -------------------------------------------------------------------------
    # ACT & ASSERT: Verify FileNotFoundError raises on missing bucket file
    # -------------------------------------------------------------------------
    with pytest.raises(FileNotFoundError):
        get_config()


def test_get_config_missing_region_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify get_config raises FileNotFoundError if region.yml is missing."""
    # -------------------------------------------------------------------------
    # ARRANGE: Write mocks, then delete region.yml
    # -------------------------------------------------------------------------
    temp_config_dir = tmp_path / "config"
    temp_config_dir.mkdir()
    _create_mock_configs(temp_config_dir)

    (temp_config_dir / "region.yml").unlink()

    monkeypatch.setattr(paths, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(paths, "ENV_FILE", temp_config_dir / ".env")

    # -------------------------------------------------------------------------
    # ACT & ASSERT: Verify FileNotFoundError raises on missing region file
    # -------------------------------------------------------------------------
    with pytest.raises(FileNotFoundError):
        get_config()


def test_get_config_file_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Verify get_config raises FileNotFoundError if environment.yml does not exist."""
    # -------------------------------------------------------------------------
    # ARRANGE: Establish empty target configuration directory
    # -------------------------------------------------------------------------
    temp_config_dir = tmp_path / "config"
    temp_config_dir.mkdir()

    monkeypatch.setattr(paths, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(paths, "ENV_FILE", temp_config_dir / ".env")

    # -------------------------------------------------------------------------
    # ACT & ASSERT: Verify FileNotFoundError raises on missing master file
    # -------------------------------------------------------------------------
    with pytest.raises(FileNotFoundError):
        get_config()


def test_get_config_missing_active_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify get_config raises ValueError if active_environment key is absent."""
    # -------------------------------------------------------------------------
    # ARRANGE: Write environment.yml with missing active_environment parameter
    # -------------------------------------------------------------------------
    temp_config_dir = tmp_path / "config"
    temp_config_dir.mkdir()

    env_file = temp_config_dir / "enviroment.yml"
    with env_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump({"environments": {"IOP": {}}}, f)

    monkeypatch.setattr(paths, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(paths, "ENV_FILE", temp_config_dir / ".env")

    # -------------------------------------------------------------------------
    # ACT & ASSERT: Verify ValueError is raised with informative message
    # -------------------------------------------------------------------------
    with pytest.raises(ValueError, match="Missing 'active_environment'"):
        get_config()


def test_get_config_missing_active_env_mapping(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify get_config raises KeyError if environment configuration is missing."""
    # -------------------------------------------------------------------------
    # ARRANGE: Map environment target to an unconfigured identifier (PROD)
    # -------------------------------------------------------------------------
    temp_config_dir = tmp_path / "config"
    temp_config_dir.mkdir()

    env_file = temp_config_dir / "enviroment.yml"
    with env_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump({"active_environment": "PROD", "environments": {"IOP": {}}}, f)

    monkeypatch.setattr(paths, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(paths, "ENV_FILE", temp_config_dir / ".env")

    # -------------------------------------------------------------------------
    # ACT & ASSERT: Verify KeyError raises with proper key reference
    # -------------------------------------------------------------------------
    with pytest.raises(KeyError, match="Configured environment 'PROD' is missing"):
        get_config()


def test_get_config_missing_required_urls(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify get_config raises ValueError if base_url or token_url is missing."""
    # -------------------------------------------------------------------------
    # ARRANGE: Create config where key credentials or endpoint URLs are missing
    # -------------------------------------------------------------------------
    temp_config_dir = tmp_path / "config"
    temp_config_dir.mkdir()

    env_file = temp_config_dir / "enviroment.yml"
    mock_invalid_config = {
        "active_environment": "IOP",
        "environments": {
            "IOP": {"token_url": "https://keycloak.iop-env.entsoe.eu/token"}
        },
    }
    with env_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump(mock_invalid_config, f)

    monkeypatch.setattr(paths, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(paths, "ENV_FILE", temp_config_dir / ".env")

    # -------------------------------------------------------------------------
    # ACT & ASSERT: Expect validation error indicating missing url structures
    # -------------------------------------------------------------------------
    with pytest.raises(ValueError, match="must contain both 'base_url'"):
        get_config()


def test_config_facade_integrity() -> None:
    """Verify config_loader facade file contains no direct class definitions."""
    # -------------------------------------------------------------------------
    # ARRANGE: Locate and parse the config_loader facade file using AST
    # -------------------------------------------------------------------------
    import ast

    from entsoe_pipeline.config import config_loader

    facade_path = Path(config_loader.__file__)

    # -------------------------------------------------------------------------
    # ACT: Read and construct AST tree from config_loader.py
    # -------------------------------------------------------------------------
    with facade_path.open(encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=str(facade_path))

    class_defs = [
        node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
    ]

    # -------------------------------------------------------------------------
    # ASSERT: Ensure there are no direct class definitions inside the facade
    # -------------------------------------------------------------------------
    assert not class_defs, (
        f"Facade {facade_path.name} must not contain any direct class definitions. "
        f"Found class definitions: {class_defs}. These must reside in the core package."
    )


def test_get_landing_bucket_schema_success(
    db_env: str,
) -> None:
    """Verify get_landing_bucket_schema returns folder paths correctly."""
    # -------------------------------------------------------------------------
    # ARRANGE
    # -------------------------------------------------------------------------
    from sqlalchemy import create_engine

    from entsoe_pipeline.db import build_metadata, init_db

    init_db()

    engine = create_engine(db_env)
    db_metadata = build_metadata()
    landing_folders_schema = db_metadata.tables["landing_folders_schema"]

    with engine.begin() as conn:
        conn.execute(
            landing_folders_schema.insert(),
            [
                {
                    "s3_folder_path": "iop/TP_export/Load/ActualTotalLoad_6.1.A_r3",
                    "environment": "iop",
                    "domain": "Load",
                    "folder_name": "ActualTotalLoad_6.1.A_r3",
                },
                {
                    "s3_folder_path": "prod/TP_export/Generation/ActualGenerationOutputPerGenerationUnit_16.1.A_r3",
                    "environment": "prod",
                    "domain": "Generation",
                    "folder_name": "ActualGenerationOutputPerGenerationUnit_16.1.A_r3",
                },
            ],
        )

    # -------------------------------------------------------------------------
    # ACT
    # -------------------------------------------------------------------------
    folders = get_landing_bucket_schema()

    # -------------------------------------------------------------------------
    # ASSERT
    # -------------------------------------------------------------------------
    assert folders == [
        "iop/TP_export/Load/ActualTotalLoad_6.1.A_r3",
        "prod/TP_export/Generation/ActualGenerationOutputPerGenerationUnit_16.1.A_r3",
    ]


def test_get_active_domains_config_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify get_active_domains_config returns active domains data correctly."""
    # -------------------------------------------------------------------------
    # ARRANGE
    # -------------------------------------------------------------------------
    mock_domains = {
        "active_mode": "Example",
        "environments": {
            "IOP": {
                "root_directories": [
                    {
                        "name": "TP_export",
                        "domains": {"Load": {"ActualTotalLoad_6.1.A_r3": True}},
                    }
                ]
            }
        },
    }
    domains_file = tmp_path / "my_entsoe_domains.yml"
    with domains_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump(mock_domains, f)

    monkeypatch.setattr(paths, "MY_ENTSOE_DOMAINS_YML", domains_file)

    # -------------------------------------------------------------------------
    # ACT
    # -------------------------------------------------------------------------
    config = get_active_domains_config()

    # -------------------------------------------------------------------------
    # ASSERT
    # -------------------------------------------------------------------------
    assert config == mock_domains


def test_get_fms_extensions_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify get_fms_extensions loads the file formats config correctly."""
    # -------------------------------------------------------------------------
    # ARRANGE
    # -------------------------------------------------------------------------
    mock_data = {
        "allowed_extensions": [".csv", ".zip"],
        "metadata": {
            ".csv": {"description": "CSV"},
            ".zip": {"description": "ZIP"},
        },
    }
    extensions_file = tmp_path / "fms_extensions.yml"
    with extensions_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump(mock_data, f)

    monkeypatch.setattr(paths, "FMS_EXTENSIONS_YML", extensions_file)

    # -------------------------------------------------------------------------
    # ACT
    # -------------------------------------------------------------------------
    extensions = get_fms_extensions()

    # -------------------------------------------------------------------------
    # ASSERT
    # -------------------------------------------------------------------------
    assert extensions == [".csv", ".zip"]
