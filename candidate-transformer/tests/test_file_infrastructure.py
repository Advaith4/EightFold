"""File infrastructure tests for Sprint 4.1."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import cast

import pytest
from pydantic import ValidationError
from src.loaders import (
    BaseLoader,
    CorruptedFileError,
    FileMetadata,
    FilePayload,
    FileReadError,
    FileTooLargeError,
    LoaderError,
    UnsupportedFileTypeError,
    UploadedContent,
)

UTC_NOW = datetime(2026, 6, 30, 9, 30, tzinfo=timezone.utc)  # noqa: UP017


def test_file_payload_accepts_bytes_only_representation() -> None:
    """FilePayload represents loaded technical bytes and metadata only."""
    metadata = FileMetadata(
        filename="resume.pdf",
        content_type="application/pdf",
        extension=".pdf",
        size_bytes=4,
        checksum="sha256:abcd",
        loaded_at=UTC_NOW,
    )
    payload = FilePayload(content_bytes=b"data", metadata=metadata)

    assert payload.content_bytes == b"data"
    assert payload.text is None
    assert payload.metadata.filename == "resume.pdf"


def test_file_payload_accepts_text_only_representation_and_serializes() -> None:
    """Text payloads serialize with nested metadata for future loaders."""
    metadata = FileMetadata(
        filename="candidate.txt",
        content_type="text/plain",
        extension=".txt",
        size_bytes=0,
        checksum="sha256:text",
        encoding="utf-8",
        loaded_at=UTC_NOW,
    )
    payload = FilePayload(text="plain file text", metadata=metadata)

    dumped = payload.model_dump(mode="json")
    reloaded = FilePayload.model_validate(dumped)

    assert dumped["text"] == "plain file text"
    assert dumped["metadata"]["checksum"] == "sha256:text"
    assert reloaded == payload


def test_file_metadata_rejects_invalid_values() -> None:
    """FileMetadata enforces technical metadata constraints."""
    with pytest.raises(ValidationError):
        FileMetadata(size_bytes=-1, checksum="sha256:bad")
    with pytest.raises(ValidationError):
        FileMetadata(size_bytes=1, checksum="")
    with pytest.raises(ValidationError):
        FileMetadata(
            size_bytes=1,
            checksum="sha256:bad",
            filename="",
        )
    with pytest.raises(ValidationError):
        FileMetadata(
            size_bytes=1,
            checksum="sha256:bad",
            loaded_at=datetime(2026, 6, 30, 9, 30),
        )
    with pytest.raises(ValidationError):
        FileMetadata(size_bytes=1, checksum="sha256:bad", extension="pdf")
    with pytest.raises(ValidationError):
        FileMetadata(size_bytes=1, checksum="sha256:bad", content_type="plain")


def test_file_payload_rejects_missing_or_multiple_representations() -> None:
    """FilePayload requires exactly one loaded representation."""
    metadata = FileMetadata(size_bytes=4, checksum="sha256:abcd", loaded_at=UTC_NOW)

    with pytest.raises(ValidationError):
        FilePayload(metadata=metadata)
    with pytest.raises(ValidationError):
        FilePayload(content_bytes=b"data", text="plain text", metadata=metadata)


def test_file_payload_rejects_invalid_content_values() -> None:
    """FilePayload validates content values without parsing them."""
    metadata = FileMetadata(size_bytes=4, checksum="sha256:abcd", loaded_at=UTC_NOW)

    with pytest.raises(ValidationError):
        FilePayload(content_bytes=b"too long", metadata=metadata)
    with pytest.raises(ValidationError):
        FilePayload(text="", metadata=metadata)


def test_file_payload_is_immutable() -> None:
    """File infrastructure models are immutable value objects."""
    payload = FilePayload(
        content_bytes=b"data",
        metadata=FileMetadata(size_bytes=4, checksum="sha256:abcd", loaded_at=UTC_NOW),
    )

    with pytest.raises(ValidationError):
        payload.text = "changed"


def test_base_loader_is_abstract_contract() -> None:
    """BaseLoader cannot be instantiated without a load implementation."""
    with pytest.raises(TypeError):
        BaseLoader()  # type: ignore[abstract]


class InMemoryLoader(BaseLoader):
    """Test-only loader proving the abstract contract shape."""

    def load(self, source: UploadedContent) -> FilePayload:
        data = cast(bytes, source)
        return FilePayload(
            content_bytes=data,
            metadata=FileMetadata(
                size_bytes=len(data),
                checksum="sha256:test",
                loaded_at=UTC_NOW,
            ),
        )


def test_base_loader_contract_returns_file_payload() -> None:
    """Concrete loaders must return FilePayload without parsing candidate data."""
    loader = InMemoryLoader()

    payload = loader.load(b"data")

    assert isinstance(payload, FilePayload)
    assert payload.content_bytes == b"data"


def test_loader_exception_hierarchy() -> None:
    """Loader-specific errors inherit from LoaderError."""
    for error_type in (
        UnsupportedFileTypeError,
        FileTooLargeError,
        FileReadError,
        CorruptedFileError,
    ):
        assert issubclass(error_type, LoaderError)
