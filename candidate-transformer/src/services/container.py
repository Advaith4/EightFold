"""Application service container."""

from src.adapters import AdapterRegistry
from src.config.models import LoggingConfig, ProjectConfig
from src.logging import ProjectLogger


class ServiceContainer:
    """Centralize infrastructure services for application wiring."""

    def __init__(
        self,
        app_config: ProjectConfig,
        logging_config: LoggingConfig,
        logger: ProjectLogger,
        adapter_registry: AdapterRegistry,
    ) -> None:
        """Initialize the service container.

        Args:
            app_config: Typed application configuration.
            logging_config: Typed logging configuration.
            logger: Project logger service.
            adapter_registry: Registry of externally managed adapters.
        """
        self.app_config = app_config
        self.logging_config = logging_config
        self.logger = logger
        self.adapter_registry = adapter_registry
