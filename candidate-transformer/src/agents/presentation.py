"""Presentation projection agent for intelligence results."""

from __future__ import annotations

from src.agents.models import (
    DecisionContext,
    IntelligenceResult,
    PresentationResult,
    PresentationSummary,
)
from src.models import CanonicalCandidate, LinkType
from src.models.base import JsonValue


class PresentationAgent:
    """Prepare intelligence output for UI, API, and export consumers."""

    projection_version = "presentation_v1"

    def present(self, candidate_output: object) -> PresentationResult:
        """Create deterministic presentation artifacts from intelligence output."""
        if not isinstance(candidate_output, IntelligenceResult):
            raise TypeError("PresentationAgent requires an IntelligenceResult")
        candidate = candidate_output.canonical_candidate
        context = candidate_output.decision_context
        warnings = self._presentation_warnings(candidate, context)
        summary = PresentationSummary(
            workflow_status=context.workflow_status,
            candidate_confidence=candidate.confidence.score,
            sources=context.detected_sources,
            decision_count=len(candidate.decision_logs),
            missing_fields=context.missing_important_fields,
            conflicting_fields=context.conflicting_fields,
            presentation_warnings=warnings,
        )
        return PresentationResult(
            candidate=candidate,
            decision_context=context,
            summary=summary,
            projections={
                "recruiter": self._recruiter_view(candidate, summary),
                "hr": self._hr_view(candidate, summary),
                "engineering": self._engineering_view(candidate, summary),
            },
            warnings=warnings,
            metadata={
                "projection_version": self.projection_version,
                "generated_by": "PresentationAgent",
                "projection_names": ["recruiter", "hr", "engineering"],
                "warning_count": len(warnings),
            },
        )

    def _presentation_warnings(
        self, candidate: CanonicalCandidate, context: DecisionContext
    ) -> tuple[str, ...]:
        warnings: list[str] = []
        if candidate.identity.full_name is None:
            warnings.append("missing name")
        if not candidate.contact_info.emails:
            warnings.append("missing email")
        if not candidate.contact_info.phones:
            warnings.append("missing phone")
        if context.missing_important_fields:
            warnings.append("incomplete profile")
        return tuple(warnings)

    def _recruiter_view(
        self, candidate: CanonicalCandidate, summary: PresentationSummary
    ) -> dict[str, JsonValue]:
        return {
            "candidate_id": candidate.candidate_id,
            "full_name": candidate.identity.full_name,
            "email": candidate.contact_info.preferred_email,
            "phone": candidate.contact_info.preferred_phone,
            "location": candidate.location.display_name if candidate.location else None,
            "summary": candidate.summary,
            "skills": [skill.name for skill in candidate.skills],
            "experience_count": len(candidate.experiences),
            "education_count": len(candidate.education),
            "workflow_status": summary.workflow_status.value,
            "confidence": summary.candidate_confidence,
            "warnings": list(summary.presentation_warnings),
        }

    def _hr_view(
        self, candidate: CanonicalCandidate, summary: PresentationSummary
    ) -> dict[str, JsonValue]:
        return {
            "candidate_id": candidate.candidate_id,
            "full_name": candidate.identity.full_name,
            "contact_email": candidate.contact_info.preferred_email,
            "contact_phone": candidate.contact_info.preferred_phone,
            "sources": list(summary.sources),
            "education": [
                {
                    "institution": item.institution,
                    "credential": item.credential,
                    "field_of_study": item.field_of_study,
                }
                for item in candidate.education
            ],
            "experience": [
                {
                    "title": item.title,
                    "organization": item.organization,
                    "is_current": item.is_current,
                }
                for item in candidate.experiences
            ],
            "decision_count": summary.decision_count,
            "missing_fields": list(summary.missing_fields),
            "workflow_status": summary.workflow_status.value,
        }

    def _engineering_view(
        self, candidate: CanonicalCandidate, summary: PresentationSummary
    ) -> dict[str, JsonValue]:
        return {
            "candidate_id": candidate.candidate_id,
            "full_name": candidate.identity.full_name,
            "skills": [
                {
                    "name": skill.name,
                    "category": str(skill.category) if skill.category else None,
                    "evidence_count": skill.evidence_count,
                }
                for skill in candidate.skills
            ],
            "links": [
                {
                    "type": str(link.link_type),
                    "url": link.url,
                    "label": link.label,
                }
                for link in candidate.links
            ],
            "github_profile": self._github_profile(candidate),
            "decision_count": summary.decision_count,
            "conflicting_fields": list(summary.conflicting_fields),
            "confidence": summary.candidate_confidence,
            "workflow_status": summary.workflow_status.value,
        }

    def _github_profile(self, candidate: CanonicalCandidate) -> str | None:
        for link in candidate.links:
            if str(link.link_type) == LinkType.GITHUB.value:
                return link.url
        return None
