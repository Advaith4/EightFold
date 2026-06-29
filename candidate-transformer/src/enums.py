"""Shared infrastructure enums."""

from enum import Enum


class PipelineStatus(str, Enum):  # noqa: UP042
    """Known pipeline foundation statuses."""

    FOUNDATION_READY = "Foundation ready"
    INITIALIZED = "Initialized"
    NOT_IMPLEMENTED = "Not implemented"


class PipelineStage(str, Enum):  # noqa: UP042
    """Planned pipeline stages."""

    INITIALIZE = "initialize"
    INGEST = "ingest"
    MAP = "map"
    NORMALIZE = "normalize"
    GROUP = "group"
    MERGE = "merge"
    PROJECT = "project"
    VALIDATE = "validate"
    EXPORT = "export"


class SourceType(str, Enum):  # noqa: UP042
    """Future source type identifiers."""

    CSV = "CSV"
    ATS = "ATS"
    RESUME = "Resume"
    GITHUB = "GitHub"
    LINKEDIN = "LinkedIn"


class LogLevel(str, Enum):  # noqa: UP042
    """Supported logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
