"""Typed UI status models."""

from pydantic import BaseModel


class SystemStatus(BaseModel):
    """Represent foundational system status for the UI."""

    configuration_loaded: bool
    logger_configured: bool
    pipeline_initialized: bool

    @property
    def configuration_label(self) -> str:
        """Return configuration status text."""
        return "Configuration loaded" if self.configuration_loaded else "Config error"

    @property
    def logger_label(self) -> str:
        """Return logger status text."""
        return "Logger configured" if self.logger_configured else "Logger error"

    @property
    def pipeline_label(self) -> str:
        """Return pipeline status text."""
        return "Pipeline initialized" if self.pipeline_initialized else "Pipeline error"
