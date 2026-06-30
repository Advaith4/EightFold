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
    PresentationAgent,
)
from src.enums import SourceType as InfrastructureSourceType
from src.github import GitHubAdapter, GitHubFetcher, GitHubPayload
from src.interfaces import BaseAdapter
from src.loaders import FileMetadata, FilePayload
from src.models import PayloadFormat, RawCandidateRecord
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

    def analyze(self, raw_records: list[RawCandidateRecord]) -> DecisionContext:
        self.received = raw_records
        return DecisionContext(
            record_count=len(raw_records),
            detected_sources=("test",),
            duplicate_sources=(),
            missing_important_fields=(),
            available_fields_by_source={"test": ("record_id",)},
            decision_log=("test context",),
        )


class RecordingPresentationAgent(PresentationAgent):
    """Test presentation agent recording output."""

    def __init__(self) -> None:
        self.received: object | None = None

    def present(self, candidate_output: object) -> object:
        self.received = candidate_output
        return {"presented": candidate_output}


def test_agents_construct_with_default_dependencies() -> None:
    """Sprint 6.0 agents expose clean public constructors."""
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


def test_candidate_intelligence_agent_analyzes_single_source() -> None:
    """Single-source analysis reports source, count, fields, and missing data."""
    context = CandidateIntelligenceAgent().analyze(
        [
            raw_record(
                "github",
                payload={
                    "profile": {"login": "octocat"},
                    "repositories": [],
                    "languages": {},
                },
            )
        ]
    )

    assert isinstance(context, DecisionContext)
    assert context.record_count == 1
    assert context.detected_sources == ("GitHub",)
    assert context.duplicate_sources == ()
    assert context.available_fields_by_source["GitHub"] == (
        "languages",
        "profile",
        "repositories",
    )
    assert "certifications" in context.missing_important_fields


def test_candidate_intelligence_agent_analyzes_multiple_sources() -> None:
    """Multiple-source analysis preserves source order and field observations."""
    context = CandidateIntelligenceAgent().analyze(
        [
            raw_record("github", payload={"profile": {}, "repositories": []}),
            raw_record(
                "resume",
                source_type=DomainSourceType.RESUME,
                payload={"email": "ada@example.com", "phone": "+15551234567"},
                raw_text="Ada Lovelace",
            ),
        ]
    )

    assert context.record_count == 2
    assert context.detected_sources == ("GitHub", "Resume")
    assert context.available_fields_by_source["Resume"] == (
        "email",
        "phone",
        "raw_text",
    )


def test_candidate_intelligence_agent_reports_missing_important_fields() -> None:
    """Missing important fields are deterministic observations only."""
    context = CandidateIntelligenceAgent().analyze(
        [
            raw_record(
                "resume",
                source_type=DomainSourceType.RESUME,
                payload={"email": "a@b.co"},
            )
        ]
    )

    assert context.missing_important_fields == (
        "phone",
        "education",
        "experience",
        "skills",
        "certifications",
    )


def test_candidate_intelligence_agent_detects_duplicate_sources() -> None:
    """Duplicate source labels are reported without merge decisions."""
    context = CandidateIntelligenceAgent().analyze(
        [raw_record("github-1"), raw_record("github-2")]
    )

    assert context.record_count == 2
    assert context.detected_sources == ("GitHub",)
    assert context.duplicate_sources == ("GitHub",)
    assert "Duplicate sources detected: GitHub" in context.decision_log


def test_candidate_intelligence_agent_handles_empty_input() -> None:
    """Empty input yields an explainable empty decision context."""
    context = CandidateIntelligenceAgent().analyze([])

    assert context.record_count == 0
    assert context.detected_sources == ()
    assert context.duplicate_sources == ()
    assert context.available_fields_by_source == {}
    assert context.decision_log == (
        "Received 0 candidate records.",
        "No sources detected.",
        "No conflicts analyzed yet.",
    )


def test_candidate_intelligence_agent_generates_decision_log() -> None:
    """Decision log contains observations and avoids conflict resolution."""
    context = CandidateIntelligenceAgent().analyze(
        [raw_record("github", payload={"profile": {}, "languages": {}})]
    )

    assert "Received sources: GitHub" in context.decision_log
    assert "GitHub contains: languages, profile." in context.decision_log
    assert context.decision_log[-1] == "No conflicts analyzed yet."


def test_decision_context_is_immutable() -> None:
    """DecisionContext is stable for later orchestration stages."""
    context = CandidateIntelligenceAgent().analyze([])

    with pytest.raises(PydanticValidationError):
        context.record_count = 1


def test_presentation_agent_returns_supplied_object_unchanged() -> None:
    """Presentation shell performs no projection or validation this sprint."""
    value = {"candidate": "future"}

    assert PresentationAgent().present(value) is value


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
    assert isinstance(presentation_agent.received, DecisionContext)
    assert result == {"presented": presentation_agent.received}
