"""CSV and JSON loader tests for Sprint 4.2."""

from __future__ import annotations

from pathlib import Path

import pytest
from src.loaders import (
    CorruptedFileError,
    CSVLoader,
    FilePayload,
    FileReadError,
    JSONLoader,
    UnsupportedFileTypeError,
)


def test_csv_loader_loads_valid_csv(tmp_path: Path) -> None:
    """CSVLoader reads CSV text into a FilePayload without parsing rows."""
    path = tmp_path / "candidates.csv"
    path.write_bytes(b"name,email\nAnika,anika@example.com\n")

    payload = CSVLoader().load(path)

    assert isinstance(payload, FilePayload)
    assert payload.text == "name,email\nAnika,anika@example.com\n"
    assert payload.content_bytes is None
    assert payload.metadata.filename == "candidates.csv"
    assert payload.metadata.extension == ".csv"
    assert payload.metadata.content_type == "text/csv"
    assert payload.metadata.encoding == "utf-8-sig"
    assert payload.metadata.checksum.startswith("sha256:")


def test_csv_loader_rejects_empty_csv(tmp_path: Path) -> None:
    """CSVLoader rejects empty files instead of returning partial payloads."""
    path = tmp_path / "empty.csv"
    path.write_text("", encoding="utf-8")

    with pytest.raises(CorruptedFileError):
        CSVLoader().load(path)


def test_csv_loader_rejects_wrong_extension(tmp_path: Path) -> None:
    """CSVLoader validates the technical file extension."""
    path = tmp_path / "candidates.txt"
    path.write_text("name,email\n", encoding="utf-8")

    with pytest.raises(UnsupportedFileTypeError):
        CSVLoader().load(path)


def test_csv_loader_rejects_missing_file(tmp_path: Path) -> None:
    """CSVLoader raises a loader read error for missing files."""
    with pytest.raises(FileReadError):
        CSVLoader().load(tmp_path / "missing.csv")


def test_csv_loader_handles_utf8_bom(tmp_path: Path) -> None:
    """CSVLoader detects UTF-8 BOM encoded files."""
    path = tmp_path / "bom.csv"
    path.write_bytes("name,email\n".encode("utf-8-sig"))

    payload = CSVLoader().load(path)

    assert payload.text == "name,email\n"
    assert payload.metadata.encoding == "utf-8-sig"


def test_csv_loader_rejects_undecodable_bytes(tmp_path: Path) -> None:
    """CSVLoader reports encoding failures as loader read errors."""
    path = tmp_path / "bad.csv"
    path.write_bytes(b"\xff\xfe\x00")

    with pytest.raises(FileReadError):
        CSVLoader().load(path)


def test_json_loader_loads_valid_json(tmp_path: Path) -> None:
    """JSONLoader validates syntax while preserving original JSON text."""
    path = tmp_path / "candidate.json"
    original = '{"name":"Anika","skills":["Python"]}'
    path.write_text(original, encoding="utf-8")

    payload = JSONLoader().load(path)

    assert isinstance(payload, FilePayload)
    assert payload.text == original
    assert payload.content_bytes is None
    assert payload.metadata.filename == "candidate.json"
    assert payload.metadata.extension == ".json"
    assert payload.metadata.content_type == "application/json"
    assert payload.metadata.encoding == "utf-8-sig"


def test_json_loader_rejects_invalid_json(tmp_path: Path) -> None:
    """JSONLoader rejects invalid JSON syntax without recovery."""
    path = tmp_path / "candidate.json"
    path.write_text('{"name":', encoding="utf-8")

    with pytest.raises(CorruptedFileError):
        JSONLoader().load(path)


def test_json_loader_rejects_empty_json(tmp_path: Path) -> None:
    """JSONLoader rejects empty JSON files."""
    path = tmp_path / "empty.json"
    path.write_text("", encoding="utf-8")

    with pytest.raises(CorruptedFileError):
        JSONLoader().load(path)


def test_json_loader_rejects_wrong_extension(tmp_path: Path) -> None:
    """JSONLoader validates the technical file extension."""
    path = tmp_path / "candidate.txt"
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(UnsupportedFileTypeError):
        JSONLoader().load(path)


def test_json_loader_rejects_missing_file(tmp_path: Path) -> None:
    """JSONLoader raises a loader read error for missing files."""
    with pytest.raises(FileReadError):
        JSONLoader().load(tmp_path / "missing.json")


def test_json_loader_serialization_round_trip(tmp_path: Path) -> None:
    """JSONLoader payloads serialize and deserialize as FilePayload objects."""
    path = tmp_path / "candidate.json"
    path.write_text("{}", encoding="utf-8")
    payload = JSONLoader().load(path)

    dumped = payload.model_dump(mode="json")
    reloaded = FilePayload.model_validate(dumped)

    assert dumped["text"] == "{}"
    assert dumped["metadata"]["content_type"] == "application/json"
    assert reloaded == payload
