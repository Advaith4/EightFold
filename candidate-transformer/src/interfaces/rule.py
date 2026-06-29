"""Rule interface definitions."""

from abc import ABC, abstractmethod
from typing import Any


class BaseRule(ABC):
    """Contract for evaluating a rule against input data."""

    @abstractmethod
    def evaluate(self, data: Any) -> bool:
        """Evaluate a rule.

        Args:
            data: Data to evaluate.

        Returns:
            True when the rule passes, otherwise False.
        """
