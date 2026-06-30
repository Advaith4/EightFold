"""Models used by the multi-agent orchestration layer."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from src.models import CanonicalCandidate, RawCandidateRecord


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


class CandidateGroup(BaseModel):
    """Deterministic cluster of raw records believed to represent one candidate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    group_id: str
    records: tuple[RawCandidateRecord, ...]
    match_keys: tuple[str, ...]


class IntelligenceResult(BaseModel):
    """Canonical candidates and reasoning context produced by intelligence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    decision_context: DecisionContext
    candidate_groups: tuple[CandidateGroup, ...] = ()
    canonical_candidates: tuple[CanonicalCandidate, ...] = ()
    selected_candidate: CanonicalCandidate
    canonical_candidate: CanonicalCandidate


# ==============================================================================
# Presentation View Models
# ==============================================================================


class SkillTag(BaseModel):
    name: str
    category: str | None


class EducationCard(BaseModel):
    institution: str | None
    degree: str | None
    field: str | None
    duration: str


class ExperienceCard(BaseModel):
    company: str | None
    title: str | None
    duration: str
    description: str | None


class CandidateHeader(BaseModel):
    name: str
    primary_email: str | None
    primary_phone: str | None
    location: str | None
    github_url: str | None
    linkedin_url: str | None
    overall_confidence_score: str
    workflow_status: str
    sources_used: list[str]


class CandidateOverview(BaseModel):
    skills: list[SkillTag]
    education: list[EducationCard]
    experience: list[ExperienceCard]


class ConfidenceSummary(BaseModel):
    overall_score: str
    confidence_level: str
    reason: str
    method: str
    details: list[str] | None = None


class ProvenanceRow(BaseModel):
    field: str
    value: str
    source: str
    method: str
    confidence: str


class DecisionTimeline(BaseModel):
    step: str
    observation: str
    rule: str
    decision: str


class RecruiterProjection(BaseModel):
    identity: dict[str, str | None]
    contact: dict[str, str | None]
    skills: list[str]
    experience_summary: str
    education_summary: str
    confidence: str
    missing_information: list[str]


class HRProjection(BaseModel):
    candidate_timeline: list[str]
    sources: list[str]
    provenance_summary: str
    missing_fields: list[str]
    decision_summary: str


class EngineeringProjection(BaseModel):
    raw_sources: list[str]
    merge_decisions: list[str]
    confidence_details: str
    available_fields: list[str]
    processing_summary: str


class CandidatePresentation(BaseModel):
    candidate_id: str
    header: CandidateHeader
    overview: CandidateOverview
    confidence: ConfidenceSummary
    provenance: list[ProvenanceRow]
    recruiter_projection: RecruiterProjection
    hr_projection: HRProjection
    engineering_projection: EngineeringProjection


class PresentationResult(BaseModel):
    """Clean View Model for UI rendering without backend logic."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidates: list[CanonicalCandidate]
    selected_candidate: CanonicalCandidate
    candidate_groups: list[CandidateGroup]
    candidate_presentations: list[CandidatePresentation]
    pipeline_summary: dict[str, object]
    processing_summary: dict[str, object]
    header: CandidateHeader
    overview: CandidateOverview
    confidence: ConfidenceSummary
    provenance: list[ProvenanceRow]
    decision_log: list[DecisionTimeline]
    missing_fields: list[str]
    conflicting_fields: list[str]
    recruiter_projection: RecruiterProjection
    hr_projection: HRProjection
    engineering_projection: EngineeringProjection
    raw_json_dump: str
