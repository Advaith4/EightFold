"""Professional Streamlit landing page for Sprint 1."""

from typing import Any

import streamlit as st

from src.pipeline import CandidatePipeline
from src.ui.status import SystemStatus


class LandingPageRenderer:
    """Render the Sprint 1 Streamlit application shell."""

    def __init__(
        self,
        app_config: dict[str, Any],
        pipeline: CandidatePipeline,
        logger_configured: bool,
    ) -> None:
        """Initialize the renderer.

        Args:
            app_config: Loaded application configuration.
            pipeline: Pipeline skeleton instance.
            logger_configured: Whether project logging was configured.
        """
        self._app_config = app_config
        self._pipeline = pipeline
        self._status = SystemStatus(
            configuration_loaded=True,
            logger_configured=logger_configured,
            pipeline_initialized=True,
        )

    def render(self) -> None:
        """Render the complete landing page."""
        application = self._app_config.get("application", {})
        title = application.get(
            "name",
            "Candidate Intelligence Transformation Engine",
        )

        st.set_page_config(page_title=title, page_icon="CI", layout="wide")
        self._render_header(str(title))
        self._render_status()
        self._render_pipeline()
        self._render_configuration()

    def _render_header(self, title: str) -> None:
        """Render the page header and architecture overview."""
        st.title(title)
        st.caption("Sprint 1: Project Foundation")
        st.markdown(
            "A clean engineering baseline for future candidate intelligence "
            "transformation workflows."
        )

        overview_cols = st.columns(4)
        overview_cols[0].metric("Architecture", "Clean")
        overview_cols[1].metric("Configuration", "YAML")
        overview_cols[2].metric("Logging", "Structured")
        overview_cols[3].metric("Pipeline", "Initialized")

    def _render_status(self) -> None:
        """Render system status indicators."""
        st.subheader("System Status")
        status_cols = st.columns(3)
        status_cols[0].success(self._status.configuration_label)
        status_cols[1].success(self._status.logger_label)
        status_cols[2].success(self._status.pipeline_label)

        st.subheader("Sprint Status")
        st.info("Foundation complete. Transformation logic is intentionally absent.")

    def _render_pipeline(self) -> None:
        """Render planned pipeline stages."""
        st.subheader("Planned Pipeline Stages")
        stage_cols = st.columns(3)
        for index, stage in enumerate(self._pipeline.stages):
            stage_cols[index % 3].code(stage, language="text")

    def _render_configuration(self) -> None:
        """Render loaded configuration details."""
        st.subheader("Loaded Configuration")
        st.json(self._app_config)
