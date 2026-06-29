"""Service container tests."""

from src.adapters import AdapterRegistry
from src.config.models import (
    ApplicationSettings,
    LoggingConfig,
    LoggingSettings,
    PathSettings,
    PipelineSettings,
    ProjectConfig,
)
from src.enums import LogLevel, PipelineStatus
from src.logging import ProjectLogger
from src.services import ServiceContainer


def test_service_container_holds_infrastructure_services() -> None:
    """Service container exposes explicitly provided infrastructure services."""
    app_config = ProjectConfig(
        application=ApplicationSettings(name="Test", environment="test"),
        pipeline=PipelineSettings(
            current_sprint="Phase 1",
            status=PipelineStatus.FOUNDATION_READY,
            stages=[],
        ),
        paths=PathSettings(inputs="inputs", outputs="outputs", logs="logs"),
    )
    logging_config = LoggingConfig(
        logging=LoggingSettings(
            level=LogLevel.INFO,
            directory="logs",
            file_name="application.log",
            rotation="00:00",
            retention="1 day",
            compression="zip",
            format="{time} | {level} | {message}",
        )
    )
    logger = ProjectLogger(logging_config)
    registry = AdapterRegistry()

    container = ServiceContainer(
        app_config=app_config,
        logging_config=logging_config,
        logger=logger,
        adapter_registry=registry,
    )

    assert container.app_config is app_config
    assert container.logging_config is logging_config
    assert container.logger is logger
    assert container.adapter_registry is registry
