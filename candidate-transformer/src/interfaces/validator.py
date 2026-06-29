"""Validator interface definitions."""

from abc import ABC, abstractmethod
from typing import Any


class BaseValidator(ABC):
    """Contract for validating data."""

    @abstractmethod
    def validate(self, data: Any) -> bool:
        """Validate input data.

        Args:
            data: Data to validate.

        Returns:
            True when data is valid, otherwise False.
        """
