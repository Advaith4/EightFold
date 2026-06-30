"""Application service for end-to-end candidate processing."""

from __future__ import annotations

from pathlib import Path

from src.adapters import (
    AdapterRegistry,
    ATSJsonAdapter,
    RecruiterCSVAdapter,
    ResumeFileAdapter,
)
from src.agents import (
    AgentOrchestrator,
    CandidateArtifact,
    IntakeAgent,
    PresentationResult,
)
from src.detection import SourceDetector
from src.enums import SourceType
from src.exceptions import ValidationError
from src.loaders import (
    BaseLoader,
    CSVLoader,
    DOCXLoader,
    FilePayload,
    JSONLoader,
    PDFLoader,
    UploadedContent,
)
from src.services.container import ServiceContainer


class CandidateProcessingService:
    """Single application entry point for the candidate intelligence workflow."""

    _expected_extensions = {
        "resume_pdf": ".pdf",
        "resume_docx": ".docx",
        "ats_json": ".json",
        "recruiter_csv": ".csv",
    }

    def __init__(
        self,
        *,
        orchestrator: AgentOrchestrator | None = None,
        services: ServiceContainer | None = None,
        source_detector: SourceDetector | None = None,
    ) -> None:
        """Initialize the service with injectable orchestration dependencies."""
        self._source_detector = source_detector or SourceDetector()
        self._orchestrator = orchestrator or self._build_default_orchestrator(services)

    def process_candidate(
        self,
        *,
        resume_pdf: UploadedContent | FilePayload | None = None,
        resume_docx: UploadedContent | FilePayload | None = None,
        ats_json: UploadedContent | FilePayload | None = None,
        recruiter_csv: UploadedContent | FilePayload | None = None,
        github_url: str | None = None,
    ) -> PresentationResult:
        """Execute the full candidate intelligence workflow for supplied sources."""
        artifacts = self._collect_artifacts(
            resume_pdf=resume_pdf,
            resume_docx=resume_docx,
            ats_json=ats_json,
            recruiter_csv=recruiter_csv,
            github_url=github_url,
        )
        result = self._orchestrator.run(artifacts)
        if not isinstance(result, PresentationResult):
            raise TypeError("CandidateProcessingService requires a PresentationResult")
        return result

    def _collect_artifacts(
        self,
        *,
        resume_pdf: UploadedContent | FilePayload | None,
        resume_docx: UploadedContent | FilePayload | None,
        ats_json: UploadedContent | FilePayload | None,
        recruiter_csv: UploadedContent | FilePayload | None,
        github_url: str | None,
    ) -> list[CandidateArtifact]:
        artifacts: list[CandidateArtifact] = []
        file_inputs = {
            "resume_pdf": resume_pdf,
            "resume_docx": resume_docx,
            "ats_json": ats_json,
            "recruiter_csv": recruiter_csv,
        }
        for name, value in file_inputs.items():
            if value is None:
                continue
            self._validate_file_input(name, value)
            artifacts.append(value)
        if github_url is not None:
            github_url = github_url.strip()
            if github_url:
                if not github_url.startswith("http") and "github.com" not in github_url:
                    github_url = f"https://github.com/{github_url}"
                elif not github_url.startswith("http"):
                    github_url = f"https://{github_url}"
            self._validate_github_url(github_url)
            artifacts.append(github_url)
        return artifacts

    def _validate_file_input(
        self, name: str, value: UploadedContent | FilePayload
    ) -> None:
        expected_extension = self._expected_extensions[name]
        actual_extension = self._extension_for(value)
        if actual_extension != expected_extension:
            raise ValidationError(
                f"{name} requires a {expected_extension} file, "
                f"received {actual_extension or 'unknown'}"
            )

    def _extension_for(self, value: UploadedContent | FilePayload) -> str | None:
        if isinstance(value, FilePayload):
            extension = value.metadata.extension
            return extension.lower() if extension else None
        if isinstance(value, Path):
            return value.suffix.lower()
        if isinstance(value, str):
            if not value.strip():
                raise ValidationError("File path inputs must not be empty")
            return Path(value).suffix.lower()
        raise ValidationError(
            "CandidateProcessingService file inputs require paths or FilePayloads"
        )

    def _validate_github_url(self, value: str) -> None:
        if not value.strip():
            raise ValidationError("github_url must not be empty")
        if self._source_detector.detect(value) != SourceType.GITHUB_PROFILE:
            raise ValidationError("github_url must be an HTTPS GitHub profile URL")

    def _build_default_orchestrator(
        self, services: ServiceContainer | None
    ) -> AgentOrchestrator:
        adapter_registry = (
            services.adapter_registry if services is not None else AdapterRegistry()
        )
        self._register_default_adapters(adapter_registry)
        intake_agent = IntakeAgent(
            loaders=self._default_loaders(),
            adapter_registry=adapter_registry,
        )
        return AgentOrchestrator(intake_agent=intake_agent)

    def _register_default_adapters(self, registry: AdapterRegistry) -> None:
        registered = set(registry.list_registered())
        for adapter in (ResumeFileAdapter(), ATSJsonAdapter(), RecruiterCSVAdapter()):
            if adapter.source_type not in registered:
                registry.register(adapter)

    def _default_loaders(self) -> dict[str, BaseLoader]:
        return {
            ".pdf": PDFLoader(),
            ".docx": DOCXLoader(),
            ".json": JSONLoader(),
            ".csv": CSVLoader(),
        }
