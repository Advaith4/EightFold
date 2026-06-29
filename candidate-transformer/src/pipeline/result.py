"""Pipeline stage result contracts."""

from time import perf_counter
from typing import Any

from pydantic import BaseModel, Field


class StageResult(BaseModel):
    """Consistent return contract for pipeline stages."""

    success: bool
    payload: Any | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    execution_time: float = 0.0


class StageTimer:
    """Measure stage execution time."""

    def __init__(self) -> None:
        """Create a stage timer."""
        self._started_at = perf_counter()

    def elapsed(self) -> float:
        """Return elapsed seconds since timer creation."""
        return perf_counter() - self._started_at
