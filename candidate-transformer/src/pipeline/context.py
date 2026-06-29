"""Pipeline context passed between transformation stages."""

from typing import Any

from pydantic import BaseModel, Field


class PipelineContext(BaseModel):
    """Represent infrastructure-level stage-to-stage pipeline state.

    Pipeline stages own mutations to this object while executing. The context is
    intentionally free of candidate-specific fields until domain models are
    introduced in a future phase.
    """

    raw_records: list[Any] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
