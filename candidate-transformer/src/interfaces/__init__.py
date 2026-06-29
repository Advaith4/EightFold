"""Abstract interfaces used across the application."""

from src.interfaces.adapter import BaseAdapter
from src.interfaces.projector import BaseProjector
from src.interfaces.rule import BaseRule
from src.interfaces.service import BaseService
from src.interfaces.validator import BaseValidator

__all__ = [
    "BaseAdapter",
    "BaseProjector",
    "BaseRule",
    "BaseService",
    "BaseValidator",
]
