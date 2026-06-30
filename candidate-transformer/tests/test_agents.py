"""Multi-agent orchestration layer tests."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError as PydanticValidationError
from src.adapters import AdapterRegistry
from src.agents import (
    AgentOrchestrator,
    CandidateIntelligenceAgent,
    DecisionContext,
    IntakeAgent,
    IntelligenceResult,
    PresentationAgent,
    PresentationResult,
    SourceConfidencePolicy,
    WorkflowStatus,
)
from src.enums import SourceType as InfrastructureSourceType
from src.github import GitHubAdapter, GitHubFetcher, GitHubPayload
from src.interfaces import BaseAdapter
from src.loaders import FileMetadata, FilePayload
from src.models import CanonicalCandidate, PayloadFormat, RawCandidateRecord
from src.models.base import JsonValue
from src.models.enums import SourceType as DomainSourceType


def raw_record(
    record_id: str = "record",
    *,
    source_type: DomainSourceType = DomainSourceType.GITHUB,
    payload: dict[str, JsonValue] | None = None,
    raw_text: str | None = None,
) -> RawCandidateRecord:
    """Create a raw candidate record for orchestration tests."""
    return RawCandidateRecord(
        record_id=record_id,
        source_type=source_type,
        source_system=str(source_type.value),
        source_record_id=record_id,
        payload_format=PayloadFormat.API_RESPONSE,
        payload=payload or {"record_id": record_id},
        raw_text=raw_text,
        checksum=f"sha256:{record_id}",
    )


def intelligence_result(record: RawCandidateRecord | None = None) -> IntelligenceResult:
    """Create a real intelligence result for orchestration doubles."""
    return CandidateIntelligenceAgent().process([record or raw_record("intake")])


class FakeGitHubFetcher(GitHubFetcher):
    """Test fetcher recording the requested profile URL."""

    def __init__(self) -> None:
        self.requested_url: str | None = None

    def fetch(self, profile_url: str) -> GitHubPayload:
        self.requested_url = profile_url
        return GitHubPayload(profile={"login": "octocat"})


class FakeGitHubAdapter(GitHubAdapter):
    """Test adapter recording the payload it parsed."""

    def __init__(self) -> None:
        self.parsed_payload: GitHubPayload | None = None

    def parse(self, raw_data: Any) -> RawCandidateRecord:
        if not isinstance(raw_data, GitHubPayload):
            raise TypeError("expected GitHubPayload")
        self.parsed_payload = raw_data
        return raw_record("github")


class FakeAdapter(BaseAdapter):
    """Test source adapter for loaded file payloads."""

    @property
    def source_type(self) -> str:
        return InfrastructureSourceType.RECRUITER_CSV.value

    def load(self) -> Any:
        return None

    def parse(self, raw_data: Any) -> RawCandidateRecord:
        assert isinstance(raw_data, FilePayload)
        return raw_record("file")

    def metadata(self) -> dict[str, Any]:
        return {"source_type": self.source_type}


class RecordingIntakeAgent(IntakeAgent):
    """Test intake agent recording supplied artifacts."""

    def __init__(self) -> None:
        self.received: object | None = None

    def process(self, artifacts: object) -> list[RawCandidateRecord]:
        self.received = artifacts
        return [raw_record("intake")]


class RecordingIntelligenceAgent(CandidateIntelligenceAgent):
    """Test intelligence agent recording raw records."""

    def __init__(self) -> None:
        self.received: list[RawCandidateRecord] | None = None

    def analyze(self, raw_records: list[RawCandidateRecord]) -> IntelligenceResult:
        self.received = raw_records
        return intelligence_result(raw_records[0])


class RecordingPresentationAgent(PresentationAgent):
    """Test presentation agent recording output."""

    def __init__(self) -> None:
        self.received: object | None = None

    def present(self, candidate_output: object) -> PresentationResult:
        self.received = candidate_output
        return super().present(candidate_output)


def test_agents_construct_with_default_dependencies() -> None:
    """Agents expose clean public constructors."""
    assert isinstance(IntakeAgent(), IntakeAgent)
    assert isinstance(CandidateIntelligenceAgent(), CandidateIntelligenceAgent)
    assert isinstance(PresentationAgent(), PresentationAgent)
    assert isinstance(AgentOrchestrator(), AgentOrchestrator)


def test_intake_agent_delegates_github_url_to_fetcher_and_adapter() -> None:
    """GitHub intake composes existing source detection, fetcher, and adapter."""
    fetcher = FakeGitHubFetcher()
    adapter = FakeGitHubAdapter()
    agent = IntakeAgent(github_fetcher=fetcher, github_adapter=adapter)

    records = agent.process("https://github.com/octocat")

    assert [record.record_id for record in records] == ["github"]
    assert fetcher.requested_url == "https://github.com/octocat"
    assert adapter.parsed_payload == GitHubPayload(profile={"login": "octocat"})


def test_intake_agent_routes_loaded_payload_to_registered_adapter() -> None:
    """Loaded file payloads are routed by detected source type to adapters."""
    registry = AdapterRegistry()
    registry.register(FakeAdapter())
    payload = FilePayload(
        text="name,email\nAda,ada@example.com\n",
        metadata=FileMetadata(
            filename="candidates.csv",
            content_type="text/csv",
            extension=".csv",
            size_bytes=31,
            checksum="sha256:file",
        ),
    )
    agent = IntakeAgent(adapter_registry=registry)

    records = agent.process(payload)

    assert [record.record_id for record in records] == ["file"]


def test_candidate_intelligence_process_returns_canonical_and_context() -> None:
    """Sprint 7.0 returns a canonical candidate plus updated decision context."""
    result = CandidateIntelligenceAgent().process(
        [
            raw_record(
                "github",
                payload={
                    "profile": {
                        "login": "octocat",
                        "name": "The Octocat",
                        "bio": "GitHub mascot",
                        "email": "octocat@example.com",
                        "html_url": "https://github.com/octocat",
                    },
                    "repositories": [],
                    "languages": {"Python": 100},
                },
            )
        ]
    )

    assert isinstance(result, IntelligenceResult)
    assert isinstance(result.canonical_candidate, CanonicalCandidate)
    assert isinstance(result.decision_context, DecisionContext)
    assert result.canonical_candidate.identity.full_name == "The Octocat"
    assert result.canonical_candidate.summary == "GitHub mascot"
    assert result.canonical_candidate.contact_info.emails == ["octocat@example.com"]
    assert result.canonical_candidate.skills == []


def test_candidate_intelligence_maps_single_resume_source() -> None:
    """Resume-only candidates map explicit fields without inference."""
    result = CandidateIntelligenceAgent().process(
        [
            raw_record(
                "resume",
                source_type=DomainSourceType.RESUME,
                payload={
                    "full_name": "Ada Lovelace",
                    "email": "ada@example.com",
                    "phone": "+15551234567",
                    "skills": ["Python"],
                    "education": [{"institution": "University", "degree": "BS"}],
                    "experience": [{"title": "Engineer", "company": "Analytical"}],
                },
            )
        ]
    )
    candidate = result.canonical_candidate

    assert candidate.identity.full_name == "Ada Lovelace"
    assert candidate.contact_info.preferred_email == "ada@example.com"
    assert candidate.contact_info.preferred_phone == "+15551234567"
    assert [skill.name for skill in candidate.skills] == ["Python"]
    assert candidate.education[0].institution == "University"
    assert candidate.experiences[0].organization == "Analytical"
    assert candidate.confidence.score == 0.85


@pytest.mark.parametrize(
    ("sources", "expected_score"),
    [
        ((DomainSourceType.ATS,), 0.95),
        ((DomainSourceType.RESUME,), 0.85),
        ((DomainSourceType.GITHUB,), 0.80),
        ((DomainSourceType.RESUME, DomainSourceType.ATS), 0.95),
        ((DomainSourceType.RESUME, DomainSourceType.GITHUB), 0.85),
        ((DomainSourceType.ATS, DomainSourceType.GITHUB), 0.95),
        (
            (DomainSourceType.RESUME, DomainSourceType.ATS, DomainSourceType.GITHUB),
            0.95,
        ),
    ],
)
def test_candidate_intelligence_assigns_deterministic_confidence(
    sources: tuple[DomainSourceType, ...], expected_score: float
) -> None:
    """Confidence comes from the configurable source reliability policy."""
    records = [
        raw_record(
            f"record-{index}",
            source_type=source,
            payload={"email": f"candidate{index}@example.com"},
        )
        for index, source in enumerate(sources)
    ]

    result = CandidateIntelligenceAgent().process(records)

    assert result.canonical_candidate.confidence.score == expected_score
    assert (
        result.canonical_candidate.confidence.method
        == "deterministic_source_precedence"
    )


def test_candidate_intelligence_accepts_replaceable_confidence_policy() -> None:
    """Confidence values are centralized in a replaceable policy object."""
    policy = SourceConfidencePolicy(
        source_scores=((DomainSourceType.RESUME.value, 0.42),),
        default_score=0.10,
        method="test_policy",
    )
    result = CandidateIntelligenceAgent(confidence_policy=policy).process(
        [
            raw_record(
                "resume",
                source_type=DomainSourceType.RESUME,
                payload={"email": "ada@example.com"},
            )
        ]
    )

    assert result.canonical_candidate.confidence.score == 0.42
    assert result.canonical_candidate.confidence.method == "test_policy"


def test_candidate_intelligence_prefers_ats_over_resume_and_github() -> None:
    """Scalar conflicts use ATS > Resume > GitHub precedence."""
    result = CandidateIntelligenceAgent().process(
        [
            raw_record(
                "github",
                payload={"profile": {"email": "github@example.com"}},
            ),
            raw_record(
                "resume",
                source_type=DomainSourceType.RESUME,
                payload={"email": "resume@example.com"},
            ),
            raw_record(
                "ats",
                source_type=DomainSourceType.ATS,
                payload={"email": "ats@example.com"},
            ),
        ]
    )

    candidate = result.canonical_candidate
    assert candidate.contact_info.preferred_email == "ats@example.com"
    assert candidate.contact_info.emails == [
        "github@example.com",
        "resume@example.com",
        "ats@example.com",
    ]
    assert "contact_info.preferred_email" in result.decision_context.conflicting_fields
    email_decision = next(
        log
        for log in candidate.decision_logs
        if log.field_path == "contact_info.preferred_email"
    )
    assert email_decision.selected_value == "ats@example.com"
    assert email_decision.rejected_values == [
        "github@example.com",
        "resume@example.com",
    ]
    assert email_decision.rule_id == "source_precedence_v1"


def test_candidate_intelligence_equal_priority_keeps_first_value() -> None:
    """Equal source priority keeps the first encountered explicit value."""
    result = CandidateIntelligenceAgent().process(
        [
            raw_record(
                "resume-1",
                source_type=DomainSourceType.RESUME,
                payload={"phone": "+10000000001"},
            ),
            raw_record(
                "resume-2",
                source_type=DomainSourceType.RESUME,
                payload={"phone": "+10000000002"},
            ),
        ]
    )

    assert result.canonical_candidate.contact_info.preferred_phone == "+10000000001"
    assert "contact_info.preferred_phone" in result.decision_context.conflicting_fields


def test_candidate_intelligence_tracks_provenance_for_populated_fields() -> None:
    """Canonical fields retain provenance back to raw records."""
    result = CandidateIntelligenceAgent().process(
        [
            raw_record(
                "resume",
                source_type=DomainSourceType.RESUME,
                payload={"full_name": "Ada Lovelace", "email": "ada@example.com"},
            )
        ]
    )
    candidate = result.canonical_candidate

    assert candidate.provenance
    assert candidate.identity.provenance[0].raw_record_id == "resume"
    assert candidate.contact_info.provenance[0].source_field == "email"
    assert candidate.decision_logs[0].provenance_ids


def test_candidate_intelligence_reports_missing_fields() -> None:
    """Missing important fields are reported in DecisionContext."""
    result = CandidateIntelligenceAgent().process(
        [
            raw_record(
                "resume",
                source_type=DomainSourceType.RESUME,
                payload={"email": "a@b.co"},
            )
        ]
    )

    assert result.decision_context.missing_important_fields == (
        "full_name",
        "phone",
        "education",
        "experience",
        "skills",
        "certifications",
    )


def test_candidate_intelligence_detects_duplicate_sources_and_records() -> None:
    """Duplicate source and record observations remain explicit."""
    result = CandidateIntelligenceAgent().process(
        [
            raw_record("same", payload={"email": "one@example.com"}),
            raw_record("same", payload={"email": "two@example.com"}),
        ]
    )

    assert result.decision_context.duplicate_sources == ("GitHub",)
    assert result.decision_context.duplicate_record_ids == ("same",)
    assert "Duplicate records detected: same" in result.decision_context.decision_log


def test_candidate_intelligence_handles_empty_input() -> None:
    """Empty input yields an empty canonical candidate and context."""
    result = CandidateIntelligenceAgent().process([])

    assert result.canonical_candidate.candidate_id.startswith("candidate_")
    assert result.canonical_candidate.audit_information is not None
    assert result.canonical_candidate.audit_information.raw_record_count == 0
    assert result.decision_context.record_count == 0
    assert result.decision_context.decision_log == (
        "Received 0 candidate records.",
        "No sources detected.",
        "Workflow status: INCOMPLETE_PROFILE.",
        "No conflicts analyzed yet.",
    )


def test_candidate_intelligence_generates_structured_decision_log() -> None:
    """Decision logs are audit artifacts, not hidden reasoning."""
    result = CandidateIntelligenceAgent().process(
        [raw_record("github", payload={"profile": {"name": "The Octocat"}})]
    )

    decision = result.canonical_candidate.decision_logs[0]
    assert decision.field_path == "identity.full_name"
    assert decision.selected_value == "The Octocat"
    assert "Observation: full_name present in GitHub." in decision.reason
    assert "Reason: Single explicit value detected." in decision.reason
    assert "Rule Applied:" in decision.reason
    assert "Decision: Selected GitHub value." in decision.reason
    assert "Affected Field: full_name." in decision.reason
    assert "Structured decisions generated: 1." in result.decision_context.decision_log


def test_decision_context_is_immutable() -> None:
    """DecisionContext is stable for later orchestration stages."""
    context = CandidateIntelligenceAgent().process([]).decision_context

    with pytest.raises(PydanticValidationError):
        context.record_count = 1


def test_candidate_intelligence_generates_stable_uuid5_ids() -> None:
    """Stable IDs repeat for identical inputs and do not depend on list indexes."""
    record = raw_record(
        "resume",
        source_type=DomainSourceType.RESUME,
        payload={
            "full_name": "Ada Lovelace",
            "email": "ada@example.com",
            "skills": ["Python"],
            "education": [{"institution": "University", "degree": "BS"}],
            "experience": [{"title": "Engineer", "company": "Analytical"}],
        },
    )

    first = CandidateIntelligenceAgent().process([record]).canonical_candidate
    second = CandidateIntelligenceAgent().process([record]).canonical_candidate

    assert first.candidate_id == second.candidate_id
    assert first.skills[0].skill_id == second.skills[0].skill_id
    assert first.education[0].education_id == second.education[0].education_id
    assert first.experiences[0].experience_id == second.experiences[0].experience_id
    assert first.candidate_id.startswith("candidate_")
    assert first.skills[0].skill_id.startswith("skill_")
    assert first.skills[0].skill_id != "skill_1"


def test_candidate_intelligence_workflow_status_requires_review_for_conflicts() -> None:
    """Conflicting scalar values require human review deterministically."""
    result = CandidateIntelligenceAgent().process(
        [
            raw_record("github", payload={"profile": {"email": "github@example.com"}}),
            raw_record(
                "resume",
                source_type=DomainSourceType.RESUME,
                payload={"email": "resume@example.com"},
            ),
        ]
    )

    assert (
        result.decision_context.workflow_status == WorkflowStatus.REQUIRES_HUMAN_REVIEW
    )


def test_candidate_intelligence_workflow_status_marks_incomplete_profile() -> None:
    """Missing required observations mark the profile incomplete."""
    result = CandidateIntelligenceAgent().process(
        [
            raw_record(
                "resume",
                source_type=DomainSourceType.RESUME,
                payload={"email": "a@b.co"},
            )
        ]
    )

    assert result.decision_context.workflow_status == WorkflowStatus.INCOMPLETE_PROFILE


def test_candidate_intelligence_workflow_status_ready_for_complete_profile() -> None:
    """Complete, non-conflicting observations are ready for presentation."""
    result = CandidateIntelligenceAgent().process(
        [
            raw_record(
                "ats",
                source_type=DomainSourceType.ATS,
                payload={
                    "full_name": "Ada Lovelace",
                    "email": "ada@example.com",
                    "phone": "+15551234567",
                    "skills": ["Python"],
                    "education": [{"institution": "University", "degree": "BS"}],
                    "experience": [{"title": "Engineer", "company": "Analytical"}],
                    "certifications": ["Example Cert"],
                },
            )
        ]
    )

    assert (
        result.decision_context.workflow_status == WorkflowStatus.READY_FOR_PRESENTATION
    )
    assert (
        "Workflow status: READY_FOR_PRESENTATION."
        in result.decision_context.decision_log
    )


def _complete_intelligence_result() -> IntelligenceResult:
    """Create a complete deterministic candidate for presentation tests."""
    return CandidateIntelligenceAgent().process(
        [
            raw_record(
                "ats",
                source_type=DomainSourceType.ATS,
                payload={
                    "full_name": "Ada Lovelace",
                    "email": "ada@example.com",
                    "phone": "+15551234567",
                    "location": "London",
                    "summary": "Computing pioneer",
                    "skills": ["Python"],
                    "education": [{"institution": "University", "degree": "BS"}],
                    "experience": [{"title": "Engineer", "company": "Analytical"}],
                    "certifications": ["Example Cert"],
                },
            )
        ]
    )


def test_presentation_agent_builds_recruiter_projection() -> None:
    """Recruiter view presents concise candidate and readiness information."""
    result = PresentationAgent().present(_complete_intelligence_result())
    recruiter = result.projections["recruiter"]

    assert recruiter["full_name"] == "Ada Lovelace"
    assert recruiter["email"] == "ada@example.com"
    assert recruiter["phone"] == "+15551234567"
    assert recruiter["skills"] == ["Python"]
    assert recruiter["experience_count"] == 1
    assert recruiter["education_count"] == 1


def test_presentation_agent_builds_hr_projection() -> None:
    """HR view presents contact, source, education, and experience details."""
    result = PresentationAgent().present(_complete_intelligence_result())
    hr_view = result.projections["hr"]

    assert hr_view["sources"] == ["ATS"]
    assert hr_view["education"] == [
        {
            "institution": "University",
            "credential": "BS",
            "field_of_study": None,
        }
    ]
    assert hr_view["experience"] == [
        {"title": "Engineer", "organization": "Analytical", "is_current": False}
    ]


def test_presentation_agent_builds_engineering_projection() -> None:
    """Engineering view presents explicit technical evidence without inference."""
    intelligence = CandidateIntelligenceAgent().process(
        [
            raw_record(
                "github",
                payload={
                    "profile": {
                        "name": "The Octocat",
                        "html_url": "https://github.com/octocat",
                    },
                    "skills": ["Python"],
                },
            )
        ]
    )
    engineering = PresentationAgent().present(intelligence).projections["engineering"]

    assert engineering["skills"] == [
        {"name": "Python", "category": None, "evidence_count": 0}
    ]
    assert engineering["github_profile"] == "https://github.com/octocat"
    assert engineering["confidence"] == 0.80


def test_presentation_agent_generates_warnings_without_modifying_candidate() -> None:
    """Presentation validation reports omissions and preserves candidate data."""
    intelligence = CandidateIntelligenceAgent().process([])
    result = PresentationAgent().present(intelligence)

    assert result.candidate == intelligence.canonical_candidate
    assert result.warnings == (
        "missing name",
        "missing email",
        "missing phone",
        "incomplete profile",
    )


def test_presentation_agent_generates_summary() -> None:
    """Summary reflects existing intelligence artifacts without new reasoning."""
    result = PresentationAgent().present(_complete_intelligence_result())

    assert result.summary.workflow_status == WorkflowStatus.READY_FOR_PRESENTATION
    assert result.summary.candidate_confidence == 0.95
    assert result.summary.sources == ("ATS",)
    assert result.summary.decision_count == len(result.candidate.decision_logs)
    assert result.summary.missing_fields == ()
    assert result.summary.conflicting_fields == ()
    assert result.summary.presentation_warnings == ()


def test_presentation_agent_returns_export_model() -> None:
    """PresentationResult is deterministic and JSON serializable."""
    intelligence = _complete_intelligence_result()
    first = PresentationAgent().present(intelligence)
    second = PresentationAgent().present(intelligence)

    assert isinstance(first, PresentationResult)
    assert first == second
    assert first.decision_context == intelligence.decision_context
    assert tuple(first.projections) == ("recruiter", "hr", "engineering")
    assert first.metadata["projection_version"] == "presentation_v1"
    assert first.model_dump(mode="json")["candidate"]["candidate_id"]


def test_presentation_agent_rejects_non_intelligence_input() -> None:
    """PresentationAgent accepts only the completed intelligence contract."""
    with pytest.raises(TypeError, match="IntelligenceResult"):
        PresentationAgent().present({"candidate": "invalid"})


def test_agent_orchestrator_coordinates_agent_execution_flow() -> None:
    """Orchestrator delegates intake, intelligence, and presentation in order."""
    intake_agent = RecordingIntakeAgent()
    intelligence_agent = RecordingIntelligenceAgent()
    presentation_agent = RecordingPresentationAgent()
    orchestrator = AgentOrchestrator(
        intake_agent=intake_agent,
        intelligence_agent=intelligence_agent,
        presentation_agent=presentation_agent,
    )

    result = orchestrator.run(["artifact"])

    assert intake_agent.received == ["artifact"]
    assert intelligence_agent.received is not None
    assert [record.record_id for record in intelligence_agent.received] == ["intake"]
    assert isinstance(presentation_agent.received, IntelligenceResult)
    assert isinstance(result, PresentationResult)
    assert isinstance(presentation_agent.received, IntelligenceResult)
    assert result.candidate == presentation_agent.received.canonical_candidate
