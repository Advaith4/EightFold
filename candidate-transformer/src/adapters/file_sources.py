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

    def _record_id(
        self, prefix: str, payload: FilePayload, suffix: str | None = None
    ) -> str:
        checksum = payload.metadata.checksum.replace(":", "_")
        if suffix is not None:
            return f"{prefix}_{checksum}_{suffix}"
        return f"{prefix}_{checksum}"

    def _source_record_id(self, payload: FilePayload) -> str | None:
        return payload.metadata.source_path or payload.metadata.filename

    def _indexed_source_record_id(
        self, payload: FilePayload, index: int, include_index: bool
    ) -> str | None:
        source_id = self._source_record_id(payload)
        if source_id is None or not include_index:
            return source_id
        return f"{source_id}#{index}"


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

    def parse(self, raw_data: Any) -> RawCandidateRecord | list[RawCandidateRecord]:
        """Parse JSON text into one or more ATS raw candidate records."""
        payload = self._require_payload(raw_data)
        parsed_items = self._parse_json(payload)
        records = [
            self._record_from_item(
                payload,
                item,
                index,
                include_index=len(parsed_items) > 1,
            )
            for index, item in enumerate(parsed_items, start=1)
        ]
        if len(records) == 1:
            return records[0]
        return records

    def _record_from_item(
        self,
        payload: FilePayload,
        item: dict[str, JsonValue],
        index: int,
        *,
        include_index: bool,
    ) -> RawCandidateRecord:
        suffix = f"row_{index}" if include_index else None
        return RawCandidateRecord(
            record_id=self._record_id("ats", payload, suffix),
            source_type=SourceType.ATS,
            source_system="ats",
            source_record_id=self._indexed_source_record_id(
                payload, index, include_index
            ),
            payload_format=PayloadFormat.JSON_DOCUMENT,
            payload=item,
            raw_text=payload.text,
            checksum=payload.metadata.checksum,
        )

    def _parse_json(self, payload: FilePayload) -> list[dict[str, JsonValue]]:
        text = payload.text or (
            payload.content_bytes.decode("utf-8") if payload.content_bytes else None
        )
        if text is None:
            raise AdapterError("ATSJsonAdapter requires JSON text")
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AdapterError("ATS JSON payload is malformed") from exc
        if isinstance(parsed, dict):
            return [self._normalize_json(parsed)]
        if isinstance(parsed, list):
            return [
                self._normalize_json(item)
                for item in parsed
                if isinstance(item, dict) and item
            ]
        raise AdapterError("ATS JSON payload must be an object or array")

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

    def parse(self, raw_data: Any) -> RawCandidateRecord | list[RawCandidateRecord]:
        """Parse recruiter CSV rows into raw candidate records."""
        payload = self._require_payload(raw_data)
        rows = self._rows(payload)
        records = [
            self._record_from_row(
                payload,
                row,
                index,
                include_index=len(rows) > 1,
            )
            for index, row in enumerate(rows, start=1)
        ]
        if len(records) == 1:
            return records[0]
        return records

    def _record_from_row(
        self,
        payload: FilePayload,
        row: dict[str, JsonValue],
        index: int,
        *,
        include_index: bool,
    ) -> RawCandidateRecord:
        suffix = f"row_{index}" if include_index else None
        return RawCandidateRecord(
            record_id=self._record_id("csv", payload, suffix),
            source_type=SourceType.CSV,
            source_system="recruiter_csv",
            source_record_id=self._indexed_source_record_id(
                payload, index, include_index
            ),
            payload_format=PayloadFormat.CSV_ROW,
            payload=row,
            raw_text=payload.text,
            checksum=payload.metadata.checksum,
        )

    def _rows(self, payload: FilePayload) -> list[dict[str, JsonValue]]:
        text = payload.text or (
            payload.content_bytes.decode("utf-8") if payload.content_bytes else None
        )
        if text is None:
            raise AdapterError("RecruiterCSVAdapter requires CSV text")
        reader = csv.DictReader(StringIO(text))
        rows = []
        for row in reader:
            cleaned_row = {key: value for key, value in row.items() if key is not None}
            normalized = self._normalize_csv(cleaned_row)
            if normalized:
                rows.append(normalized)
        if not rows:
            raise AdapterError("Recruiter CSV payload contains no rows")
        return rows

    def _normalize_csv(self, row: dict[str, Any]) -> dict[str, Any]:
        """Normalize CSV row headers to canonical payload keys."""
        normalized: dict[str, Any] = {}

        for k, v in row.items():
            clean_k = str(k).strip().lower().replace(" ", "_")
            if v is not None:
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
