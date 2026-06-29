"""Service interface definitions."""

from abc import ABC, abstractmethod
from typing import Any


class BaseService(ABC):
    """Contract for application services."""

    @abstractmethod
    def execute(self, data: Any | None = None) -> Any:
        """Execute service behavior.

        Args:
            data: Optional input data for the service.

        Returns:
            Service-specific result.
        """
