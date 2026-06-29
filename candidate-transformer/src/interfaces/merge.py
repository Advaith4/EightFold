"""Merge engine interface definitions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.pipeline.context import PipelineContext


class IMergeEngine(ABC):
    """Contract for future merge engines."""

    @abstractmethod
    def merge(self, context: PipelineContext) -> PipelineContext:
        """Merge grouped records in the pipeline context.

        Args:
            context: Current pipeline context.

        Returns:
            Updated pipeline context.
        """
