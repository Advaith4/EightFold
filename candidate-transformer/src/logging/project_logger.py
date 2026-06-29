"""Project logging setup."""

import sys
from pathlib import Path
from typing import Any

from loguru import logger

from src.config.models import LoggingConfig, LoggingSettings
from src.exceptions import ConfigurationError


class ProjectLogger:
    """Configure console and rotating file logging for the project."""

    def __init__(self, config: LoggingConfig | dict[str, Any]) -> None:
        """Initialize logger configuration.

        Args:
            config: Typed or mapping-based logging configuration.
        """
        self._config = config
        self._configured = False

    @property
    def is_configured(self) -> bool:
        """Return whether logging sinks have been configured."""
        return self._configured

    def configure(self) -> None:
        """Configure Loguru sinks.

        Raises:
            ConfigurationError: If required logging configuration is missing.
        """
        logging_config = self._logging_settings()
        level = logging_config.level.value
        directory = Path(logging_config.directory)
        file_name = logging_config.file_name
        log_format = logging_config.format

        directory.mkdir(parents=True, exist_ok=True)
        logger.remove()
        logger.add(sys.stderr, level=level, format=log_format)
        logger.add(
            directory / file_name,
            level=level,
            format=log_format,
            rotation=logging_config.rotation,
            retention=logging_config.retention,
            compression=logging_config.compression,
        )
        self._configured = True

    def get_logger(self) -> Any:
        """Return the configured Loguru logger.

        Returns:
            Loguru logger instance.
        """
        if not self._configured:
            self.configure()
        return logger

    def _logging_settings(self) -> LoggingSettings:
        """Return validated logging settings."""
        if isinstance(self._config, LoggingConfig):
            return self._config.logging

        logging_config = self._config.get("logging")
        if not isinstance(logging_config, dict):
            raise ConfigurationError("Logging configuration must define 'logging'.")
        return LoggingConfig.model_validate({"logging": logging_config}).logging
