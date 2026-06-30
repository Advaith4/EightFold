"""File loading infrastructure models."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CONTENT_TYPE_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]*/[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]*$"
)
EXTENSION_PATTERN = re.compile(r"^\.[A-Za-z0-9][A-Za-z0-9._-]*$")


class ExtractionStatus(str, Enum):  # noqa: UP042
    """Technical extraction status for document loaders."""

    TEXT_EXTRACTED = "text_extracted"
    NO_TEXT_LAYER = "no_text_layer"
    EXTRACTION_FAILED = "extraction_failed"


def utc_now() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)  # noqa: UP017


def ensure_timezone_aware(value: datetime, field_name: str) -> datetime:
    """Validate that a datetime includes timezone information."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value


class LoaderModel(BaseModel):
    """Base configuration for immutable loader infrastructure models."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        populate_by_name=True,
    )


class FileMetadata(LoaderModel):
    """Technical metadata captured for a loaded file payload."""

    filename: str | None = None
    content_type: str | None = None
    extension: str | None = None
    size_bytes: int = Field(ge=0)
    checksum: str
    encoding: str | None = None
    source_path: str | None = None
    extraction_status: ExtractionStatus | None = None
    page_count: int | None = Field(default=None, ge=0)
    loaded_at: datetime = Field(default_factory=utc_now)

    @field_validator("filename", "content_type", "extension", "encoding", "source_path")
    @classmethod
    def optional_strings_must_not_be_empty(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("metadata strings must not be empty")
        return value

    @field_validator("content_type")
    @classmethod
    def content_type_must_have_valid_format(cls, value: str | None) -> str | None:
        if value is not None and not CONTENT_TYPE_PATTERN.match(value):
            raise ValueError("content_type must use type/subtype format")
        return value

    @field_validator("extension")
    @classmethod
    def extension_must_have_valid_format(cls, value: str | None) -> str | None:
        if value is not None and not EXTENSION_PATTERN.match(value):
            raise ValueError("extension must start with a dot and contain a suffix")
        return value

    @field_validator("checksum")
    @classmethod
    def checksum_must_be_non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("checksum must be non-empty")
        return value

    @field_validator("loaded_at")
    @classmethod
    def loaded_at_must_be_aware(cls, value: datetime) -> datetime:
        return ensure_timezone_aware(value, "loaded_at")


class FilePayload(LoaderModel):
    """Loaded technical file content handed off by the File Loading stage."""

    content_bytes: bytes | None = None
    text: str | None = None
    metadata: FileMetadata

    @field_validator("text")
    @classmethod
    def text_must_not_be_empty(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("text must not be empty when provided")
        return value

    @model_validator(mode="after")
    def content_must_have_exactly_one_representation(self) -> FilePayload:
        has_bytes = self.content_bytes is not None
        has_text = self.text is not None
        if has_bytes == has_text:
            raise ValueError("FilePayload requires exactly one loaded representation")
        if (
            self.content_bytes is not None
            and len(self.content_bytes) != self.metadata.size_bytes
        ):
            raise ValueError("metadata.size_bytes must match content_bytes length")
        return self
