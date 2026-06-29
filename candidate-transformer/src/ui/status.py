"""Typed UI status models."""

from pydantic import BaseModel


class SystemStatus(BaseModel):
    """Represent foundational system status for the UI."""

    current_sprint: str
    project_status: str
    configuration_loaded: bool
    logger_configured: bool
    pipeline_initialized: bool
    version: str

    @property
    def configuration_label(self) -> str:
        """Return configuration status text."""
        return "Loaded" if self.configuration_loaded else "Error"

    @property
    def logger_label(self) -> str:
        """Return logger status text."""
        return "Configured" if self.logger_configured else "Error"

    @property
    def pipeline_label(self) -> str:
        """Return pipeline status text."""
        return "Initialized" if self.pipeline_initialized else "Error"
