# ruff: noqa: UP040
"""Abstract contracts for file loaders."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO, TextIO, TypeAlias

from src.loaders.models import FilePayload

UploadedContent: TypeAlias = bytes | str | Path | BinaryIO | TextIO


class BaseLoader(ABC):
    """Contract for technical file loading into a FilePayload."""

    @abstractmethod
    def load(self, source: UploadedContent) -> FilePayload:
        """Load bounded technical content without business interpretation."""
