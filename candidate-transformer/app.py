"""Streamlit entry point for the candidate transformer foundation."""

from pathlib import Path

from src.__version__ import __version__
from src.adapters import AdapterRegistry
from src.config import ConfigurationLoader, LoggingConfig, ProjectConfig
from src.exceptions import ApplicationError
from src.logging import ProjectLogger
from src.pipeline import CandidatePipeline, PipelineContext
from src.services import ServiceContainer
from src.ui.landing_page import LandingPageRenderer


def main() -> None:
    """Run the Streamlit application."""
    root = Path(__file__).parent
    app_config = ConfigurationLoader(root / "config" / "default.yaml").load()
    logging_config = ConfigurationLoader(root / "config" / "logging.yaml").load()

    if not isinstance(app_config, ProjectConfig):
        raise ApplicationError("Default configuration did not produce ProjectConfig.")
    if not isinstance(logging_config, LoggingConfig):
        raise ApplicationError("Logging configuration did not produce LoggingConfig.")

    project_logger = ProjectLogger(logging_config)
    logger = project_logger.get_logger()
    logger.info("Application startup completed")

    services = ServiceContainer(
        app_config=app_config,
        logging_config=logging_config,
        logger=project_logger,
        adapter_registry=AdapterRegistry(),
    )
    pipeline = CandidatePipeline(services=services)
    stage_result = pipeline.initialize()
    pipeline_context = stage_result.payload

    renderer = LandingPageRenderer(
        app_config=app_config,
        pipeline=pipeline,
        pipeline_initialized=isinstance(pipeline_context, PipelineContext)
        and bool(pipeline_context.metadata.get("pipeline_initialized", False)),
        logger_configured=project_logger.is_configured,
        version=__version__,
    )
    renderer.render()


if __name__ == "__main__":
    try:
        main()
    except ApplicationError as error:
        raise SystemExit(str(error)) from error
