"""Interface contract tests."""

import pytest
from src.interfaces import (
    BaseAdapter,
    IConfidenceCalculator,
    IGroupingEngine,
    IMergeEngine,
    INormalizer,
)


@pytest.mark.parametrize(
    "interface",
    [
        BaseAdapter,
        IConfidenceCalculator,
        IGroupingEngine,
        IMergeEngine,
        INormalizer,
    ],
)
def test_interfaces_are_abstract(interface: type[object]) -> None:
    """Core extension interfaces cannot be instantiated directly."""
    with pytest.raises(TypeError):
        interface()
