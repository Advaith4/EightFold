"""Professional Streamlit landing page for Sprint 1."""

import streamlit as st

from src.config import ProjectConfig
from src.pipeline import CandidatePipeline
from src.ui.status import SystemStatus


class LandingPageRenderer:
    """Render the Sprint 1 Streamlit application shell."""

    def __init__(
        self,
        app_config: ProjectConfig,
        pipeline: CandidatePipeline,
        pipeline_initialized: bool,
        logger_configured: bool,
        version: str,
    ) -> None:
        """Initialize the renderer.

        Args:
            app_config: Loaded application configuration.
            pipeline: Pipeline skeleton instance.
            pipeline_initialized: Whether pipeline initialization completed.
            logger_configured: Whether project logging was configured.
            version: Application version.
        """
        self._app_config = app_config
        self._pipeline = pipeline
        self._status = SystemStatus(
            current_sprint=app_config.pipeline.current_sprint,
            project_status=app_config.pipeline.status.value,
            configuration_loaded=True,
            logger_configured=logger_configured,
            pipeline_initialized=pipeline_initialized,
            version=version,
        )

    def render(self) -> None:
        """Render the complete landing page."""
        st.set_page_config(
            page_title=self._app_config.application.name,
            page_icon=self._app_config.ui.page_icon,
            layout=self._app_config.ui.layout,
        )
        st.title(self._app_config.application.name)
        self._render_status()

    def _render_status(self) -> None:
        """Render requested developer status indicators."""
        status_rows = {
            "Current Sprint": self._status.current_sprint,
            "Project Status": self._status.project_status,
            "Logger Status": self._status.logger_label,
            "Configuration Status": self._status.configuration_label,
            "Pipeline Status": self._status.pipeline_label,
            "Version": self._status.version,
        }

        cols = st.columns(3)
        for index, item in enumerate(status_rows.items()):
            label, value = item
            cols[index % 3].metric(label, value)
