"""Adapter registry tests."""

from typing import Any

import pytest
from src.adapters import AdapterRegistry
from src.exceptions import AdapterError
from src.interfaces import BaseAdapter


class _TestAdapter(BaseAdapter):
    """Test adapter implementation."""

    def __init__(self, source_type: str) -> None:
        self._source_type = source_type

    @property
    def source_type(self) -> str:
        """Return the test adapter source type."""
        return self._source_type

    def load(self) -> Any:
        """Load test data."""
        return []

    def parse(self, raw_data: Any) -> Any:
        """Parse test data."""
        return raw_data

    def metadata(self) -> dict[str, Any]:
        """Return test adapter metadata."""
        return {"source_type": self.source_type}


def test_adapter_registry_registers_and_retrieves_adapter() -> None:
    """Adapter registry returns registered adapter instances."""
    registry = AdapterRegistry()
    adapter = _TestAdapter("test")

    registry.register(adapter)

    assert registry.get("test") is adapter
    assert registry.list_registered() == ("test",)


def test_adapter_registry_rejects_duplicate_source_type() -> None:
    """Adapter registry prevents duplicate source type registrations."""
    registry = AdapterRegistry()
    registry.register(_TestAdapter("test"))

    with pytest.raises(AdapterError, match="Adapter already registered"):
        registry.register(_TestAdapter("test"))


def test_adapter_registry_unregisters_adapter() -> None:
    """Adapter registry removes adapters by source type."""
    registry = AdapterRegistry()
    registry.register(_TestAdapter("test"))

    registry.unregister("test")

    assert registry.list_registered() == ()


def test_adapter_registry_raises_for_missing_source_type() -> None:
    """Adapter registry fails clearly for missing adapters."""
    registry = AdapterRegistry()

    with pytest.raises(AdapterError, match="Adapter is not registered"):
        registry.get("missing")
