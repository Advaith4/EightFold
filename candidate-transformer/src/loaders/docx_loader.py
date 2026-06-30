"""Concrete DOCX file loader."""

from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.document import Document as DocumentObject
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph

from src.loaders.base import BaseLoader, UploadedContent
from src.loaders.exceptions import (
    CorruptedFileError,
    FileReadError,
    UnsupportedFileTypeError,
)
from src.loaders.models import ExtractionStatus, FileMetadata, FilePayload


class DOCXLoader(BaseLoader):
    """Load DOCX files into technical FilePayload objects."""

    supported_extension = ".docx"
    content_type = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

    def load(self, source: UploadedContent) -> FilePayload:
        """Read a DOCX file and extract deterministic text in document order."""
        path = self._path_from_source(source)
        self._validate_path(path)
        content_bytes = self._read_bytes(path)
        if not content_bytes:
            raise CorruptedFileError("DOCX file is empty")
        document = self._open_document(content_bytes)
        text = self._extract_text(document)
        if not text.strip():
            raise CorruptedFileError("DOCX document contains no text")
        return FilePayload(
            text=text,
            metadata=FileMetadata(
                filename=path.name,
                content_type=self.content_type,
                extension=path.suffix.lower(),
                size_bytes=len(content_bytes),
                checksum=f"sha256:{sha256(content_bytes).hexdigest()}",
                source_path=str(path),
                extraction_status=ExtractionStatus.TEXT_EXTRACTED,
            ),
        )

    def _path_from_source(self, source: UploadedContent) -> Path:
        if isinstance(source, Path):
            return source
        if isinstance(source, str):
            return Path(source)
        raise FileReadError("DOCXLoader requires a filesystem path")

    def _validate_path(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            raise FileReadError("DOCX file does not exist")
        if path.suffix.lower() != self.supported_extension:
            raise UnsupportedFileTypeError("DOCXLoader only supports .docx files")

    def _read_bytes(self, path: Path) -> bytes:
        try:
            return path.read_bytes()
        except OSError as exc:
            raise FileReadError("DOCX file is unreadable") from exc

    def _open_document(self, content: bytes) -> DocumentObject:
        try:
            return Document(BytesIO(content))
        except Exception as exc:
            raise CorruptedFileError("DOCX document is corrupted") from exc

    def _extract_text(self, document: DocumentObject) -> str:
        parts: list[str] = []
        for block in self._iter_block_items(document):
            if isinstance(block, Paragraph):
                parts.append(block.text)
            else:
                parts.extend(self._extract_table_text(block))
        return "\n".join(parts)

    def _iter_block_items(self, document: DocumentObject) -> list[Paragraph | Table]:
        body = document.element.body
        blocks: list[Paragraph | Table] = []
        for child in body.iterchildren():
            if isinstance(child, CT_P):
                blocks.append(Paragraph(child, document))
            elif isinstance(child, CT_Tbl):
                blocks.append(Table(child, document))
        return blocks

    def _extract_table_text(self, table: Table) -> list[str]:
        cell_text: list[str] = []
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    if paragraph.text:
                        cell_text.append(paragraph.text)
        return cell_text
