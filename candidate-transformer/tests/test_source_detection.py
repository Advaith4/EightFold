"""Source detection tests for Sprint 5.0."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from src.detection import SourceDetector
from src.enums import SourceType
from src.exceptions import ValidationError
from src.loaders.models import FileMetadata, FilePayload

UTC_NOW = datetime(2026, 6, 30, 9, 30, tzinfo=timezone.utc)  # noqa: UP017


def payload(
    *,
    text: str | None = "content",
    content_bytes: bytes | None = None,
    extension: str | None,
    content_type: str | None = None,
    filename: str | None = None,
) -> FilePayload:
    """Build a technical payload for source detection tests."""
    metadata = FileMetadata(
        filename=filename,
        content_type=content_type,
        extension=extension,
        size_bytes=len(content_bytes or b""),
        checksum="sha256:test",
        loaded_at=UTC_NOW,
    )
    if text is not None:
        return FilePayload(text=text, metadata=metadata)
    return FilePayload(content_bytes=content_bytes or b"", metadata=metadata)


def test_detector_detects_pdf_as_resume() -> None:
    """PDF payloads classify as resume sources by extension."""
    detected = SourceDetector().detect(payload(extension=".pdf"))

    assert detected is SourceType.RESUME


def test_detector_detects_docx_as_resume() -> None:
    """DOCX payloads classify as resume sources by extension."""
    detected = SourceDetector().detect(payload(extension=".docx"))

    assert detected is SourceType.RESUME


def test_detector_detects_ats_json_from_required_keys() -> None:
    """ATS JSON detection uses structural keys without interpreting values."""
    detected = SourceDetector().detect(
        payload(
            text='{"candidate":{"name":"Anika"}}',
            extension=".json",
            content_type="application/json",
        )
    )

    assert detected is SourceType.ATS_JSON


def test_detector_detects_ats_json_from_mime_type() -> None:
    """JSON MIME type is sufficient when structural ATS keys are present."""
    detected = SourceDetector().detect(
        payload(
            text='{"application":{"id":"app_1"}}',
            extension=None,
            content_type="application/json",
        )
    )

    assert detected is SourceType.ATS_JSON


def test_detector_detects_recruiter_csv_from_headers() -> None:
    """Recruiter CSV detection inspects headers only."""
    detected = SourceDetector().detect(
        payload(text="full_name,email\nAnika,anika@example.com\n", extension=".csv")
    )

    assert detected is SourceType.RECRUITER_CSV


def test_detector_detects_github_profile_url() -> None:
    """Only single-segment HTTPS GitHub profile URLs are classified."""
    detected = SourceDetector().detect("https://github.com/octocat")

    assert detected is SourceType.GITHUB_PROFILE


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/octocat",
        "https://example.com/octocat",
        "https://github.com/octocat/hello-world",
        "https://github.com/octocat/hello-world/issues/1",
        "https://github.com/octocat/hello-world/pull/1",
        "https://github.com/orgs/python",
    ],
)
def test_detector_ignores_non_profile_github_urls(url: str) -> None:
    """Repository, issue, pull request, org, and non-HTTPS URLs remain unknown."""
    detected = SourceDetector().detect(url)

    assert detected is SourceType.UNKNOWN


def test_detector_returns_unknown_for_unknown_extension() -> None:
    """Unsupported extensions do not raise classification errors."""
    detected = SourceDetector().detect(payload(text="plain text", extension=".txt"))

    assert detected is SourceType.UNKNOWN


def test_detector_raises_existing_exception_for_invalid_payload() -> None:
    """Invalid detector inputs use the project exception hierarchy."""
    with pytest.raises(ValidationError):
        SourceDetector().detect(object())  # type: ignore[arg-type]


def test_detector_returns_unknown_for_empty_payload() -> None:
    """Empty technical payloads are valid but unclassified."""
    detected = SourceDetector().detect(
        payload(text=None, content_bytes=b"", extension=".bin")
    )

    assert detected is SourceType.UNKNOWN


def test_detector_returns_unknown_for_malformed_json() -> None:
    """Malformed JSON does not crash source detection."""
    detected = SourceDetector().detect(payload(text='{"candidate":', extension=".json"))

    assert detected is SourceType.UNKNOWN


def test_detector_returns_unknown_for_json_without_ats_keys() -> None:
    """JSON without structural ATS keys remains unknown."""
    detected = SourceDetector().detect(
        payload(text='{"repository":"x"}', extension=".json")
    )

    assert detected is SourceType.UNKNOWN


def test_detector_returns_unknown_for_csv_without_headers() -> None:
    """CSV payloads without recognized headers remain unknown."""
    detected = SourceDetector().detect(payload(text="Anika,Rao\n", extension=".csv"))

    assert detected is SourceType.UNKNOWN
