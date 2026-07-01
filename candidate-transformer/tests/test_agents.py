"""Multi-agent orchestration layer tests."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError as PydanticValidationError
from src.adapters import (
    AdapterRegistry,
    ATSJsonAdapter,
    RecruiterCSVAdapter,
    ResumeFileAdapter,
)
from src.agents import (
    AgentOrchestrator,
    CandidateGroup,
    CandidateIntelligenceAgent,
    DecisionContext,
    DuplicateDetectionAgent,
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


def test_intake_agent_processes_multiple_github_urls_and_skips_invalid() -> None:
    """Multiple GitHub URLs produce records while invalid inputs are collected."""
    fetcher = FakeGitHubFetcher()
    adapter = FakeGitHubAdapter()
    agent = IntakeAgent(github_fetcher=fetcher, github_adapter=adapter)

    records = agent.process(["https://github.com/octocat", "not-a-real-file"])

    assert [record.record_id for record in records] == ["github"]
    assert fetcher.requested_url == "https://github.com/octocat"
    assert agent.errors


def test_intake_agent_processes_multiple_resume_payloads() -> None:
    """Every resume file payload produces an independent raw record."""
    registry = AdapterRegistry()
    registry.register(ResumeFileAdapter())
    agent = IntakeAgent(adapter_registry=registry)
    payloads = [
        FilePayload(
            text="Ada Lovelace\nPython",
            metadata=FileMetadata(
                filename="resume-one.pdf",
                content_type="application/pdf",
                extension=".pdf",
                size_bytes=19,
                checksum="sha256:resume-one",
            ),
        ),
        FilePayload(
            text="Grace Hopper\nCOBOL",
            metadata=FileMetadata(
                filename="resume-two.docx",
                content_type=(
                    "application/vnd.openxmlformats-officedocument"
                    ".wordprocessingml.document"
                ),
                extension=".docx",
                size_bytes=18,
                checksum="sha256:resume-two",
            ),
        ),
    ]

    records = agent.process(payloads)

    assert [record.source_type for record in records] == [
        DomainSourceType.RESUME,
        DomainSourceType.RESUME,
    ]
    assert len(records) == 2


def test_intake_agent_processes_recruiter_csv_rows() -> None:
    """Every recruiter CSV row becomes a raw candidate record."""
    registry = AdapterRegistry()
    registry.register(RecruiterCSVAdapter())
    payload = FilePayload(
        text="full_name,email\nAda,ada@example.com\nGrace,grace@example.com\n",
        metadata=FileMetadata(
            filename="candidates.csv",
            content_type="text/csv",
            extension=".csv",
            size_bytes=58,
            checksum="sha256:csv-many",
        ),
    )
    agent = IntakeAgent(adapter_registry=registry)

    records = agent.process(payload)

    assert [record.payload["email"] for record in records] == [
        "ada@example.com",
        "grace@example.com",
    ]
    assert [record.source_record_id for record in records] == [
        "candidates.csv#1",
        "candidates.csv#2",
    ]


def test_intake_agent_processes_ats_json_object_and_array() -> None:
    """ATS JSON object and array formats produce raw candidate records."""
    registry = AdapterRegistry()
    registry.register(ATSJsonAdapter())
    object_payload = FilePayload(
        text='{"email":"ada@example.com"}',
        metadata=FileMetadata(
            filename="candidate.json",
            content_type="application/json",
            extension=".json",
            size_bytes=27,
            checksum="sha256:ats-one",
        ),
    )
    array_payload = FilePayload(
        text='[{"email":"grace@example.com"},{"email":"katherine@example.com"}]',
        metadata=FileMetadata(
            filename="candidates.json",
            content_type="application/json",
            extension=".json",
            size_bytes=65,
            checksum="sha256:ats-many",
        ),
    )
    agent = IntakeAgent(adapter_registry=registry)

    records = agent.process([object_payload, array_payload])

    assert [record.payload["email"] for record in records] == [
        "ada@example.com",
        "grace@example.com",
        "katherine@example.com",
    ]


def test_intake_agent_skips_malformed_ats_array_items() -> None:
    """Malformed ATS array entries are skipped without aborting the file."""
    registry = AdapterRegistry()
    registry.register(ATSJsonAdapter())
    payload = FilePayload(
        text='[{"email":"ada@example.com"}, null, "bad", {}]',
        metadata=FileMetadata(
            filename="candidates.json",
            content_type="application/json",
            extension=".json",
            size_bytes=45,
            checksum="sha256:ats-partial",
        ),
    )
    agent = IntakeAgent(adapter_registry=registry)

    records = agent.process(payload)

    assert [record.payload["email"] for record in records] == ["ada@example.com"]


def test_intake_agent_continues_after_partial_file_failure() -> None:
    """One failed artifact does not stop later valid artifacts."""
    registry = AdapterRegistry()
    registry.register(RecruiterCSVAdapter())
    payload = FilePayload(
        text="full_name,email\nAda,ada@example.com\n",
        metadata=FileMetadata(
            filename="candidates.csv",
            content_type="text/csv",
            extension=".csv",
            size_bytes=37,
            checksum="sha256:csv-valid",
        ),
    )
    agent = IntakeAgent(adapter_registry=registry)

    records = agent.process(["missing.unknown", payload])

    assert [record.payload["email"] for record in records] == ["ada@example.com"]
    assert agent.errors


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
                    "languages": {"octocat/hello-world": {"Python": 100}},
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
    assert [skill.name for skill in result.canonical_candidate.skills] == ["Python"]


def test_duplicate_detection_matches_same_email() -> None:
    """Exact normalized email joins records into one group."""
    groups = DuplicateDetectionAgent().process(
        [
            raw_record(
                "resume",
                source_type=DomainSourceType.RESUME,
                payload={"email": " ADA@example.com "},
            ),
            raw_record(
                "ats",
                source_type=DomainSourceType.ATS,
                payload={"email": "ada@example.com"},
            ),
        ]
    )

    assert len(groups) == 1
    assert groups[0].matching_rule == "Exact Email Match"
    assert groups[0].matched_fields == ("email",)
    assert groups[0].source_types == ("Resume", "ATS")
    assert "email:ada@example.com" in groups[0].match_keys
    assert "Rule: Exact Email Match" in groups[0].grouping_decisions[0]


def test_duplicate_detection_matches_same_phone() -> None:
    """Exact normalized phone joins records into one group."""
    groups = DuplicateDetectionAgent().process(
        [
            raw_record("resume", payload={"phone": "+1 (555) 123-4567"}),
            raw_record(
                "csv",
                source_type=DomainSourceType.CSV,
                payload={"phone": "5551234567"},
            ),
        ]
    )

    assert len(groups) == 1
    assert groups[0].matching_rule == "Exact Phone Match"
    assert groups[0].matched_fields == ("phone",)


def test_duplicate_detection_matches_same_github_profile() -> None:
    """GitHub username and profile URL join records into one group."""
    groups = DuplicateDetectionAgent().process(
        [
            raw_record(
                "resume",
                source_type=DomainSourceType.RESUME,
                payload={"github_url": "https://github.com/OctoCat/"},
            ),
            raw_record(
                "github",
                source_type=DomainSourceType.GITHUB,
                payload={"profile": {"login": "octocat"}},
            ),
        ]
    )

    assert len(groups) == 1
    assert groups[0].matching_rule == "GitHub Profile Match"
    assert groups[0].matched_fields == ("github",)


def test_duplicate_detection_matches_same_ats_candidate_id() -> None:
    """ATS candidate IDs join ATS records into one group."""
    groups = DuplicateDetectionAgent().process(
        [
            raw_record(
                "ats-1",
                source_type=DomainSourceType.ATS,
                payload={"candidate_id": "ATS-123"},
            ),
            raw_record(
                "ats-2",
                source_type=DomainSourceType.ATS,
                payload={"candidate_id": " ats-123 "},
            ),
        ]
    )

    assert len(groups) == 1
    assert groups[0].matching_rule == "ATS Candidate ID"
    assert groups[0].matched_fields == ("ats_candidate_id",)


def test_duplicate_detection_matches_name_and_organization() -> None:
    """Name plus organization joins records without contact identifiers."""
    groups = DuplicateDetectionAgent().process(
        [
            raw_record(
                "resume",
                payload={
                    "full_name": "Ada Lovelace",
                    "experience": [{"organization": "Analytical Engines"}],
                },
            ),
            raw_record(
                "csv",
                source_type=DomainSourceType.CSV,
                payload={
                    "name": " ada   lovelace ",
                    "company": "Analytical Engines",
                },
            ),
        ]
    )

    assert len(groups) == 1
    assert groups[0].matching_rule == "Name + Organization"
    assert groups[0].matched_fields == ("name+organization",)


def test_duplicate_detection_matches_name_and_education() -> None:
    """Name plus institution joins records without contact identifiers."""
    groups = DuplicateDetectionAgent().process(
        [
            raw_record(
                "resume",
                payload={
                    "full_name": "Grace Hopper",
                    "education": [{"institution": "Yale University"}],
                },
            ),
            raw_record(
                "ats",
                source_type=DomainSourceType.ATS,
                payload={
                    "full_name": "Grace Hopper",
                    "education": [{"school": "yale university"}],
                },
            ),
        ]
    )

    assert len(groups) == 1
    assert groups[0].matching_rule == "Name + Educational Institution"
    assert groups[0].matched_fields == ("name+education",)


def test_duplicate_detection_keeps_different_candidates_separate() -> None:
    """Records without matching identity signals stay in separate groups."""
    groups = DuplicateDetectionAgent().process(
        [
            raw_record("one", payload={"email": "one@example.com"}),
            raw_record("two", payload={"email": "two@example.com"}),
        ]
    )

    assert len(groups) == 2
    assert [group.matching_rule for group in groups] == ["No Match", "No Match"]


def test_duplicate_detection_handles_empty_and_missing_fields() -> None:
    """Empty input and missing identity fields remain deterministic."""
    agent = DuplicateDetectionAgent()

    assert agent.process([]) == []
    groups = agent.process(
        [
            raw_record("one", payload={"record_id": "one"}),
            raw_record("two", payload={"record_id": "two"}),
        ]
    )

    assert len(groups) == 2
    assert groups[0].matched_fields == ()


def test_candidate_intelligence_uses_duplicate_detection_groups() -> None:
    """Candidate intelligence now consumes detector-created groups."""
    result = CandidateIntelligenceAgent().process(
        [
            raw_record(
                "resume",
                source_type=DomainSourceType.RESUME,
                payload={"full_name": "Ada Lovelace", "email": "ada@example.com"},
            ),
            raw_record(
                "ats",
                source_type=DomainSourceType.ATS,
                payload={"full_name": "Ada Lovelace", "email": "ada@example.com"},
            ),
            raw_record(
                "csv",
                source_type=DomainSourceType.CSV,
                payload={"full_name": "Grace Hopper", "email": "grace@example.com"},
            ),
        ]
    )

    assert len(result.candidate_groups) == 2
    assert len(result.canonical_candidates) == 2
    assert result.candidate_groups[0].matching_rule == "Exact Email Match"
    assert [record.record_id for record in result.candidate_groups[0].records] == [
        "resume",
        "ats",
    ]


def test_candidate_intelligence_groups_records_by_duplicate_detection() -> None:
    """Sprint 1.3 groups records using deterministic duplicate detection."""
    result = CandidateIntelligenceAgent().process(
        [
            raw_record(
                "resume",
                source_type=DomainSourceType.RESUME,
                payload={"full_name": "Ada Lovelace", "email": "ada@example.com"},
            ),
            raw_record(
                "github",
                payload={
                    "profile": {
                        "login": "ada",
                        "name": "Ada Lovelace",
                        "email": "ada@example.com",
                    },
                    "languages": {"ada/project": {"Python": 100}},
                },
            ),
        ]
    )

    assert len(result.candidate_groups) == 1
    assert isinstance(result.candidate_groups[0], CandidateGroup)
    assert [record.record_id for record in result.candidate_groups[0].records] == [
        "resume",
        "github",
    ]
    assert result.candidate_groups[0].matching_rule == "Exact Email Match"
    assert result.candidate_groups[0].matched_fields == ("email",)
    assert len(result.canonical_candidates) == 1
    assert result.selected_candidate == result.canonical_candidates[0]
    assert result.canonical_candidate == result.selected_candidate


def test_candidate_intelligence_returns_canonical_candidate_per_group() -> None:
    """Every compatibility group produces a canonical candidate."""
    result = CandidateIntelligenceAgent().process(
        [
            raw_record(
                "one",
                source_type=DomainSourceType.RESUME,
                payload={"full_name": "Ada Lovelace", "email": "ada@example.com"},
            ),
            raw_record(
                "two",
                source_type=DomainSourceType.ATS,
                payload={"full_name": "Grace Hopper", "email": "grace@example.com"},
            ),
        ]
    )

    assert len(result.candidate_groups) == 2
    assert len(result.canonical_candidates) == 2
    assert [
        candidate.identity.full_name for candidate in result.canonical_candidates
    ] == ["Ada Lovelace", "Grace Hopper"]


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
    assert candidate.confidence.score == pytest.approx(0.96)


@pytest.mark.parametrize(
    ("sources", "expected_score"),
    [
        ((DomainSourceType.ATS,), 0.95),
        ((DomainSourceType.RESUME,), 0.85),
        ((DomainSourceType.GITHUB,), 0.80),
        ((DomainSourceType.RESUME, DomainSourceType.ATS), 0.85),
        ((DomainSourceType.RESUME, DomainSourceType.GITHUB), 0.85),
        ((DomainSourceType.ATS, DomainSourceType.GITHUB), 0.95),
        (
            (DomainSourceType.RESUME, DomainSourceType.ATS, DomainSourceType.GITHUB),
            0.85,
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
            payload={
                "email": f"candidate{index}@example.com",
                "experiences": [{"organization": f"Dummy Corp {index}"}],
                "education": [{"institution": f"Dummy U {index}"}],
                "skills": ["Dummy Skill"],
            },
        )
        for index, source in enumerate(sources)
    ]

    result = CandidateIntelligenceAgent().process(records)
    bonus = 0.11
    expected = min(0.99, max(0.0, expected_score + bonus))

    assert result.selected_candidate.confidence.score == pytest.approx(expected)
    assert result.canonical_candidates[0].confidence.score == pytest.approx(expected)


def test_candidate_intelligence_explains_confidence_score_formula() -> None:
    """Candidate-level confidence includes deterministic score arithmetic."""
    result = CandidateIntelligenceAgent().process(
        [
            raw_record(
                "ats",
                source_type=DomainSourceType.ATS,
                payload={
                    "email": "ada@example.com",
                    "experiences": [{"organization": "Analytical Engines"}],
                    "education": [{"institution": "Dummy U"}],
                    "skills": ["Python"],
                },
            )
        ]
    )

    reasons = result.canonical_candidate.confidence.reasons

    assert result.canonical_candidate.confidence.score == pytest.approx(0.99)
    assert "Sources counted in this candidate: ATS." in reasons
    assert (
        "Base source reliability uses strongest counted source: 95% from ATS."
        in reasons
    )
    assert "Experience entries present: +5%." in reasons
    assert "Education entries present: +5%." in reasons
    assert "Skills present: +1%." in reasons
    assert "Final confidence: 99% = 95% +5% +5% +1% capped at 99%." in reasons


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
                payload={
                    "email": "ada@example.com",
                    "experiences": [{"organization": "Dummy Corp"}],
                    "education": [{"institution": "Dummy U"}],
                    "skills": ["Dummy Skill"],
                },
            )
        ]
    )

    assert result.canonical_candidate.confidence.score == pytest.approx(0.53)
    assert (
        result.canonical_candidate.confidence.method == "Dynamic Completeness Scoring"
    )


def test_candidate_intelligence_preserves_multiple_unmerged_candidates() -> None:
    """Sprint 1.2 carries each candidate forward without cross-group merging."""
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

    assert len(result.canonical_candidates) == 3
    assert (
        result.selected_candidate.contact_info.preferred_email == "github@example.com"
    )
    assert [
        candidate.contact_info.preferred_email
        for candidate in result.canonical_candidates
    ] == ["github@example.com", "resume@example.com", "ats@example.com"]
    assert result.decision_context.conflicting_fields == ()


def test_candidate_intelligence_selected_candidate_remains_first_group() -> None:
    """Backward compatibility keeps the first canonical candidate selected."""
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

    assert result.selected_candidate == result.canonical_candidates[0]
    assert result.canonical_candidate == result.selected_candidate
    assert result.selected_candidate.contact_info.preferred_phone == "+10000000001"
    assert result.canonical_candidates[1].contact_info.preferred_phone == "+10000000002"
    assert result.decision_context.conflicting_fields == ()


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


def test_candidate_intelligence_records_duplicate_sources_after_grouping() -> None:
    """Duplicate source observations remain explicit after grouping."""
    result = CandidateIntelligenceAgent().process(
        [
            raw_record("same", payload={"email": "one@example.com"}),
            raw_record("same", payload={"email": "two@example.com"}),
        ]
    )

    assert len(result.candidate_groups) == 1
    assert len(result.canonical_candidates) == 1
    assert result.candidate_groups[0].matching_rule == "GitHub Profile Match"
    assert result.decision_context.duplicate_sources == ("GitHub",)
    assert result.decision_context.duplicate_record_ids == ("same",)


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


def test_candidate_intelligence_defers_cross_group_conflict_review() -> None:
    """Cross-record conflict review waits for the duplicate detection stage."""
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

    assert result.decision_context.conflicting_fields == ()
    assert result.decision_context.workflow_status == WorkflowStatus.INCOMPLETE_PROFILE


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
    recruiter = result.recruiter_projection

    assert recruiter.identity["Name"] == "Ada Lovelace"
    assert recruiter.contact["Primary Email"] == "ada@example.com"
    assert recruiter.skills == ["Python"]
    assert recruiter.experience_summary == "1 previous roles detected"


def test_presentation_agent_builds_hr_projection() -> None:
    """HR view presents contact, source, education, and experience details."""
    result = PresentationAgent().present(_complete_intelligence_result())
    hr_view = result.hr_projection

    assert hr_view.sources == ["ATS"]
    assert hr_view.provenance_summary == "Deterministic Merge"
    assert "Added via ATS" in hr_view.candidate_timeline[0]


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
    engineering = PresentationAgent().present(intelligence).engineering_projection

    assert engineering.raw_sources == ["GitHub"]
    assert "0.4" in engineering.confidence_details


def test_presentation_agent_generates_warnings_without_modifying_candidate() -> None:
    """Presentation validation reports omissions and preserves candidate data."""
    intelligence = CandidateIntelligenceAgent().process([])
    result = PresentationAgent().present(intelligence)

    assert result.header.name == "Unknown Candidate"
    assert "full_name" in result.missing_fields
    assert "phone" in result.missing_fields


def test_presentation_agent_generates_summary() -> None:
    """Summary reflects existing intelligence artifacts without new reasoning."""
    result = PresentationAgent().present(_complete_intelligence_result())

    assert result.header.workflow_status == "Ready For Review"
    assert result.confidence.overall_score == "99%"
    assert result.header.sources_used == ["ATS"]
    assert result.missing_fields == []
    assert result.conflicting_fields == []


def test_presentation_agent_returns_export_model() -> None:
    """PresentationResult is deterministic and JSON serializable."""
    intelligence = _complete_intelligence_result()
    first = PresentationAgent().present(intelligence)
    second = PresentationAgent().present(intelligence)

    assert isinstance(first, PresentationResult)
    assert first == second
    assert first.header.name == "Ada Lovelace"
    assert first.model_dump(mode="json")["header"]["name"] == "Ada Lovelace"


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


