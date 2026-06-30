"""Concrete PDF file loader."""

from __future__ import annotations

from collections.abc import Sequence
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from src.loaders.base import BaseLoader, UploadedContent
from src.loaders.exceptions import (
    CorruptedFileError,
    FileReadError,
    UnsupportedFileTypeError,
)
from src.loaders.models import ExtractionStatus, FileMetadata, FilePayload


class PDFLoader(BaseLoader):
    """Load digital PDFs into technical FilePayload objects."""

    supported_extension = ".pdf"
    content_type = "application/pdf"

    def load(self, source: UploadedContent) -> FilePayload:
        """Read a PDF and deterministically extract its text layer when present."""
        path = self._path_from_source(source)
        self._validate_path(path)
        content_bytes = self._read_bytes(path)
        if not content_bytes:
            raise CorruptedFileError("PDF file is empty")
        reader = self._open_pdf(content_bytes)
        page_count = len(reader.pages)
        try:
            text = self._extract_text(reader.pages)
        except CorruptedFileError:
            raise
        except Exception as exc:
            raise CorruptedFileError("PDF text extraction failed") from exc
        checksum = f"sha256:{sha256(content_bytes).hexdigest()}"
        metadata = FileMetadata(
            filename=path.name,
            content_type=self.content_type,
            extension=path.suffix.lower(),
            size_bytes=len(content_bytes),
            checksum=checksum,
            source_path=str(path),
            page_count=page_count,
            extraction_status=(
                ExtractionStatus.TEXT_EXTRACTED
                if text.strip()
                else ExtractionStatus.NO_TEXT_LAYER
            ),
        )
        if text.strip():
            return FilePayload(text=text, metadata=metadata)
        return FilePayload(content_bytes=content_bytes, metadata=metadata)

    def _path_from_source(self, source: UploadedContent) -> Path:
        if isinstance(source, Path):
            return source
        if isinstance(source, str):
            return Path(source)
        raise FileReadError("PDFLoader requires a filesystem path")

    def _validate_path(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            raise FileReadError("PDF file does not exist")
        if path.suffix.lower() != self.supported_extension:
            raise UnsupportedFileTypeError("PDFLoader only supports .pdf files")

    def _read_bytes(self, path: Path) -> bytes:
        try:
            return path.read_bytes()
        except OSError as exc:
            raise FileReadError("PDF file is unreadable") from exc

    def _open_pdf(self, content: bytes) -> PdfReader:
        try:
            return PdfReader(BytesIO(content))
        except PdfReadError as exc:
            raise CorruptedFileError("PDF file is corrupted") from exc
        except Exception as exc:
            raise CorruptedFileError("PDF file could not be opened") from exc

    def _extract_text(self, pages: Sequence[Any]) -> str:
        try:
            page_text = [page.extract_text() or "" for page in pages]
        except Exception as exc:
            raise CorruptedFileError("PDF text extraction failed") from exc
        return "\n".join(page_text)
