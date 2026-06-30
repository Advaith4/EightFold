"""Adapters for loaded candidate file sources."""

from __future__ import annotations

import csv
import json
from io import StringIO
from typing import Any

from src.adapters.resume_parser import DeterministicResumeParser
from src.enums import SourceType as InfrastructureSourceType
from src.exceptions import AdapterError
from src.interfaces import BaseAdapter
from src.loaders import FilePayload
from src.models import PayloadFormat, RawCandidateRecord
from src.models.base import JsonValue
from src.models.enums import SourceType


class LoadedFileAdapter(BaseAdapter):
    """Base adapter for FilePayload-backed candidate sources."""

    source_system = "file"
    adapter_version = "0.1.0"

    def __init__(self, payload: FilePayload | None = None) -> None:
        """Initialize the adapter with an optional already-loaded payload."""
        self._payload = payload

    def load(self) -> FilePayload:
        """Return the provided file payload."""
        if self._payload is None:
            raise AdapterError(f"{self.__class__.__name__} requires a FilePayload")
        return self._payload

    def metadata(self) -> dict[str, Any]:
        """Return adapter metadata."""
        return {
            "source_type": self.source_type,
            "source_system": self.source_system,
            "adapter_version": self.adapter_version,
        }

    def _require_payload(self, raw_data: Any) -> FilePayload:
        if not isinstance(raw_data, FilePayload):
            raise AdapterError(f"{self.__class__.__name__} requires a FilePayload")
        return raw_data

    def _record_id(self, prefix: str, payload: FilePayload) -> str:
        checksum = payload.metadata.checksum.replace(":", "_")
        return f"{prefix}_{checksum}"

    def _source_record_id(self, payload: FilePayload) -> str | None:
        return payload.metadata.source_path or payload.metadata.filename


class ResumeFileAdapter(LoadedFileAdapter):
    """Convert loaded resume text into a raw resume candidate record."""

    @property
    def source_type(self) -> str:
        """Return the source type used by source detection."""
        return InfrastructureSourceType.RESUME.value

    def parse(self, raw_data: Any) -> RawCandidateRecord:
        """Preserve resume text as a raw candidate source."""
        payload = self._require_payload(raw_data)
        text = payload.text or ""
        extension = (payload.metadata.extension or "").lower()
        payload_format = (
            PayloadFormat.DOCX_TEXT if extension == ".docx" else PayloadFormat.PDF_TEXT
        )

        parser = DeterministicResumeParser(text)
        extracted = parser.parse()

        return RawCandidateRecord(
            record_id=self._record_id("resume", payload),
            source_type=SourceType.RESUME,
            source_system=self.source_system,
            source_record_id=self._source_record_id(payload),
            payload_format=payload_format,
            payload=extracted,
            raw_text=text or None,
            checksum=payload.metadata.checksum,
        )


class ATSJsonAdapter(LoadedFileAdapter):
    """Convert ATS JSON payloads into raw candidate records."""

    @property
    def source_type(self) -> str:
        """Return the source type used by source detection."""
        return InfrastructureSourceType.ATS_JSON.value

    def parse(self, raw_data: Any) -> RawCandidateRecord:
        """Parse validated JSON text into an ATS raw candidate record."""
        payload = self._require_payload(raw_data)
        parsed = self._parse_json(payload)
        return RawCandidateRecord(
            record_id=self._record_id("ats", payload),
            source_type=SourceType.ATS,
            source_system="ats",
            source_record_id=self._source_record_id(payload),
            payload_format=PayloadFormat.JSON_DOCUMENT,
            payload=parsed,
            raw_text=payload.text,
            checksum=payload.metadata.checksum,
        )

    def _parse_json(self, payload: FilePayload) -> dict[str, JsonValue]:
        text = payload.text or (
            payload.content_bytes.decode("utf-8") if payload.content_bytes else None
        )
        if text is None:
            raise AdapterError("ATSJsonAdapter requires JSON text")
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AdapterError("ATS JSON payload is malformed") from exc
        if not isinstance(parsed, dict):
            raise AdapterError("ATS JSON payload must be an object")

        return self._normalize_json(parsed)

    def _normalize_json(self, parsed: dict[str, Any]) -> dict[str, Any]:
        """Flatten nested fields common in ATS JSON."""
        normalized = dict(parsed)

        contact = normalized.get("contact")
        if isinstance(contact, dict):
            if "email" in contact and "email" not in normalized:
                normalized["email"] = contact["email"]
            if "phone" in contact and "phone" not in normalized:
                normalized["phone"] = contact["phone"]

        if "full_name" not in normalized:
            first = normalized.get("first_name", "")
            last = normalized.get("last_name", "")
            if first or last:
                normalized["full_name"] = f"{first} {last}".strip()

        return normalized


class RecruiterCSVAdapter(LoadedFileAdapter):
    """Convert recruiter CSV rows into raw candidate records."""

    @property
    def source_type(self) -> str:
        """Return the source type used by source detection."""
        return InfrastructureSourceType.RECRUITER_CSV.value

    def parse(self, raw_data: Any) -> RawCandidateRecord:
        """Parse the first recruiter CSV row into a raw candidate record."""
        payload = self._require_payload(raw_data)
        row = self._first_row(payload)
        return RawCandidateRecord(
            record_id=self._record_id("csv", payload),
            source_type=SourceType.CSV,
            source_system="recruiter_csv",
            source_record_id=self._source_record_id(payload),
            payload_format=PayloadFormat.CSV_ROW,
            payload=row,
            raw_text=payload.text,
            checksum=payload.metadata.checksum,
        )

    def _first_row(self, payload: FilePayload) -> dict[str, JsonValue]:
        text = payload.text or (
            payload.content_bytes.decode("utf-8") if payload.content_bytes else None
        )
        if text is None:
            raise AdapterError("RecruiterCSVAdapter requires CSV text")
        reader = csv.DictReader(StringIO(text))
        try:
            row = next(reader)
        except StopIteration as exc:
            raise AdapterError("Recruiter CSV payload contains no rows") from exc

        cleaned_row = {key: value for key, value in row.items() if key is not None}
        return self._normalize_csv(cleaned_row)

    def _normalize_csv(self, row: dict[str, Any]) -> dict[str, Any]:
        """Normalize CSV row headers to canonical payload keys."""
        normalized: dict[str, Any] = {}

        for k, v in row.items():
            clean_k = str(k).strip().lower().replace(" ", "_")
            normalized[clean_k] = v

        if "full_name" not in normalized and "name" not in normalized:
            first = normalized.get("first_name", "")
            last = normalized.get("last_name", "")
            if first or last:
                normalized["full_name"] = f"{first} {last}".strip()

        if "skills" in normalized and isinstance(normalized["skills"], str):
            skills_str = normalized["skills"]
            if skills_str:
                normalized["skills"] = [
                    s.strip() for s in skills_str.split(",") if s.strip()
                ]

        return normalized
