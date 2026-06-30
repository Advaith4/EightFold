"""Data formatting helpers for UI."""


def format_percentage(value: float | None) -> str:
    """Format a float value between 0.0 and 1.0 as a percentage."""
    if value is None:
        return "N/A"
    return f"{value * 100:.0f}%"


def safe_join(items: tuple[str, ...] | list[str] | None, sep: str = ", ") -> str:
    """Safely join a list of strings, returning 'None' if empty."""
    if not items:
        return "None"
    return sep.join(items)
