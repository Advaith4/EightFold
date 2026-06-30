"""Deterministic source detection for loaded technical payloads."""

from __future__ import annotations

import csv
import json
from collections.abc import Mapping
from io import StringIO
from urllib.parse import urlparse

from src.enums import SourceType
from src.exceptions import ValidationError
from src.loaders.models import FilePayload

ATS_JSON_KEYS = frozenset(
    {
        "candidate",
        "applicant",
        "application",
        "resume",
        "experience",
        "education",
        "email",
        "phone",
        "full_name",
        "first_name",
        "last_name",
        "candidate_id",
        "ats_candidate_id",
        "applicant_id",
        "id",
    }
)
RECRUITER_CSV_HEADERS = frozenset(
    {
        "name",
        "full_name",
        "first_name",
        "last_name",
        "email",
        "phone",
        "skills",
        "experience",
        "education",
        "candidate_id",
        "ats_candidate_id",
        "applicant_id",
        "id",
        "resume",
        "linkedin",
        "github",
    }
)
GITHUB_RESERVED_PATHS = frozenset(
    {
        "about",
        "apps",
        "blog",
        "collections",
        "contact",
        "customer-stories",
        "events",
        "explore",
        "features",
        "marketplace",
        "new",
        "notifications",
        "organizations",
        "orgs",
        "pricing",
        "pulls",
        "search",
        "settings",
        "sponsors",
        "topics",
    }
)


class SourceDetector:
    """Classify source type from loader payload metadata and shallow structure."""

    def detect(self, source: FilePayload | str) -> SourceType:
        """Return a deterministic source type for a payload or GitHub profile URL."""
        if isinstance(source, str):
            return self._detect_github_url(source)
        if not isinstance(source, FilePayload):
            raise ValidationError("SourceDetector requires a FilePayload or URL string")
        if self._is_empty_payload(source):
            return SourceType.UNKNOWN
        extension = (source.metadata.extension or "").lower()
        content_type = (source.metadata.content_type or "").lower()
        if extension in {".pdf", ".docx"}:
            return SourceType.RESUME
        if extension == ".csv":
            return self._detect_csv(source)
        if extension == ".json" or content_type == "application/json":
            return self._detect_json(source)
        return SourceType.UNKNOWN

    def _is_empty_payload(self, payload: FilePayload) -> bool:
        if payload.text is not None:
            return not payload.text.strip()
        return not payload.content_bytes

    def _detect_json(self, payload: FilePayload) -> SourceType:
        text = payload.text or self._decode_bytes(payload.content_bytes)
        if text is None or not text.strip():
            return SourceType.UNKNOWN
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return SourceType.UNKNOWN
        if isinstance(parsed, Mapping) and self._contains_key(parsed, ATS_JSON_KEYS):
            return SourceType.ATS_JSON
        if isinstance(parsed, list) and any(
            isinstance(item, Mapping) and self._contains_key(item, ATS_JSON_KEYS)
            for item in parsed
        ):
            return SourceType.ATS_JSON
        return SourceType.UNKNOWN

    def _detect_csv(self, payload: FilePayload) -> SourceType:
        text = payload.text or self._decode_bytes(payload.content_bytes)
        if text is None or not text.strip():
            return SourceType.UNKNOWN
        try:
            rows = csv.reader(StringIO(text))
            headers = next(rows, [])
        except csv.Error:
            return SourceType.UNKNOWN
        normalized_headers = {header.strip().lower() for header in headers if header}
        if normalized_headers & RECRUITER_CSV_HEADERS:
            return SourceType.RECRUITER_CSV
        return SourceType.UNKNOWN

    def _detect_github_url(self, value: str) -> SourceType:
        parsed = urlparse(value)
        if parsed.scheme != "https" or parsed.netloc.lower() != "github.com":
            return SourceType.UNKNOWN
        path_parts = [part for part in parsed.path.split("/") if part]
        if len(path_parts) != 1:
            return SourceType.UNKNOWN
        username = path_parts[0]
        if username.lower() in GITHUB_RESERVED_PATHS or username.startswith("."):
            return SourceType.UNKNOWN
        return SourceType.GITHUB_PROFILE

    def _contains_key(
        self, value: Mapping[object, object], keys: frozenset[str]
    ) -> bool:
        return any(isinstance(key, str) and key.lower() in keys for key in value)

    def _decode_bytes(self, content: bytes | None) -> str | None:
        if content is None:
            return None
        for encoding in ("utf-8-sig", "utf-8", "utf-16"):
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        return None
