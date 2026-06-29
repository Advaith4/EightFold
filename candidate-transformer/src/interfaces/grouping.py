"""Grouping engine interface definitions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.pipeline.context import PipelineContext


class IGroupingEngine(ABC):
    """Contract for future grouping engines."""

    @abstractmethod
    def group(self, context: PipelineContext) -> PipelineContext:
        """Group related records in the pipeline context.

        Args:
            context: Current pipeline context.

        Returns:
            Updated pipeline context.
        """
