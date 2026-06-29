"""Streamlit entry point for the candidate transformer foundation."""

from pathlib import Path

from src.config import ConfigurationLoader
from src.exceptions import ApplicationError
from src.logging import ProjectLogger
from src.pipeline import CandidatePipeline
from src.ui.landing_page import LandingPageRenderer


def main() -> None:
    """Run the Streamlit application."""
    root = Path(__file__).parent
    app_config = ConfigurationLoader(root / "config" / "default.yaml").load()
    logging_config = ConfigurationLoader(root / "config" / "logging.yaml").load()

    project_logger = ProjectLogger(logging_config)
    logger = project_logger.get_logger()
    logger.info("Application startup completed")

    pipeline = CandidatePipeline()
    pipeline.initialize()

    renderer = LandingPageRenderer(
        app_config=app_config,
        pipeline=pipeline,
        logger_configured=project_logger.is_configured,
    )
    renderer.render()


if __name__ == "__main__":
    try:
        main()
    except ApplicationError as error:
        raise SystemExit(str(error)) from error
