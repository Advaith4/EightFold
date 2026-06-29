"""Normalizer interface definitions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.pipeline.context import PipelineContext


class INormalizer(ABC):
    """Contract for future normalization engines."""

    @abstractmethod
    def normalize(self, context: PipelineContext) -> PipelineContext:
        """Normalize pipeline context data.

        Args:
            context: Current pipeline context.

        Returns:
            Updated pipeline context.
        """
