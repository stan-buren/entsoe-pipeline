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

"""Unit tests for the environment switcher utility module.

This module validates that the switch_env utility correctly writes
the target environment parameter into the active environment YAML configuration
and gracefully handles terminal parameter validation errors.
"""

import sys

from pathlib import Path

import pytest

import entsoe_pipeline.config.switch_env as se

from entsoe_pipeline.config.switch_env import main, switch_environment


def test_switch_environment_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify switch_environment successfully rewrites active_environment in YAML.

    This ensures that target environment values are substituted precisely
    while preserving structure and formatting of the original config.
    """
    # -------------------------------------------------------------------------
    # ARRANGE: Setup isolated CONFIG_DIR and mock environment YAML
    # -------------------------------------------------------------------------
    temp_config_dir = tmp_path / "config"
    temp_config_dir.mkdir()
    config_file = temp_config_dir / "enviroment.yml"

    initial_content = (
        "# Configuration file\n"
        "active_environment: IOP\n"
        "environments:\n"
        "  IOP: {}\n"
        "  PROD: {}\n"
    )
    config_file.write_text(initial_content, encoding="utf-8")

    monkeypatch.setattr(se, "CONFIG_DIR", temp_config_dir)

    # -------------------------------------------------------------------------
    # ACT: Switch environment to PROD
    # -------------------------------------------------------------------------
    switch_environment("PROD")

    # -------------------------------------------------------------------------
    # ASSERT: Verify file contents were modified correctly
    # -------------------------------------------------------------------------
    updated_content = config_file.read_text(encoding="utf-8")
    assert "active_environment: PROD" in updated_content
    assert "# Configuration file" in updated_content


def test_switch_environment_file_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify switch_environment raises FileNotFoundError if config file is missing."""
    # -------------------------------------------------------------------------
    # ARRANGE: Point CONFIG_DIR to empty isolated folder
    # -------------------------------------------------------------------------
    temp_config_dir = tmp_path / "config"
    temp_config_dir.mkdir()

    monkeypatch.setattr(se, "CONFIG_DIR", temp_config_dir)

    # -------------------------------------------------------------------------
    # ACT & ASSERT: Expect FileNotFoundError when executing switch
    # -------------------------------------------------------------------------
    with pytest.raises(FileNotFoundError):
        switch_environment("PROD")


def test_main_cli_missing_args(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify main exits and prints usage when no arguments are provided."""
    # -------------------------------------------------------------------------
    # ARRANGE: Setup sys.argv with no parameters (only script name)
    # -------------------------------------------------------------------------
    monkeypatch.setattr(sys, "argv", ["switch_env.py"])

    # -------------------------------------------------------------------------
    # ACT & ASSERT: Expect SystemExit(1) on main execution
    # -------------------------------------------------------------------------
    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Usage: python switch_env.py" in captured.out


def test_main_cli_unsupported_environment(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify main exits and prints error for unsupported environments."""
    # -------------------------------------------------------------------------
    # ARRANGE: Setup sys.argv with an invalid environment name
    # -------------------------------------------------------------------------
    monkeypatch.setattr(sys, "argv", ["switch_env.py", "STAGE"])

    # -------------------------------------------------------------------------
    # ACT & ASSERT: Expect SystemExit(1) on main execution
    # -------------------------------------------------------------------------
    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Error: Unsupported environment" in captured.out


def test_main_cli_file_missing_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify main catches FileNotFoundError and prints standard error output."""
    # -------------------------------------------------------------------------
    # ARRANGE: Set sys.argv to valid target and point CONFIG_DIR to empty folder
    # -------------------------------------------------------------------------
    temp_config_dir = tmp_path / "config"
    temp_config_dir.mkdir()

    monkeypatch.setattr(sys, "argv", ["switch_env.py", "PROD"])
    monkeypatch.setattr(se, "CONFIG_DIR", temp_config_dir)

    # -------------------------------------------------------------------------
    # ACT & ASSERT: Expect SystemExit(1) and error message on stderr
    # -------------------------------------------------------------------------
    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Error: Configuration file not found" in captured.err


def test_main_cli_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify main runs successfully under valid environment args and files."""
    # -------------------------------------------------------------------------
    # ARRANGE: Setup system arguments, environment YAML file, and directory patch
    # -------------------------------------------------------------------------
    temp_config_dir = tmp_path / "config"
    temp_config_dir.mkdir()
    config_file = temp_config_dir / "enviroment.yml"

    config_file.write_text("active_environment: IOP\n", encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["switch_env.py", "PROD"])
    monkeypatch.setattr(se, "CONFIG_DIR", temp_config_dir)

    # -------------------------------------------------------------------------
    # ACT: Run main entry point
    # -------------------------------------------------------------------------
    main()

    # -------------------------------------------------------------------------
    # ASSERT: Verify file state switched and success message printed
    # -------------------------------------------------------------------------
    assert "active_environment: PROD" in config_file.read_text(encoding="utf-8")
    captured = capsys.readouterr()
    assert "Successfully switched active environment to PROD" in captured.out
