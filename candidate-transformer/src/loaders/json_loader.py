"""Concrete JSON file loader."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from src.loaders.base import BaseLoader, UploadedContent
from src.loaders.exceptions import (
    CorruptedFileError,
    FileReadError,
    UnsupportedFileTypeError,
)
from src.loaders.models import FileMetadata, FilePayload


class JSONLoader(BaseLoader):
    """Load JSON files into technical FilePayload objects."""

    supported_extension = ".json"
    content_type = "application/json"

    def load(self, source: UploadedContent) -> FilePayload:
        """Read a JSON file as text and validate syntax without interpretation."""
        path = self._path_from_source(source)
        self._validate_path(path)
        content_bytes = self._read_bytes(path)
        if not content_bytes:
            raise CorruptedFileError("JSON file is empty")
        text, encoding = self._decode(content_bytes)
        if not text.strip():
            raise CorruptedFileError("JSON file is empty")
        self._validate_json_syntax(text)
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
        raise FileReadError("JSONLoader requires a filesystem path")

    def _validate_path(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            raise FileReadError("JSON file does not exist")
        if path.suffix.lower() != self.supported_extension:
            raise UnsupportedFileTypeError("JSONLoader only supports .json files")

    def _read_bytes(self, path: Path) -> bytes:
        try:
            return path.read_bytes()
        except OSError as exc:
            raise FileReadError("JSON file is unreadable") from exc

    def _decode(self, content: bytes) -> tuple[str, str]:
        for encoding in ("utf-8-sig", "utf-8", "utf-16"):
            try:
                return content.decode(encoding), encoding
            except UnicodeDecodeError:
                continue
        raise FileReadError("JSON file encoding could not be decoded")

    def _validate_json_syntax(self, text: str) -> None:
        try:
            json.loads(text)
        except json.JSONDecodeError as exc:
            raise CorruptedFileError("JSON file contains invalid syntax") from exc
