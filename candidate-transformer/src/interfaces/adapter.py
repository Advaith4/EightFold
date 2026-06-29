"""Adapter interface definitions."""

from abc import ABC, abstractmethod
from typing import Any


class BaseAdapter(ABC):
    """Contract for loading and parsing external source data."""

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Return the adapter source type.

        Returns:
            Stable source type identifier for the adapter.
        """

    @abstractmethod
    def load(self) -> Any:
        """Load raw data from an external source.

        Returns:
            Source-specific raw data.
        """

    @abstractmethod
    def parse(self, raw_data: Any) -> Any:
        """Parse raw source data into an intermediate representation.

        Args:
            raw_data: Source-specific data returned by load.

        Returns:
            Parsed source data.
        """

    @abstractmethod
    def metadata(self) -> dict[str, Any]:
        """Return adapter metadata.

        Returns:
            Adapter metadata such as source type and version.
        """
