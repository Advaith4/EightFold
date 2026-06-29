"""Adapter registry for externally managed adapter instances."""

from src.exceptions import AdapterError
from src.interfaces.adapter import BaseAdapter


class AdapterRegistry:
    """Register and retrieve adapters by source type."""

    def __init__(self) -> None:
        """Initialize an empty adapter registry."""
        self._adapters: dict[str, BaseAdapter] = {}

    def register(self, adapter: BaseAdapter) -> None:
        """Register an adapter instance.

        Args:
            adapter: Adapter exposing a unique source type.

        Raises:
            AdapterError: If an adapter with the same source type exists.
        """
        source_type = adapter.source_type
        if source_type in self._adapters:
            raise AdapterError(f"Adapter already registered: {source_type}")
        self._adapters[source_type] = adapter

    def unregister(self, source_type: str) -> None:
        """Remove a registered adapter.

        Args:
            source_type: Source type to remove.

        Raises:
            AdapterError: If no adapter is registered for the source type.
        """
        if source_type not in self._adapters:
            raise AdapterError(f"Adapter is not registered: {source_type}")
        del self._adapters[source_type]

    def get(self, source_type: str) -> BaseAdapter:
        """Return a registered adapter by source type.

        Args:
            source_type: Source type key.

        Returns:
            Registered adapter instance.

        Raises:
            AdapterError: If no adapter is registered for the source type.
        """
        try:
            return self._adapters[source_type]
        except KeyError as exc:
            raise AdapterError(f"Adapter is not registered: {source_type}") from exc

    def list_registered(self) -> tuple[str, ...]:
        """Return registered source types in deterministic order."""
        return tuple(sorted(self._adapters))
