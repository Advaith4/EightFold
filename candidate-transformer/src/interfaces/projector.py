"""Projector interface definitions."""

from abc import ABC, abstractmethod
from typing import Any


class BaseProjector(ABC):
    """Contract for projecting data into an output schema."""

    @abstractmethod
    def project(self, data: Any) -> Any:
        """Project data into an output representation.

        Args:
            data: Data to project.

        Returns:
            Projected output data.
        """
