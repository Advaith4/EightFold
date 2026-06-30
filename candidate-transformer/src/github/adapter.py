"""Adapter converting raw GitHub payloads into raw candidate records."""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any

from src.exceptions import AdapterError
from src.github.models import GitHubPayload
from src.interfaces import BaseAdapter
from src.models import PayloadFormat, RawCandidateRecord
from src.models.enums import SourceType


class GitHubAdapter(BaseAdapter):
    """Create immutable raw candidate records from GitHub API payloads."""

    source_system = "github"
    adapter_version = "0.1.0"

    def __init__(self, payload: GitHubPayload | None = None) -> None:
        """Initialize the adapter with an optional already-fetched payload."""
        self._payload = payload

    @property
    def source_type(self) -> str:
        """Return the adapter source type."""
        return SourceType.GITHUB.value

    def load(self) -> GitHubPayload:
        """Return the provided GitHub payload."""
        if self._payload is None:
            raise AdapterError("GitHubAdapter requires a GitHubPayload")
        return self._payload

    def parse(self, raw_data: Any) -> RawCandidateRecord:
        """Convert a GitHubPayload into a RawCandidateRecord."""
        if not isinstance(raw_data, GitHubPayload):
            raise AdapterError("GitHubAdapter requires a GitHubPayload")
        username = raw_data.profile.get("login")
        if not isinstance(username, str) or not username:
            raise AdapterError("GitHub payload is missing profile login")
        payload = self._raw_payload(raw_data)
        checksum = self._checksum(payload)
        return RawCandidateRecord(
            record_id=f"github_{username}",
            source_type=SourceType.GITHUB,
            source_system=self.source_system,
            source_record_id=username,
            payload_format=PayloadFormat.API_RESPONSE,
            payload=payload,
            checksum=checksum,
        )

    def metadata(self) -> dict[str, Any]:
        """Return adapter metadata."""
        return {
            "source_type": self.source_type,
            "source_system": self.source_system,
            "adapter_version": self.adapter_version,
        }

    def _raw_payload(self, payload: GitHubPayload) -> dict[str, Any]:
        return {
            "profile": payload.profile,
            "repositories": payload.repositories,
            "languages": payload.languages,
            "provenance": self._provenance(payload),
        }

    def _provenance(self, payload: GitHubPayload) -> dict[str, Any]:
        profile_fields = tuple(sorted(payload.profile))
        repository_fields = {
            self._repository_key(repository): tuple(sorted(repository))
            for repository in payload.repositories
        }
        language_fields = {
            repository_name: tuple(sorted(languages))
            for repository_name, languages in payload.languages.items()
        }
        return {
            "source": "GitHub",
            "method": "REST API",
            "profile_fields": profile_fields,
            "repository_fields": repository_fields,
            "language_fields": language_fields,
        }

    def _repository_key(self, repository: dict[str, Any]) -> str:
        full_name = repository.get("full_name")
        if isinstance(full_name, str) and full_name:
            return full_name
        name = repository.get("name")
        if isinstance(name, str) and name:
            return name
        return "unknown_repository"

    def _checksum(self, payload: dict[str, Any]) -> str:
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return f"sha256:{sha256(serialized.encode('utf-8')).hexdigest()}"
