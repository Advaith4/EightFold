"""YAML-backed configuration loading."""

from pathlib import Path
from typing import Any

import yaml

from src.exceptions import ConfigurationError


class ConfigurationLoader:
    """Load and cache YAML configuration files."""

    def __init__(self, config_path: str | Path) -> None:
        """Initialize the loader.

        Args:
            config_path: Path to a YAML configuration file.
        """
        self._config_path = Path(config_path)
        self._cached_config: dict[str, Any] | None = None

    @property
    def config_path(self) -> Path:
        """Return the configured YAML path."""
        return self._config_path

    def load(self) -> dict[str, Any]:
        """Load and cache configuration.

        Returns:
            Parsed configuration values.

        Raises:
            ConfigurationError: If the file is missing, invalid, or empty.
        """
        if self._cached_config is not None:
            return self._cached_config

        if not self._config_path.exists():
            raise ConfigurationError(
                f"Configuration file not found: {self._config_path}"
            )

        if not self._config_path.is_file():
            raise ConfigurationError(
                f"Configuration path is not a file: {self._config_path}"
            )

        try:
            content = yaml.safe_load(self._config_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ConfigurationError(
                f"Configuration file contains invalid YAML: {self._config_path}"
            ) from exc

        if not isinstance(content, dict):
            raise ConfigurationError(
                f"Configuration file must contain a YAML mapping: {self._config_path}"
            )

        self._cached_config = content
        return self._cached_config

    def get(self, key: str, default: Any = None) -> Any:
        """Return a top-level configuration value.

        Args:
            key: Top-level configuration key.
            default: Value returned when the key is absent.

        Returns:
            The matching configuration value or the default.
        """
        return self.load().get(key, default)
