"""Loader-specific exception hierarchy."""

from __future__ import annotations


class LoaderError(Exception):
    """Base error for File Loading stage failures."""


class UnsupportedFileTypeError(LoaderError):
    """Raised when a loader rejects an unsupported file type."""


class FileTooLargeError(LoaderError):
    """Raised when loaded content exceeds configured file size limits."""


class FileReadError(LoaderError):
    """Raised when input content cannot be read safely."""


class CorruptedFileError(LoaderError):
    """Raised when file content is malformed or corrupted."""
