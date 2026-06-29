"""Project logging setup."""

import sys
from pathlib import Path
from typing import Any

from loguru import logger

from src.exceptions import ConfigurationError


class ProjectLogger:
    """Configure console and rotating file logging for the project."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize logger configuration.

        Args:
            config: Logging configuration mapping.
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
        logging_config = self._config.get("logging")
        if not isinstance(logging_config, dict):
            raise ConfigurationError("Logging configuration must define 'logging'.")

        level = str(logging_config.get("level", "INFO"))
        directory = Path(str(logging_config.get("directory", "logs")))
        file_name = str(logging_config.get("file_name", "application.log"))
        log_format = str(logging_config.get("format", "{time} | {level} | {message}"))

        directory.mkdir(parents=True, exist_ok=True)
        logger.remove()
        logger.add(sys.stderr, level=level, format=log_format)
        logger.add(
            directory / file_name,
            level=level,
            format=log_format,
            rotation=str(logging_config.get("rotation", "00:00")),
            retention=str(logging_config.get("retention", "14 days")),
            compression=str(logging_config.get("compression", "zip")),
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


