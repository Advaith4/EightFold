"""Supporting domain value objects and audit models."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator, model_validator

from src.models.base import DomainModel, JsonValue, ensure_timezone_aware, utc_now
from src.models.enums import DecisionType, SourceType, ValidationStatus

CANONICAL_FIELD_ROOTS = {
    "candidate_id",
    "identifiers",
    "identity",
    "contact_info",
    "location",
    "experiences",
    "education",
    "skills",
    "links",
    "summary",
    "confidence",
    "provenance",
    "decision_logs",
    "validation",
    "metadata",
    "audit_information",
}


def _field_path_has_valid_structure(value: str) -> bool:
    parts = value.split(".")
    if not parts:
        return False
    for index, part in enumerate(parts):
        base, bracket, suffix = part.partition("[")
        if not base.isidentifier() or (
            index == 0 and base not in CANONICAL_FIELD_ROOTS
        ):
            return False
        if bracket:
            if not suffix.endswith("]"):
                return False
            index_value = suffix[:-1]
            if not index_value.isdecimal():
                return False
    return True


class Confidence(DomainModel):
    """Quantified reliability for a value, entity, or candidate."""

    score: float = Field(default=0.0, ge=0.0, le=1.0)
    method: str = "unspecified"
    reasons: list[str] = Field(default_factory=list)
    calculated_at: datetime | None = None

    @field_validator("method")
    @classmethod
    def method_must_be_non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("method must be non-empty")
        return value

    @field_validator("reasons")
    @classmethod
    def reasons_must_be_non_empty(cls, value: list[str]) -> list[str]:
        if any(not reason for reason in value):
            raise ValueError("reasons must not contain empty strings")
        return value

    @field_validator("calculated_at")
    @classmethod
    def calculated_at_must_be_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None:
            return ensure_timezone_aware(value, "calculated_at")
        return value


class Provenance(DomainModel):
    """Traceability from a domain value back to source evidence."""

    provenance_id: str
    raw_record_id: str
    source_type: SourceType
    source_system: str
    source_field: str | None = None
    source_value: JsonValue = None
    source_location: str | None = None
    extracted_at: datetime = Field(default_factory=utc_now)

    @field_validator("provenance_id", "raw_record_id", "source_system")
    @classmethod
    def required_strings_must_be_non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("required provenance strings must be non-empty")
        return value

    @field_validator("extracted_at")
    @classmethod
    def extracted_at_must_be_aware(cls, value: datetime) -> datetime:
        return ensure_timezone_aware(value, "extracted_at")


class DecisionLog(DomainModel):
    """Explainable record of a deterministic transformation decision."""

    decision_id: str
    decision_type: DecisionType
    field_path: str
    input_values: list[JsonValue] = Field(default_factory=list)
    selected_value: JsonValue = None
    rejected_values: list[JsonValue] = Field(default_factory=list)
    reason: str
    rule_id: str | None = None
    provenance_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("decision_id", "field_path", "reason")
    @classmethod
    def required_strings_must_be_non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("required decision strings must be non-empty")
        return value

    @field_validator("field_path")
    @classmethod
    def field_path_must_have_valid_canonical_structure(cls, value: str) -> str:
        if not _field_path_has_valid_structure(value):
            raise ValueError("field_path must be a valid canonical field path")
        return value

    @field_validator("provenance_ids")
    @classmethod
    def provenance_ids_must_be_non_empty(cls, value: list[str]) -> list[str]:
        if any(not provenance_id for provenance_id in value):
            raise ValueError("provenance_ids must not contain empty strings")
        return value

    @field_validator("created_at")
    @classmethod
    def created_at_must_be_aware(cls, value: datetime) -> datetime:
        return ensure_timezone_aware(value, "created_at")


class Metadata(DomainModel):
    """Operational metadata for raw and canonical domain objects."""

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime | None = None
    created_by: str = "candidate-transformer"
    pipeline_version: str = "0.1.0"
    tags: list[str] = Field(default_factory=list)

    @field_validator("created_at")
    @classmethod
    def created_at_must_be_aware(cls, value: datetime) -> datetime:
        return ensure_timezone_aware(value, "created_at")

    @field_validator("updated_at")
    @classmethod
    def updated_at_must_be_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None:
            return ensure_timezone_aware(value, "updated_at")
        return value

    @field_validator("created_by", "pipeline_version")
    @classmethod
    def required_strings_must_be_non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("metadata strings must be non-empty")
        return value

    @field_validator("tags")
    @classmethod
    def tags_must_be_non_empty(cls, value: list[str]) -> list[str]:
        if any(not tag for tag in value):
            raise ValueError("tags must not contain empty strings")
        return value

    @model_validator(mode="after")
    def created_at_must_not_follow_updated_at(self) -> Metadata:
        if self.updated_at is not None and self.created_at > self.updated_at:
            raise ValueError("created_at must not be later than updated_at")
        return self


class AuditInformation(DomainModel):
    """High-level audit summary for a canonical candidate."""

    raw_record_count: int = Field(default=0, ge=0)
    provenance_count: int = Field(default=0, ge=0)
    decision_count: int = Field(default=0, ge=0)
    validation_status: ValidationStatus = ValidationStatus.NOT_VALIDATED
    projection_ready: bool = False
    generated_at: datetime = Field(default_factory=utc_now)

    @field_validator("generated_at")
    @classmethod
    def generated_at_must_be_aware(cls, value: datetime) -> datetime:
        return ensure_timezone_aware(value, "generated_at")

    @model_validator(mode="after")
    def invalid_candidates_must_not_be_projection_ready(self) -> AuditInformation:
        if self.validation_status == ValidationStatus.INVALID and self.projection_ready:
            raise ValueError(
                "projection_ready must not be true when validation is invalid"
            )
        return self


class ValidationResult(DomainModel):
    """Structured validation outcome for an entity or field."""

    is_valid: bool = False
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    info: list[str] = Field(default_factory=list)
    validated_at: datetime = Field(default_factory=utc_now)
    validator_version: str = "0.1.0"

    @field_validator("errors", "warnings", "info")
    @classmethod
    def messages_must_be_non_empty(cls, value: list[str]) -> list[str]:
        if any(not message for message in value):
            raise ValueError("validation messages must be non-empty")
        return value

    @field_validator("validated_at")
    @classmethod
    def validated_at_must_be_aware(cls, value: datetime) -> datetime:
        return ensure_timezone_aware(value, "validated_at")

    @field_validator("validator_version")
    @classmethod
    def validator_version_must_be_non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("validator_version must be non-empty")
        return value

    @model_validator(mode="after")
    def errors_make_result_invalid(self) -> ValidationResult:
        if self.errors and self.is_valid:
            raise ValueError("is_valid must be false when errors are present")
        return self
