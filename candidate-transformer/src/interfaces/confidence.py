"""Confidence calculator interface definitions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.pipeline.context import PipelineContext


class IConfidenceCalculator(ABC):
    """Contract for future confidence calculation engines."""

    @abstractmethod
    def calculate(self, context: PipelineContext) -> PipelineContext:
        """Calculate confidence information for pipeline context data.

        Args:
            context: Current pipeline context.

        Returns:
            Updated pipeline context.
        """
