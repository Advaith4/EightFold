# ruff: noqa: UP040
"""Shared base types for domain models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TypeAlias

from pydantic import BaseModel, ConfigDict

JsonValue: TypeAlias = str | int | float | bool | None | dict[str, Any] | list[Any]


def utc_now() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)  # noqa: UP017


def ensure_timezone_aware(value: datetime, field_name: str) -> datetime:
    """Validate that a datetime includes timezone information."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value


class DomainModel(BaseModel):
    """Base configuration for immutable domain data models."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        use_enum_values=True,
    )
