"""GitHub source payload models."""

from __future__ import annotations

from pydantic import ConfigDict, Field, field_validator

from src.models.base import DomainModel, JsonValue


class GitHubPayload(DomainModel):
    """Raw public GitHub API data for a profile source."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    profile: dict[str, JsonValue]
    repositories: list[dict[str, JsonValue]] = Field(default_factory=list)
    languages: dict[str, dict[str, int]] = Field(default_factory=dict)

    @field_validator("profile")
    @classmethod
    def profile_must_not_be_empty(
        cls, value: dict[str, JsonValue]
    ) -> dict[str, JsonValue]:
        if not value:
            raise ValueError("profile must not be empty")
        return value
