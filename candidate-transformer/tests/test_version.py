"""Version metadata tests."""

from src.__version__ import __version__


def test_version_module_exposes_project_version() -> None:
    """Version module provides a single runtime version value."""
    assert __version__ == "0.1.0"
