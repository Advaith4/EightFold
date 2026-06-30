"""Models used by the multi-agent orchestration layer."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from src.models import CanonicalCandidate
from src.models.base import JsonValue


class WorkflowStatus(str, Enum):  # noqa: UP042
    """Deterministic workflow readiness states for intelligence output."""

    READY_FOR_PRESENTATION = "READY_FOR_PRESENTATION"
    REQUIRES_HUMAN_REVIEW = "REQUIRES_HUMAN_REVIEW"
    INCOMPLETE_PROFILE = "INCOMPLETE_PROFILE"


class DecisionContext(BaseModel):
    """Deterministic observations produced before candidate transformation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    record_count: int = Field(ge=0)
    detected_sources: tuple[str, ...]
    duplicate_sources: tuple[str, ...]
    duplicate_record_ids: tuple[str, ...]
    required_fields: tuple[str, ...]
    missing_important_fields: tuple[str, ...]
    conflicting_fields: tuple[str, ...]
    available_fields_by_source: dict[str, tuple[str, ...]]
    workflow_status: WorkflowStatus
    decision_log: tuple[str, ...]


class IntelligenceResult(BaseModel):
    """Canonical candidate and reasoning context produced by intelligence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    canonical_candidate: CanonicalCandidate
    decision_context: DecisionContext


class PresentationSummary(BaseModel):
    """Presentation-level summary for UI, API, and export consumers."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    workflow_status: WorkflowStatus
    candidate_confidence: float = Field(ge=0.0, le=1.0)
    sources: tuple[str, ...]
    decision_count: int = Field(ge=0)
    missing_fields: tuple[str, ...]
    conflicting_fields: tuple[str, ...]
    presentation_warnings: tuple[str, ...]


class PresentationResult(BaseModel):
    """Presentation-ready candidate artifact without UI rendering."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate: CanonicalCandidate
    decision_context: DecisionContext
    summary: PresentationSummary
    projections: dict[str, dict[str, JsonValue]]
    warnings: tuple[str, ...]
    metadata: dict[str, JsonValue]
