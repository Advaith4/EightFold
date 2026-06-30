"""Models used by the multi-agent orchestration layer."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DecisionContext(BaseModel):
    """Deterministic observations produced before candidate transformation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    record_count: int = Field(ge=0)
    detected_sources: tuple[str, ...]
    duplicate_sources: tuple[str, ...]
    missing_important_fields: tuple[str, ...]
    available_fields_by_source: dict[str, tuple[str, ...]]
    decision_log: tuple[str, ...]
