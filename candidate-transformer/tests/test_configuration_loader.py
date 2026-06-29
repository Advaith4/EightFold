"""Configuration loader tests."""

from pathlib import Path

import pytest

from src.config import ConfigurationLoader
from src.exceptions import ConfigurationError


def test_configuration_loader_loads_yaml(tmp_path: Path) -> None:
    """Configuration loader parses YAML mappings."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text("application:\n  name: Test\n", encoding="utf-8")

    loader = ConfigurationLoader(config_path)
    config = loader.load()

    assert config["application"]["name"] == "Test"


def test_configuration_loader_caches_result(tmp_path: Path) -> None:
    """Configuration loader returns the cached mapping after first load."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text("value: first\n", encoding="utf-8")

    loader = ConfigurationLoader(config_path)
    first_config = loader.load()
    config_path.write_text("value: second\n", encoding="utf-8")
    second_config = loader.load()

    assert first_config is second_config
    assert second_config["value"] == "first"


def test_configuration_loader_raises_for_missing_file(tmp_path: Path) -> None:
    """Configuration loader fails fast when a file does not exist."""
    loader = ConfigurationLoader(tmp_path / "missing.yaml")

    with pytest.raises(ConfigurationError, match="Configuration file not found"):
        loader.load()
