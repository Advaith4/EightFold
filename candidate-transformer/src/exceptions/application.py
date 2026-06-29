"""Custom application exceptions."""


class ApplicationError(Exception):
    """Base error for application-specific failures."""

    def __init__(self, message: str) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable failure details.
        """
        super().__init__(message)
        self.message = message


class ConfigurationError(ApplicationError):
    """Raised when configuration cannot be loaded or used."""


class PipelineError(ApplicationError):
    """Raised when pipeline orchestration fails."""


class AdapterError(ApplicationError):
    """Raised when an adapter cannot load or parse a source."""


class ValidationError(ApplicationError):
    """Raised when validation cannot be completed."""


class UIError(ApplicationError):
    """Raised when UI initialization or rendering fails."""
