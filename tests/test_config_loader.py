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

"""Unit and integration tests for the PortsConfig loader class.

This module validates the behavior of the PortsConfig dataclass, ensuring
proper parsing of ports.yml files, graceful handling of empty or missing configurations,
and robust default fallback port settings.
"""

from pathlib import Path

import pytest
import yaml

import entsoe_pipeline.config.config_loader as cl

from entsoe_pipeline import PortsConfig


def test_ports_config_creation() -> None:
    """Verify that PortsConfig fields are correctly initialized via constructor.

    This checks that the underlying dataclass properly stores the S3 compatible
    storage gateway and Apache Iceberg catalog port numbers as immutable fields,
    preventing runtime typing errors when building the Spark session configuration.
    """
    # -------------------------------------------------------------------------
    # GIVEN: Target port configurations for local infrastructure components
    # -------------------------------------------------------------------------
    s3_port = 9000
    catalog_port = 8000

    # -------------------------------------------------------------------------
    # WHEN: We instantiate the PortsConfig class directly
    # -------------------------------------------------------------------------
    config = PortsConfig(s3_compatible=s3_port, iceberg_catalog=catalog_port)

    # -------------------------------------------------------------------------
    # THEN: Verify that the fields exactly match the constructor values
    # -------------------------------------------------------------------------
    assert config.s3_compatible == s3_port
    assert config.iceberg_catalog == catalog_port


def test_ports_config_from_yaml_fallback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify from_yaml loads default fallback ports if the keys are empty.

    This ensures that when a developer initializes an empty configuration file,
    the pipeline safely falls back to standard local ports (8333 and 8181)
    to facilitate a "zero-config" developer onboarding experience.

    Args:
        monkeypatch: Pytest utility to patch environment or module variables.
        tmp_path: Pytest utility to isolate temporary directory storage.
    """
    # -------------------------------------------------------------------------
    # GIVEN: An isolated configuration directory and an empty ports.yml file
    # -------------------------------------------------------------------------
    temp_config_dir = tmp_path / "config"
    temp_config_dir.mkdir()
    ports_file = temp_config_dir / "ports.yml"

    # Write empty dictionary structure to simulated ports.yml
    with ports_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump({"ports": {}}, f)

    # -------------------------------------------------------------------------
    # WHEN: We patch CONFIG_DIR to point to our isolated test directory
    # -------------------------------------------------------------------------

    monkeypatch.setattr(cl, "CONFIG_DIR", temp_config_dir)

    # And: load the configuration using the from_yaml class method
    config = PortsConfig.from_yaml()

    # -------------------------------------------------------------------------
    # THEN: Verify that the fallback standard default ports are correctly applied
    # -------------------------------------------------------------------------
    assert config.s3_compatible == 8333
    assert config.iceberg_catalog == 8181


def test_ports_config_from_yaml_custom_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify from_yaml correctly loads custom ports from ports.yml.

    This ensures that developer-supplied port custom overrides are correctly
    respected and parsed into the configuration object.

    Args:
        monkeypatch: Pytest utility to patch environment or module variables.
        tmp_path: Pytest utility to isolate temporary directory storage.
    """
    # -------------------------------------------------------------------------
    # GIVEN: An isolated configuration directory and a custom ports.yml
    # -------------------------------------------------------------------------
    temp_config_dir = tmp_path / "config"
    temp_config_dir.mkdir()
    ports_file = temp_config_dir / "ports.yml"

    custom_config = {
        "ports": {
            "s3_compatible": 9999,
            "iceberg_catalog": 7777,
        }
    }
    with ports_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump(custom_config, f)

    # -------------------------------------------------------------------------
    # WHEN: We patch CONFIG_DIR to point to our isolated test directory
    # -------------------------------------------------------------------------
    monkeypatch.setattr(cl, "CONFIG_DIR", temp_config_dir)

    # And: load the configuration using the from_yaml class method
    config = PortsConfig.from_yaml()

    # -------------------------------------------------------------------------
    # THEN: Verify that the class loader successfully parsed the custom values
    # -------------------------------------------------------------------------
    assert config.s3_compatible == 9999
    assert config.iceberg_catalog == 7777


def test_ports_config_from_yaml_file_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify that from_yaml raises FileNotFoundError if ports.yml does not exist.

    This validates that we fail-fast immediately with a clear exception if
    the project configuration has not been initialized.

    Args:
        monkeypatch: Pytest utility to patch environment or module variables.
        tmp_path: Pytest utility to isolate temporary directory storage.
    """
    # -------------------------------------------------------------------------
    # GIVEN: An isolated configuration directory containing NO ports.yml file
    # -------------------------------------------------------------------------
    temp_config_dir = tmp_path / "config"
    temp_config_dir.mkdir()

    # -------------------------------------------------------------------------
    # WHEN: We patch CONFIG_DIR to point to our empty folder
    # -------------------------------------------------------------------------
    monkeypatch.setattr(cl, "CONFIG_DIR", temp_config_dir)

    # -------------------------------------------------------------------------
    # THEN: Verify that a FileNotFoundError is immediately raised upon load
    # -------------------------------------------------------------------------
    with pytest.raises(FileNotFoundError):
        PortsConfig.from_yaml()
