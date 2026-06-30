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
    """Source type identifiers used by infrastructure pipeline stages."""

    CSV = "CSV"
    ATS = "ATS"
    ATS_JSON = "ATS_JSON"
    RESUME = "Resume"
    RECRUITER_CSV = "RECRUITER_CSV"
    GITHUB = "GitHub"
    GITHUB_PROFILE = "GITHUB_PROFILE"
    LINKEDIN = "LinkedIn"
    UNKNOWN = "UNKNOWN"


class LogLevel(str, Enum):  # noqa: UP042
    """Supported logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
