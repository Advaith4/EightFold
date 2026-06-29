"""Configuration loader tests."""

from pathlib import Path

import pytest
from src.config import ConfigurationLoader, LoggingConfig, ProjectConfig
from src.exceptions import ConfigurationError


def test_configuration_loader_loads_project_yaml(tmp_path: Path) -> None:
    """Configuration loader parses project YAML into a typed model."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "application:\n"
        "  name: Test\n"
        "  environment: local\n"
        "pipeline:\n"
        "  current_sprint: Phase 1\n"
        "  status: Foundation ready\n"
        "  stages: []\n"
        "paths:\n"
        "  inputs: inputs\n"
        "  outputs: outputs\n"
        "  logs: logs\n",
        encoding="utf-8",
    )

    loader = ConfigurationLoader(config_path)
    config = loader.load()

    assert isinstance(config, ProjectConfig)
    assert config.application.name == "Test"


def test_configuration_loader_loads_logging_yaml(tmp_path: Path) -> None:
    """Configuration loader parses logging YAML into a typed model."""
    config_path = tmp_path / "logging.yaml"
    config_path.write_text(
        "logging:\n"
        "  level: INFO\n"
        "  directory: logs\n"
        "  file_name: application.log\n"
        "  rotation: '00:00'\n"
        "  retention: 14 days\n"
        "  compression: zip\n"
        "  format: '{time} | {level} | {message}'\n",
        encoding="utf-8",
    )

    config = ConfigurationLoader(config_path).load()

    assert isinstance(config, LoggingConfig)
    assert config.logging.level.value == "INFO"


def test_configuration_loader_caches_result(tmp_path: Path) -> None:
    """Configuration loader returns the cached model after first load."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "application:\n"
        "  name: First\n"
        "  environment: local\n"
        "pipeline:\n"
        "  current_sprint: Phase 1\n"
        "  status: Foundation ready\n"
        "  stages: []\n"
        "paths:\n"
        "  inputs: inputs\n"
        "  outputs: outputs\n"
        "  logs: logs\n",
        encoding="utf-8",
    )

    loader = ConfigurationLoader(config_path)
    first_config = loader.load()
    config_path.write_text(
        "application:\n"
        "  name: Second\n"
        "  environment: local\n"
        "pipeline:\n"
        "  current_sprint: Phase 1\n"
        "  status: Foundation ready\n"
        "  stages: []\n"
        "paths:\n"
        "  inputs: inputs\n"
        "  outputs: outputs\n"
        "  logs: logs\n",
        encoding="utf-8",
    )
    second_config = loader.load()

    assert first_config is second_config
    assert isinstance(second_config, ProjectConfig)
    assert second_config.application.name == "First"


def test_configuration_loader_reload_refreshes_cache(tmp_path: Path) -> None:
    """Configuration reload replaces the cached model with new YAML."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "application:\n"
        "  name: First\n"
        "  environment: local\n"
        "pipeline:\n"
        "  current_sprint: Phase 1\n"
        "  status: Foundation ready\n"
        "  stages: []\n"
        "paths:\n"
        "  inputs: inputs\n"
        "  outputs: outputs\n"
        "  logs: logs\n",
        encoding="utf-8",
    )

    loader = ConfigurationLoader(config_path)
    loader.load()
    config_path.write_text(
        "application:\n"
        "  name: Second\n"
        "  environment: local\n"
        "pipeline:\n"
        "  current_sprint: Phase 1\n"
        "  status: Foundation ready\n"
        "  stages: []\n"
        "paths:\n"
        "  inputs: inputs\n"
        "  outputs: outputs\n"
        "  logs: logs\n",
        encoding="utf-8",
    )

    reloaded = loader.reload()

    assert isinstance(reloaded, ProjectConfig)
    assert reloaded.application.name == "Second"


def test_configuration_loader_reload_preserves_cache_on_error(tmp_path: Path) -> None:
    """Configuration reload keeps the last valid cache when reload fails."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "application:\n"
        "  name: First\n"
        "  environment: local\n"
        "pipeline:\n"
        "  current_sprint: Phase 1\n"
        "  status: Foundation ready\n"
        "  stages: []\n"
        "paths:\n"
        "  inputs: inputs\n"
        "  outputs: outputs\n"
        "  logs: logs\n",
        encoding="utf-8",
    )

    loader = ConfigurationLoader(config_path)
    loader.load()
    config_path.write_text("- invalid-shape\n", encoding="utf-8")

    with pytest.raises(ConfigurationError):
        loader.reload()

    cached = loader.load()
    assert isinstance(cached, ProjectConfig)
    assert cached.application.name == "First"


def test_configuration_loader_get_preserves_top_level_api(tmp_path: Path) -> None:
    """Configuration loader get returns top-level values for compatibility."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "application:\n"
        "  name: Test\n"
        "  environment: local\n"
        "pipeline:\n"
        "  current_sprint: Phase 1\n"
        "  status: Foundation ready\n"
        "  stages: []\n"
        "paths:\n"
        "  inputs: inputs\n"
        "  outputs: outputs\n"
        "  logs: logs\n",
        encoding="utf-8",
    )

    assert ConfigurationLoader(config_path).get("application")["name"] == "Test"


def test_configuration_loader_raises_for_missing_file(tmp_path: Path) -> None:
    """Configuration loader fails fast when a file does not exist."""
    loader = ConfigurationLoader(tmp_path / "missing.yaml")

    with pytest.raises(ConfigurationError, match="Configuration file not found"):
        loader.load()
