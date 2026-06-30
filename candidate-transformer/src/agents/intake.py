"""Acquisition and routing agent for candidate artifacts."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path

from src.adapters import AdapterRegistry
from src.detection.detector import SourceDetector
from src.enums import SourceType
from src.exceptions import AdapterError, ValidationError
from src.github import GitHubAdapter, GitHubFetcher
from src.interfaces import BaseAdapter
from src.loaders import BaseLoader, FilePayload, UploadedContent
from src.models import RawCandidateRecord

CandidateArtifact = UploadedContent | FilePayload


class IntakeAgent:
    """Coordinate existing acquisition components into raw candidate records."""

    def __init__(
        self,
        *,
        source_detector: SourceDetector | None = None,
        github_fetcher: GitHubFetcher | None = None,
        github_adapter: GitHubAdapter | None = None,
        loaders: Mapping[str, BaseLoader] | None = None,
        adapter_registry: AdapterRegistry | None = None,
    ) -> None:
        """Initialize the intake agent with injectable infrastructure services."""
        self._source_detector = source_detector or SourceDetector()
        self._github_fetcher = github_fetcher or GitHubFetcher()
        self._github_adapter = github_adapter or GitHubAdapter()
        self._loaders = dict(loaders or {})
        self._adapter_registry = adapter_registry or AdapterRegistry()
        self._errors: list[str] = []

    def process(
        self, artifacts: CandidateArtifact | Iterable[CandidateArtifact]
    ) -> list[RawCandidateRecord]:
        """Acquire and route candidate artifacts into raw source records."""
        self._errors = []
        records: list[RawCandidateRecord] = []
        for artifact in self._normalize_artifacts(artifacts):
            try:
                records.extend(self._process_one(artifact))
            except Exception as exc:  # noqa: BLE001
                self._errors.append(str(exc))
        return records

    @property
    def errors(self) -> tuple[str, ...]:
        """Return non-fatal ingestion errors from the last process call."""
        return tuple(self._errors)

    def _normalize_artifacts(
        self, artifacts: CandidateArtifact | Iterable[CandidateArtifact]
    ) -> tuple[CandidateArtifact, ...]:
        if isinstance(artifacts, (bytes, str, Path, FilePayload)):
            return (artifacts,)
        return tuple(artifacts)

    def _process_one(self, artifact: CandidateArtifact) -> list[RawCandidateRecord]:
        if isinstance(artifact, str):
            detected_source = self._source_detector.detect(artifact)
            if detected_source == SourceType.GITHUB_PROFILE:
                github_payload = self._github_fetcher.fetch(artifact)
                return self._records_from_parsed(
                    self._github_adapter.parse(github_payload)
                )
        file_payload = self._load_payload(artifact)
        detected_source = self._source_detector.detect(file_payload)
        adapter = self._adapter_for(detected_source)
        return self._records_from_parsed(adapter.parse(file_payload))

    def _records_from_parsed(self, parsed: object) -> list[RawCandidateRecord]:
        if isinstance(parsed, RawCandidateRecord):
            return [parsed]
        if isinstance(parsed, list):
            return [
                record for record in parsed if isinstance(record, RawCandidateRecord)
            ]
        raise AdapterError("Adapter did not return RawCandidateRecord objects")

    def _load_payload(self, artifact: CandidateArtifact) -> FilePayload:
        if isinstance(artifact, FilePayload):
            return artifact
        loader = self._loader_for(artifact)
        return loader.load(artifact)

    def _loader_for(self, artifact: UploadedContent) -> BaseLoader:
        if isinstance(artifact, Path):
            extension = artifact.suffix.lower()
        elif isinstance(artifact, str):
            extension = Path(artifact).suffix.lower()
        else:
            raise ValidationError("IntakeAgent requires a FilePayload, path, or URL")
        try:
            return self._loaders[extension]
        except KeyError as exc:
            raise AdapterError(
                f"No loader registered for extension: {extension}"
            ) from exc

    def _adapter_for(self, source_type: SourceType) -> BaseAdapter:
        return self._adapter_registry.get(source_type.value)
