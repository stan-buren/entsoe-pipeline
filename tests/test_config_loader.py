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

from pathlib import Path

import pytest
import yaml

import entsoe_pipeline.config.config_loader as cl

from entsoe_pipeline import (
    PortsConfig,
    get_buckets_config,
    get_config,
    get_env_config,
    get_limits_config,
    get_ports_config,
    get_region_config,
)


def _create_mock_configs(
    config_dir: Path,
    active_env: str = "IOP",
    ports_data: dict | None = None,
    buckets_data: dict | None = None,
    region_data: dict | None = None,
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


@pytest.fixture(autouse=True)
def clear_config_caches() -> None:
    """Fixture to clear configuration caches before and after each test."""
    get_config.cache_clear()
    yield
    get_config.cache_clear()


def test_ports_config_creation() -> None:
    """Verify that PortsConfig fields are correctly initialized via constructor."""
    # -------------------------------------------------------------------------
    # Arrange: Define target port values
    # -------------------------------------------------------------------------
    s3_port = 9000
    catalog_port = 8000

    # -------------------------------------------------------------------------
    # Act: Instantiate PortsConfig directly
    # -------------------------------------------------------------------------
    config = PortsConfig(s3_compatible=s3_port, iceberg_catalog=catalog_port)

    # -------------------------------------------------------------------------
    # Assert: Verify matching field values
    # -------------------------------------------------------------------------
    assert config.s3_compatible == s3_port
    assert config.iceberg_catalog == catalog_port


def test_get_config_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verify get_config successfully parses all configuration files."""
    # -------------------------------------------------------------------------
    # Arrange: Set up dynamic path overrides, environment files, and credentials
    # -------------------------------------------------------------------------
    temp_config_dir = tmp_path / "config"
    temp_config_dir.mkdir()

    custom_ports = {"s3_compatible": 9999, "iceberg_catalog": 7777}
    custom_buckets = {"s3_bucket": "custom-raw", "s3_table_bucket": "custom-lake"}
    custom_region = {"aws_region": "eu-west-1"}

    _create_mock_configs(
        temp_config_dir,
        ports_data=custom_ports,
        buckets_data=custom_buckets,
        region_data=custom_region,
    )

    monkeypatch.setenv("IOP_API_TOKEN", "mock-token")
    monkeypatch.setenv("IOP_API_EMAIL", "mock-email")
    monkeypatch.setenv("IOP_API_PASSWORD", "mock-pwd")

    monkeypatch.setattr(cl, "CONFIG_DIR", temp_config_dir)

    # Write a mock .env file to verify parsing from the custom path is covered
    env_file = temp_config_dir / ".env"
    env_file.write_text("IOP_API_TOKEN=mock-token", encoding="utf-8")
    monkeypatch.setattr(cl, "ENV_FILE", env_file)

    # -------------------------------------------------------------------------
    # Act: Retrieve composed PipelineConfig
    # -------------------------------------------------------------------------
    config = get_config()

    # -------------------------------------------------------------------------
    # Assert: Verify all properties were successfully parsed and structured
    # -------------------------------------------------------------------------
    assert config.active_environment == "IOP"
    assert config.limits.standard_api_requests_per_minute == 200
    assert config.limits.fms_api_requests_per_minute == 50
    assert config.limits.ban_duration_seconds == 300

    assert config.env_config.token == "mock-token"  # noqa: S105
    assert config.env_config.email == "mock-email"
    assert config.env_config.password == "mock-pwd"  # noqa: S105
    assert config.env_config.base_url == "https://fms.iop-env.entsoe.eu/"

    assert config.ports.s3_compatible == 9999
    assert config.ports.iceberg_catalog == 7777
    assert config.buckets.s3_bucket == "custom-raw"
    assert config.buckets.s3_table_bucket == "custom-lake"
    assert config.region.aws_region == "eu-west-1"


def test_get_config_caching_and_delegation_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify that get_config is cached and getters return identical references."""
    # -------------------------------------------------------------------------
    # Arrange: Set up isolated mocks and override environment variables
    # -------------------------------------------------------------------------
    temp_config_dir = tmp_path / "config"
    temp_config_dir.mkdir()
    _create_mock_configs(temp_config_dir)

    monkeypatch.setattr(cl, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(cl, "ENV_FILE", temp_config_dir / ".env")

    # -------------------------------------------------------------------------
    # Act: Retrieve master configs and delegate references
    # -------------------------------------------------------------------------
    config_1 = get_config()
    config_2 = get_config()

    buckets_ref = get_buckets_config()
    region_ref = get_region_config()
    ports_ref = get_ports_config()
    env_ref = get_env_config()
    limits_ref = get_limits_config()

    # -------------------------------------------------------------------------
    # Assert: Verify caching identity and delegation references
    # -------------------------------------------------------------------------
    # Test referential caching identity
    assert config_1 is config_2

    # Test delegation property identity matches exactly
    assert buckets_ref is config_1.buckets
    assert region_ref is config_1.region
    assert ports_ref is config_1.ports
    assert env_ref is config_1.env_config
    assert limits_ref is config_1.limits


def test_get_config_sub_configs_fallback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify get_config parses default fallbacks when optional files are empty."""
    # -------------------------------------------------------------------------
    # Arrange: Force empty dictionary values to evaluate defaults
    # -------------------------------------------------------------------------
    temp_config_dir = tmp_path / "config"
    temp_config_dir.mkdir()

    _create_mock_configs(
        temp_config_dir,
        ports_data={},
        buckets_data={},
        region_data={},
    )

    monkeypatch.setattr(cl, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(cl, "ENV_FILE", temp_config_dir / ".env")

    # -------------------------------------------------------------------------
    # Act: Load configuration hierarchy
    # -------------------------------------------------------------------------
    config = get_config()

    # -------------------------------------------------------------------------
    # Assert: Validate all fallback configurations are active
    # -------------------------------------------------------------------------
    assert config.ports.s3_compatible == 8333
    assert config.ports.iceberg_catalog == 8181
    assert config.buckets.s3_bucket == "raw-zone"
    assert config.buckets.s3_table_bucket == "lakehouse"
    assert config.region.aws_region == "us-east-1"


def test_get_config_missing_ports_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify get_config raises FileNotFoundError if ports.yml is missing."""
    # -------------------------------------------------------------------------
    # Arrange: Write mocks, then delete ports.yml
    # -------------------------------------------------------------------------
    temp_config_dir = tmp_path / "config"
    temp_config_dir.mkdir()
    _create_mock_configs(temp_config_dir)

    (temp_config_dir / "ports.yml").unlink()

    monkeypatch.setattr(cl, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(cl, "ENV_FILE", temp_config_dir / ".env")

    # -------------------------------------------------------------------------
    # Act & Assert: Verify FileNotFoundError raises on missing ports file
    # -------------------------------------------------------------------------
    with pytest.raises(FileNotFoundError):
        get_config()


def test_get_config_missing_bucket_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify get_config raises FileNotFoundError if bucket.yml is missing."""
    # -------------------------------------------------------------------------
    # Arrange: Write mocks, then delete bucket.yml
    # -------------------------------------------------------------------------
    temp_config_dir = tmp_path / "config"
    temp_config_dir.mkdir()
    _create_mock_configs(temp_config_dir)

    (temp_config_dir / "bucket.yml").unlink()

    monkeypatch.setattr(cl, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(cl, "ENV_FILE", temp_config_dir / ".env")

    # -------------------------------------------------------------------------
    # Act & Assert: Verify FileNotFoundError raises on missing bucket file
    # -------------------------------------------------------------------------
    with pytest.raises(FileNotFoundError):
        get_config()


def test_get_config_missing_region_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify get_config raises FileNotFoundError if region.yml is missing."""
    # -------------------------------------------------------------------------
    # Arrange: Write mocks, then delete region.yml
    # -------------------------------------------------------------------------
    temp_config_dir = tmp_path / "config"
    temp_config_dir.mkdir()
    _create_mock_configs(temp_config_dir)

    (temp_config_dir / "region.yml").unlink()

    monkeypatch.setattr(cl, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(cl, "ENV_FILE", temp_config_dir / ".env")

    # -------------------------------------------------------------------------
    # Act & Assert: Verify FileNotFoundError raises on missing region file
    # -------------------------------------------------------------------------
    with pytest.raises(FileNotFoundError):
        get_config()


def test_get_config_file_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Verify get_config raises FileNotFoundError if environment.yml does not exist."""
    # -------------------------------------------------------------------------
    # Arrange: Establish empty target configuration directory
    # -------------------------------------------------------------------------
    temp_config_dir = tmp_path / "config"
    temp_config_dir.mkdir()

    monkeypatch.setattr(cl, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(cl, "ENV_FILE", temp_config_dir / ".env")

    # -------------------------------------------------------------------------
    # Act & Assert: Verify FileNotFoundError raises on missing master file
    # -------------------------------------------------------------------------
    with pytest.raises(FileNotFoundError):
        get_config()


def test_get_config_missing_active_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify get_config raises ValueError if active_environment key is absent."""
    # -------------------------------------------------------------------------
    # Arrange: Write environment.yml with missing active_environment parameter
    # -------------------------------------------------------------------------
    temp_config_dir = tmp_path / "config"
    temp_config_dir.mkdir()

    env_file = temp_config_dir / "enviroment.yml"
    with env_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump({"environments": {"IOP": {}}}, f)

    monkeypatch.setattr(cl, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(cl, "ENV_FILE", temp_config_dir / ".env")

    # -------------------------------------------------------------------------
    # Act & Assert: Verify ValueError is raised with informative message
    # -------------------------------------------------------------------------
    with pytest.raises(ValueError, match="Missing 'active_environment'"):
        get_config()


def test_get_config_missing_active_env_mapping(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify get_config raises KeyError if environment configuration is missing."""
    # -------------------------------------------------------------------------
    # Arrange: Map environment target to an unconfigured identifier (PROD)
    # -------------------------------------------------------------------------
    temp_config_dir = tmp_path / "config"
    temp_config_dir.mkdir()

    env_file = temp_config_dir / "enviroment.yml"
    with env_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump({"active_environment": "PROD", "environments": {"IOP": {}}}, f)

    monkeypatch.setattr(cl, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(cl, "ENV_FILE", temp_config_dir / ".env")

    # -------------------------------------------------------------------------
    # Act & Assert: Verify KeyError raises with proper key reference
    # -------------------------------------------------------------------------
    with pytest.raises(KeyError, match="Configured environment 'PROD' is missing"):
        get_config()


def test_get_config_missing_required_urls(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify get_config raises ValueError if base_url or token_url is missing."""
    # -------------------------------------------------------------------------
    # Arrange: Create config where key credentials or endpoint URLs are missing
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

    monkeypatch.setattr(cl, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(cl, "ENV_FILE", temp_config_dir / ".env")

    # -------------------------------------------------------------------------
    # Act & Assert: Expect validation error indicating missing url structures
    # -------------------------------------------------------------------------
    with pytest.raises(ValueError, match="must contain both 'base_url'"):
        get_config()
