"""Application service tests for end-to-end candidate processing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from src.agents import (
    AgentOrchestrator,
    CandidateIntelligenceAgent,
    PresentationAgent,
    PresentationResult,
)
from src.loaders import CorruptedFileError, FileMetadata, FilePayload
from src.models import PayloadFormat, RawCandidateRecord
from src.models.base import JsonValue
from src.models.enums import SourceType
from src.services import CandidateProcessingService


def raw_record(
    record_id: str = "record",
    *,
    source_type: SourceType = SourceType.RESUME,
    payload: dict[str, JsonValue] | None = None,
) -> RawCandidateRecord:
    """Create a deterministic raw candidate record for service tests."""
    return RawCandidateRecord(
        record_id=record_id,
        source_type=source_type,
        source_system=source_type.value,
        source_record_id=record_id,
        payload_format=PayloadFormat.JSON_DOCUMENT,
        payload=payload or {"full_name": "Ada Lovelace"},
        checksum=f"sha256:{record_id}",
    )


def presentation_result(
    source_type: SourceType = SourceType.RESUME,
) -> PresentationResult:
    """Create a real presentation result without exercising intake."""
    intelligence = CandidateIntelligenceAgent().process(
        [
            raw_record(
                "candidate",
                source_type=source_type,
                payload={
                    "full_name": "Ada Lovelace",
                    "email": "ada@example.com",
                    "phone": "+15551234567",
                    "skills": ["Python"],
                    "education": [{"institution": "University"}],
                    "experience": [{"title": "Engineer"}],
                    "certifications": ["Example Cert"],
                },
            )
        ]
    )
    return PresentationAgent().present(intelligence)


def file_payload(extension: str, filename: str) -> FilePayload:
    """Create a loaded payload with the requested file extension."""
    return FilePayload(
        text="full_name,email\nAda Lovelace,ada@example.com\n",
        metadata=FileMetadata(
            filename=filename,
            content_type="text/plain",
            extension=extension,
            size_bytes=43,
            checksum=f"sha256:{filename}",
        ),
    )


class RecordingOrchestrator(AgentOrchestrator):
    """Record artifacts and return a known presentation result."""

    def __init__(self, result: PresentationResult | None = None) -> None:
        self.received: object | None = None
        self._result = result or presentation_result()

    def run(self, artifacts: object) -> object:
        self.received = artifacts
        return self._result


class FailingOrchestrator(AgentOrchestrator):
    """Raise an existing lower-layer exception for propagation tests."""

    def __init__(self, error: Exception) -> None:
        self._error = error

    def run(self, artifacts: object) -> object:
        del artifacts
        raise self._error


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"resume_pdf": Path("resume.pdf")}, [Path("resume.pdf")]),
        ({"github_url": "https://github.com/octocat"}, ["https://github.com/octocat"]),
        (
            {
                "resume_pdf": Path("resume.pdf"),
                "github_url": "https://github.com/octocat",
            },
            [Path("resume.pdf"), "https://github.com/octocat"],
        ),
        ({"ats_json": Path("candidate.json")}, [Path("candidate.json")]),
        (
            {
                "resume_docx": Path("resume.docx"),
                "ats_json": Path("candidate.json"),
            },
            [Path("resume.docx"), Path("candidate.json")],
        ),
        (
            {
                "resume_pdf": Path("resume.pdf"),
                "ats_json": Path("candidate.json"),
                "github_url": "https://github.com/octocat",
            },
            [Path("resume.pdf"), Path("candidate.json"), "https://github.com/octocat"],
        ),
    ],
)
def test_candidate_processing_service_routes_supported_input_combinations(
    kwargs: dict[str, Any], expected: list[object]
) -> None:
    """The service normalizes public inputs before invoking the orchestrator."""
    orchestrator = RecordingOrchestrator()
    service = CandidateProcessingService(orchestrator=orchestrator)

    result = service.process_candidate(**kwargs)

    assert isinstance(result, PresentationResult)
    assert orchestrator.received == expected


def test_candidate_processing_service_supports_recruiter_csv() -> None:
    """Recruiter CSV input is accepted as one of the public source arguments."""
    orchestrator = RecordingOrchestrator()
    service = CandidateProcessingService(orchestrator=orchestrator)

    service.process_candidate(recruiter_csv=Path("recruiter.csv"))

    assert orchestrator.received == [Path("recruiter.csv")]


def test_candidate_processing_service_allows_no_inputs() -> None:
    """No supplied sources are still delegated as an empty candidate workflow."""
    orchestrator = RecordingOrchestrator(presentation_result(SourceType.ATS))
    service = CandidateProcessingService(orchestrator=orchestrator)

    result = service.process_candidate()

    assert orchestrator.received == []
    assert result.header.sources_used == ["ATS"]


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/octocat",
        "https://example.com/octocat",
        "https://github.com/octocat/hello-world",
        "https://github.com/settings",
        "",
    ],
)
def test_candidate_processing_service_skips_invalid_github_url(url: str) -> None:
    """Invalid GitHub URLs are skipped without aborting processing."""
    orchestrator = RecordingOrchestrator()
    service = CandidateProcessingService(orchestrator=orchestrator)

    result = service.process_candidate(github_url=url)

    assert isinstance(result, PresentationResult)
    assert orchestrator.received == []


def test_candidate_processing_service_delegates_resume_failures_to_intake() -> None:
    """Source-level failures are handled below the service aggregation boundary."""
    service = CandidateProcessingService(
        orchestrator=FailingOrchestrator(CorruptedFileError("PDF file is corrupted"))
    )

    with pytest.raises(CorruptedFileError, match="corrupted"):
        service.process_candidate(resume_pdf=Path("resume.pdf"))


def test_candidate_processing_service_skips_unsupported_file_type() -> None:
    """Unsupported file parameters are skipped before orchestration."""
    orchestrator = RecordingOrchestrator()
    service = CandidateProcessingService(orchestrator=orchestrator)

    result = service.process_candidate(resume_pdf=Path("resume.txt"))

    assert isinstance(result, PresentationResult)
    assert orchestrator.received == []


def test_candidate_processing_service_accepts_multiple_inputs() -> None:
    """The public service aggregates multiple supported source inputs."""
    orchestrator = RecordingOrchestrator()
    service = CandidateProcessingService(orchestrator=orchestrator)
    resume_payloads = [
        file_payload(".pdf", "one.pdf"),
        file_payload(".pdf", "two.pdf"),
    ]
    ats_payloads = [file_payload(".json", "one.json")]
    csv_payloads = [file_payload(".csv", "one.csv")]

    service.process_candidate(
        resume_pdf=resume_payloads,
        ats_json=ats_payloads,
        recruiter_csv=csv_payloads,
        github_url="https://github.com/octocat\nhttps://example.com/nope",
    )

    assert orchestrator.received == [
        resume_payloads[0],
        resume_payloads[1],
        ats_payloads[0],
        csv_payloads[0],
        "https://github.com/octocat",
    ]


def test_candidate_processing_service_accepts_loaded_payloads() -> None:
    """Preloaded payloads can be supplied by UI or API callers."""
    payload = file_payload(".json", "candidate.json")
    orchestrator = RecordingOrchestrator()
    service = CandidateProcessingService(orchestrator=orchestrator)

    service.process_candidate(ats_json=payload)

    assert orchestrator.received == [payload]


def test_candidate_processing_service_requires_presentation_result() -> None:
    """The service exposes exactly one result contract."""

    class InvalidOrchestrator(AgentOrchestrator):
        def run(self, artifacts: object) -> object:
            del artifacts
            return {"candidate": "invalid"}

    service = CandidateProcessingService(orchestrator=InvalidOrchestrator())

    with pytest.raises(TypeError, match="PresentationResult"):
        service.process_candidate()


def test_candidate_processing_service_default_runs_loaded_resume_payload() -> None:
    """Default service wiring can process loaded resume payloads."""
    payload = FilePayload(
        text="Ada Lovelace\nPython",
        metadata=FileMetadata(
            filename="resume.pdf",
            content_type="application/pdf",
            extension=".pdf",
            size_bytes=19,
            checksum="sha256:resume",
        ),
    )

    result = CandidateProcessingService().process_candidate(resume_pdf=payload)

    assert result.header.sources_used == ["Resume"]
    assert len(result.decision_log) > 0


def test_candidate_processing_service_default_runs_loaded_ats_payload() -> None:
    """Default service wiring can process loaded ATS JSON payloads."""
    payload = FilePayload(
        text='{"candidate":{"id":"ats-1"},"email":"ada@example.com"}',
        metadata=FileMetadata(
            filename="candidate.json",
            content_type="application/json",
            extension=".json",
            size_bytes=52,
            checksum="sha256:ats",
        ),
    )

    result = CandidateProcessingService().process_candidate(ats_json=payload)

    assert result.header.sources_used == ["ATS"]
    assert result.header.primary_email == "ada@example.com"


def test_candidate_processing_service_default_runs_loaded_recruiter_csv_payload() -> (
    None
):
    """Default service wiring can process loaded recruiter CSV payloads."""
    payload = FilePayload(
        text="full_name,email\nAda Lovelace,ada@example.com\n",
        metadata=FileMetadata(
            filename="recruiter.csv",
            content_type="text/csv",
            extension=".csv",
            size_bytes=43,
            checksum="sha256:csv",
        ),
    )

    result = CandidateProcessingService().process_candidate(recruiter_csv=payload)

    assert result.header.sources_used == ["CSV"]
    assert result.header.name == "Ada Lovelace"
