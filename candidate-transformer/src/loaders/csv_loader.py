"""Concrete CSV file loader."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from src.loaders.base import BaseLoader, UploadedContent
from src.loaders.exceptions import (
    CorruptedFileError,
    FileReadError,
    UnsupportedFileTypeError,
)
from src.loaders.models import FileMetadata, FilePayload


class CSVLoader(BaseLoader):
    """Load CSV files into technical FilePayload objects."""

    supported_extension = ".csv"
    content_type = "text/csv"

    def load(self, source: UploadedContent) -> FilePayload:
        """Read a CSV file as text without interpreting its rows or headers."""
        path = self._path_from_source(source)
        self._validate_path(path)
        content_bytes = self._read_bytes(path)
        if not content_bytes:
            raise CorruptedFileError("CSV file is empty")
        text, encoding = self._decode(content_bytes)
        if not text:
            raise CorruptedFileError("CSV file is empty")
        return FilePayload(
            text=text,
            metadata=FileMetadata(
                filename=path.name,
                content_type=self.content_type,
                extension=path.suffix.lower(),
                size_bytes=len(content_bytes),
                checksum=f"sha256:{sha256(content_bytes).hexdigest()}",
                encoding=encoding,
                source_path=str(path),
            ),
        )

    def _path_from_source(self, source: UploadedContent) -> Path:
        if isinstance(source, Path):
            return source
        if isinstance(source, str):
            return Path(source)
        raise FileReadError("CSVLoader requires a filesystem path")

    def _validate_path(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            raise FileReadError("CSV file does not exist")
        if path.suffix.lower() != self.supported_extension:
            raise UnsupportedFileTypeError("CSVLoader only supports .csv files")

    def _read_bytes(self, path: Path) -> bytes:
        try:
            return path.read_bytes()
        except OSError as exc:
            raise FileReadError("CSV file is unreadable") from exc

    def _decode(self, content: bytes) -> tuple[str, str]:
        for encoding in ("utf-8-sig", "utf-8", "utf-16"):
            try:
                return content.decode(encoding), encoding
            except UnicodeDecodeError:
                continue
        raise FileReadError("CSV file encoding could not be decoded")
