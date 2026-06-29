"""Abstract interfaces used across the application."""

from src.interfaces.adapter import BaseAdapter
from src.interfaces.confidence import IConfidenceCalculator
from src.interfaces.grouping import IGroupingEngine
from src.interfaces.merge import IMergeEngine
from src.interfaces.normalizer import INormalizer
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
    "IConfidenceCalculator",
    "IGroupingEngine",
    "IMergeEngine",
    "INormalizer",
]
