"""Presentation projection agent for intelligence results."""

from __future__ import annotations

import json

from src.agents.models import (
    CandidateGroup,
    CandidateHeader,
    CandidateOverview,
    CandidatePresentation,
    ConfidenceSummary,
    DecisionContext,
    DecisionTimeline,
    EducationCard,
    EngineeringProjection,
    ExperienceCard,
    HRProjection,
    IntelligenceResult,
    PresentationResult,
    ProvenanceRow,
    RecruiterProjection,
    SkillTag,
    WorkflowStatus,
)
from src.models import CanonicalCandidate, LinkType


class PresentationAgent:
    """Prepare intelligence output for UI, API, and export consumers."""

    projection_version = "presentation_v2"

    def present(self, candidate_output: object) -> PresentationResult:
        """Create deterministic presentation artifacts from intelligence output."""
        if not isinstance(candidate_output, IntelligenceResult):
            raise TypeError("PresentationAgent requires an IntelligenceResult")
        context = candidate_output.decision_context
        selected_candidate = candidate_output.selected_candidate
        candidates = list(candidate_output.canonical_candidates) or [selected_candidate]
        candidate_groups = list(candidate_output.candidate_groups)
        presentations = [
            self._build_candidate_presentation(candidate, context)
            for candidate in candidates
        ]
        selected_presentation = self._selected_presentation(
            presentations, selected_candidate.candidate_id
        )
        pipeline_summary = self._build_pipeline_summary(
            candidate_count=len(candidates),
            candidate_group_count=len(candidate_groups),
            raw_record_count=sum(len(group.records) for group in candidate_groups),
            context=context,
        )
        processing_summary = self._build_processing_summary(
            selected_candidate=selected_candidate,
            candidates=candidates,
            context=context,
        )

        return PresentationResult(
            candidates=candidates,
            selected_candidate=selected_candidate,
            candidate_groups=candidate_groups,
            candidate_presentations=presentations,
            pipeline_summary=pipeline_summary,
            processing_summary=processing_summary,
            header=selected_presentation.header,
            overview=selected_presentation.overview,
            confidence=selected_presentation.confidence,
            provenance=selected_presentation.provenance,
            decision_log=self._build_decision_log(context),
            missing_fields=list(context.missing_important_fields),
            conflicting_fields=list(context.conflicting_fields),
            recruiter_projection=selected_presentation.recruiter_projection,
            hr_projection=selected_presentation.hr_projection,
            engineering_projection=selected_presentation.engineering_projection,
            raw_json_dump=self._build_raw_json(
                selected_candidate,
                context,
                candidates=candidates,
                candidate_groups=candidate_groups,
                pipeline_summary=pipeline_summary,
                processing_summary=processing_summary,
            ),
        )

    def _build_candidate_presentation(
        self, candidate: CanonicalCandidate, context: DecisionContext
    ) -> CandidatePresentation:
        return CandidatePresentation(
            candidate_id=candidate.candidate_id,
            header=self._build_header(candidate, context),
            overview=self._build_overview(candidate),
            confidence=self._build_confidence(candidate),
            provenance=self._build_provenance(candidate),
            recruiter_projection=self._build_recruiter_projection(candidate, context),
            hr_projection=self._build_hr_projection(candidate, context),
            engineering_projection=self._build_engineering_projection(
                candidate, context
            ),
        )

    def _selected_presentation(
        self, presentations: list[CandidatePresentation], candidate_id: str
    ) -> CandidatePresentation:
        for presentation in presentations:
            if presentation.candidate_id == candidate_id:
                return presentation
        return presentations[0]

    def _build_pipeline_summary(
        self,
        *,
        candidate_count: int,
        candidate_group_count: int,
        raw_record_count: int,
        context: DecisionContext,
    ) -> dict[str, object]:
        return {
            "raw_record_count": raw_record_count,
            "candidate_group_count": candidate_group_count,
            "canonical_candidate_count": candidate_count,
            "selected_candidate_strategy": "first_candidate",
            "workflow_status": context.workflow_status.value,
        }

    def _build_processing_summary(
        self,
        *,
        selected_candidate: CanonicalCandidate,
        candidates: list[CanonicalCandidate],
        context: DecisionContext,
    ) -> dict[str, object]:
        return {
            "selected_candidate_id": selected_candidate.candidate_id,
            "candidate_ids": [candidate.candidate_id for candidate in candidates],
            "sources": list(context.detected_sources),
            "number_of_decisions": len(context.decision_log),
            "missing_fields": list(context.missing_important_fields),
            "conflicting_fields": list(context.conflicting_fields),
        }

    def _format_workflow_status(self, status: WorkflowStatus) -> str:
        if status == WorkflowStatus.READY_FOR_PRESENTATION:
            return "Ready For Review"
        if status == WorkflowStatus.REQUIRES_HUMAN_REVIEW:
            return "Needs Human Review"
        if status == WorkflowStatus.INCOMPLETE_PROFILE:
            return "Incomplete Profile"
        return "Unknown"

    def _build_header(
        self, candidate: CanonicalCandidate, context: DecisionContext
    ) -> CandidateHeader:
        identity = candidate.identity
        contact = candidate.contact_info

        name = identity.full_name or "Unknown Candidate"

        github_url = None
        linkedin_url = None
        for link in candidate.links:
            if link.link_type == LinkType.GITHUB:
                github_url = link.url
            elif link.link_type == LinkType.LINKEDIN:
                linkedin_url = link.url

        conf_str = f"{int(candidate.confidence.score * 100)}%"

        return CandidateHeader(
            name=name,
            primary_email=contact.preferred_email,
            primary_phone=contact.preferred_phone,
            location=candidate.location.display_name if candidate.location else None,
            github_url=github_url,
            linkedin_url=linkedin_url,
            overall_confidence_score=conf_str,
            workflow_status=self._format_workflow_status(context.workflow_status),
            sources_used=list(context.detected_sources),
        )

    def _build_overview(self, candidate: CanonicalCandidate) -> CandidateOverview:
        skills = [
            SkillTag(
                name=skill.name,
                category=str(skill.category) if skill.category else None,
            )
            for skill in candidate.skills
        ]

        education = []
        for edu in candidate.education:
            start = edu.start_date or "Unknown Start"
            end = edu.end_date or "Present"
            duration = f"{start} - {end}"
            education.append(
                EducationCard(
                    institution=edu.institution,
                    degree=edu.credential,
                    field=edu.field_of_study,
                    duration=duration,
                )
            )

        experience = []
        for exp in candidate.experiences:
            start = exp.start_date or "Unknown Start"
            end = exp.end_date or "Present"
            duration = f"{start} - {end}"
            experience.append(
                ExperienceCard(
                    company=exp.organization,
                    title=exp.title,
                    duration=duration,
                    description=exp.description,
                )
            )

        return CandidateOverview(
            skills=skills, education=education, experience=experience
        )

    def _build_confidence(self, candidate: CanonicalCandidate) -> ConfidenceSummary:
        conf = candidate.confidence
        score_val = conf.score
        if score_val >= 0.8:
            level = "High"
        elif score_val >= 0.5:
            level = "Medium"
        else:
            level = "Low"

        return ConfidenceSummary(
            overall_score=f"{int(score_val * 100)}%",
            confidence_level=level,
            reason=(
                "Extracted directly from source documents"
                if score_val > 0.5
                else "Incomplete data extraction"
            ),
            method=conf.method or "Deterministic Source Precedence",
            details=conf.reasons,
        )

    def _build_provenance(self, candidate: CanonicalCandidate) -> list[ProvenanceRow]:
        rows = []

        if candidate.identity.full_name:
            pass

        rows.append(
            ProvenanceRow(
                field="Name",
                value=candidate.identity.full_name or "Unknown",
                source="System",
                method="Deterministic Extraction",
                confidence="High",
            )
        )
        if candidate.contact_info.preferred_email:
            rows.append(
                ProvenanceRow(
                    field="Primary Email",
                    value=candidate.contact_info.preferred_email,
                    source="System",
                    method="Regex Match",
                    confidence="High",
                )
            )

        return rows

    def _build_decision_log(self, context: DecisionContext) -> list[DecisionTimeline]:
        timeline = []
        for i, log in enumerate(context.decision_log):
            timeline.append(
                DecisionTimeline(
                    step=f"Step {i + 1}",
                    observation=log,
                    rule="System Policy",
                    decision="Processed successfully",
                )
            )
        return timeline

    def _build_recruiter_projection(
        self, candidate: CanonicalCandidate, context: DecisionContext
    ) -> RecruiterProjection:
        identity = candidate.identity
        contact = candidate.contact_info

        return RecruiterProjection(
            identity={
                "Name": identity.full_name,
                "First Name": identity.given_name,
                "Last Name": identity.family_name,
            },
            contact={
                "Primary Email": contact.preferred_email,
                "Primary Phone": contact.preferred_phone,
            },
            skills=[skill.name for skill in candidate.skills],
            experience_summary=f"{len(candidate.experiences)} previous roles detected",
            education_summary=(
                f"{len(candidate.education)} educational credentials found"
            ),
            confidence=f"{int(candidate.confidence.score * 100)}%",
            missing_information=list(context.missing_important_fields),
        )

    def _build_hr_projection(
        self, candidate: CanonicalCandidate, context: DecisionContext
    ) -> HRProjection:
        return HRProjection(
            candidate_timeline=[f"Added via {src}" for src in context.detected_sources],
            sources=list(context.detected_sources),
            provenance_summary="Deterministic Merge",
            missing_fields=list(context.missing_important_fields),
            decision_summary=f"Processed {len(context.decision_log)} steps.",
        )

    def _build_engineering_projection(
        self, candidate: CanonicalCandidate, context: DecisionContext
    ) -> EngineeringProjection:
        return EngineeringProjection(
            raw_sources=list(context.detected_sources),
            merge_decisions=list(context.decision_log),
            confidence_details=f"Score computed as {candidate.confidence.score}",
            available_fields=list(context.available_fields_by_source.keys()),
            processing_summary=f"Processed {context.record_count} records.",
        )

    def _build_raw_json(
        self,
        candidate: CanonicalCandidate,
        context: DecisionContext,
        *,
        candidates: list[CanonicalCandidate],
        candidate_groups: list[CandidateGroup],
        pipeline_summary: dict[str, object],
        processing_summary: dict[str, object],
    ) -> str:
        # Detailed JSON dump including the full presentation contract.
        data = {
            "selected_candidate": candidate.model_dump(mode="json"),
            "candidates": [item.model_dump(mode="json") for item in candidates],
            "candidate_groups": [
                group.model_dump(mode="json") for group in candidate_groups
            ],
            "pipeline_summary": pipeline_summary,
            "processing_summary": processing_summary,
            "workflow_status": context.workflow_status.value,
        }

        from typing import Any

        # Remove massive audit trails to make the JSON readable
        def clean_dict(d: dict[str, Any] | list[Any]) -> None:
            if isinstance(d, dict):
                d.pop("provenance", None)
                d.pop("decision_logs", None)
                d.pop("audit_information", None)
                for v in d.values():
                    clean_dict(v)
            elif isinstance(d, list):
                for item in d:
                    clean_dict(item)

        clean_dict(data)

        return json.dumps(data, indent=2)
