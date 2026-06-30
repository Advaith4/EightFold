"""PDF loader tests for Sprint 4.3A."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from pydantic import ValidationError
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from src.loaders import (
    BaseLoader,
    CorruptedFileError,
    ExtractionStatus,
    FilePayload,
    FileReadError,
    PDFLoader,
    UnsupportedFileTypeError,
)


def build_text_pdf(text: str) -> bytes:
    """Create a minimal digital PDF containing an extractable text layer."""
    writer = PdfWriter()
    page = writer.add_blank_page(width=200, height=200)
    resources = DictionaryObject()
    font = DictionaryObject()
    font_object = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font[NameObject("/F1")] = writer._add_object(font_object)
    resources[NameObject("/Font")] = font
    page[NameObject("/Resources")] = resources
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 12 Tf 72 120 Td ({text}) Tj ET".encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def build_blank_pdf() -> bytes:
    """Create a valid PDF page without an extractable text layer."""
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_pdf_loader_loads_valid_digital_pdf(tmp_path: Path) -> None:
    """PDFLoader extracts deterministic PDF text into a FilePayload."""
    path = tmp_path / "document.pdf"
    path.write_bytes(build_text_pdf("Hello PDF"))

    payload = PDFLoader().load(path)

    assert isinstance(payload, FilePayload)
    assert payload.text == "Hello PDF"
    assert payload.content_bytes is None
    assert payload.metadata.filename == "document.pdf"
    assert payload.metadata.extension == ".pdf"
    assert payload.metadata.content_type == "application/pdf"
    assert payload.metadata.checksum.startswith("sha256:")
    assert payload.metadata.page_count == 1
    assert payload.metadata.extraction_status is ExtractionStatus.TEXT_EXTRACTED


def test_pdf_loader_rejects_missing_file(tmp_path: Path) -> None:
    """PDFLoader raises a loader read error for missing files."""
    with pytest.raises(FileReadError):
        PDFLoader().load(tmp_path / "missing.pdf")


def test_pdf_loader_rejects_unsupported_extension(tmp_path: Path) -> None:
    """PDFLoader validates the technical file extension."""
    path = tmp_path / "document.txt"
    path.write_bytes(build_text_pdf("Hello PDF"))

    with pytest.raises(UnsupportedFileTypeError):
        PDFLoader().load(path)


def test_pdf_loader_rejects_unreadable_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PDFLoader reports read failures through the loader exception hierarchy."""
    path = tmp_path / "document.pdf"
    path.write_bytes(build_text_pdf("Hello PDF"))

    def fail_read_bytes(self: Path) -> bytes:
        raise OSError("unreadable")

    monkeypatch.setattr(Path, "read_bytes", fail_read_bytes)

    with pytest.raises(FileReadError):
        PDFLoader().load(path)


def test_pdf_loader_rejects_corrupted_pdf(tmp_path: Path) -> None:
    """PDFLoader rejects malformed PDF bytes without recovery."""
    path = tmp_path / "broken.pdf"
    path.write_bytes(b"%PDF-1.4\nnot a valid pdf")

    with pytest.raises(CorruptedFileError):
        PDFLoader().load(path)


def test_pdf_loader_rejects_empty_pdf(tmp_path: Path) -> None:
    """PDFLoader rejects empty files instead of returning partial payloads."""
    path = tmp_path / "empty.pdf"
    path.write_bytes(b"")

    with pytest.raises(CorruptedFileError):
        PDFLoader().load(path)


def test_pdf_loader_returns_bytes_when_pdf_has_no_text_layer(tmp_path: Path) -> None:
    """PDFLoader does not perform OCR when no deterministic text layer exists."""
    path = tmp_path / "blank.pdf"
    content = build_blank_pdf()
    path.write_bytes(content)

    payload = PDFLoader().load(path)

    assert payload.text is None
    assert payload.content_bytes == content
    assert payload.metadata.extraction_status is ExtractionStatus.NO_TEXT_LAYER
    assert payload.metadata.page_count == 1


def test_pdf_loader_reports_extraction_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PDFLoader raises a loader error when deterministic extraction fails."""
    path = tmp_path / "document.pdf"
    path.write_bytes(build_text_pdf("Hello PDF"))
    loader = PDFLoader()

    def fail_extract(pages: object) -> str:
        raise RuntimeError("extract failed")

    monkeypatch.setattr(loader, "_extract_text", fail_extract)

    with pytest.raises(CorruptedFileError):
        loader.load(path)


def test_pdf_loader_payload_serializes(tmp_path: Path) -> None:
    """PDFLoader payloads serialize and deserialize as FilePayload objects."""
    path = tmp_path / "document.pdf"
    path.write_bytes(build_text_pdf("Hello PDF"))
    payload = PDFLoader().load(path)

    dumped = payload.model_dump(mode="json")
    reloaded = FilePayload.model_validate(dumped)

    assert dumped["text"] == "Hello PDF"
    assert dumped["metadata"]["extraction_status"] == "text_extracted"
    assert reloaded == payload


def test_pdf_loader_payload_is_immutable(tmp_path: Path) -> None:
    """PDFLoader returns immutable loader infrastructure models."""
    path = tmp_path / "document.pdf"
    path.write_bytes(build_text_pdf("Hello PDF"))
    payload = PDFLoader().load(path)

    with pytest.raises(ValidationError):
        payload.text = "changed"


def test_pdf_loader_implements_base_loader_contract() -> None:
    """PDFLoader is a concrete BaseLoader implementation."""
    loader = PDFLoader()

    assert isinstance(loader, BaseLoader)


def test_blank_pdf_fixture_has_no_text_layer() -> None:
    """The no-text-layer fixture remains a valid PDF without extractable text."""
    reader = PdfReader(BytesIO(build_blank_pdf()))

    assert (reader.pages[0].extract_text() or "") == ""
