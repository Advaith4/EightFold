"""Typed configuration models."""

from typing import Any, Literal

from pydantic import BaseModel, Field

from src.enums import LogLevel, PipelineStatus


class ApplicationSettings(BaseModel):
    """Application-level settings."""

    name: str
    environment: str


class PipelineSettings(BaseModel):
    """Pipeline display and foundation settings."""

    current_sprint: str
    status: PipelineStatus = PipelineStatus.FOUNDATION_READY
    stages: list[str] = Field(default_factory=list)


class PathSettings(BaseModel):
    """Filesystem path settings."""

    inputs: str
    outputs: str
    logs: str


class UISettings(BaseModel):
    """UI presentation settings."""

    page_icon: str = "CI"
    layout: Literal["centered", "wide"] = "wide"


class ProjectConfig(BaseModel):
    """Typed application configuration."""

    application: ApplicationSettings
    pipeline: PipelineSettings
    paths: PathSettings
    ui: UISettings = Field(default_factory=UISettings)


class LoggingSettings(BaseModel):
    """Logging sink settings."""

    level: LogLevel = LogLevel.INFO
    directory: str
    file_name: str
    rotation: str
    retention: str
    compression: str
    format: str


class LoggingConfig(BaseModel):
    """Typed logging configuration."""

    logging: LoggingSettings


ConfigModel = ProjectConfig | LoggingConfig


def to_mapping(config: ConfigModel) -> dict[str, Any]:
    """Convert a typed configuration model to a dictionary."""
    return config.model_dump(mode="json")
