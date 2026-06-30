"""Candidate domain entities from the domain model specification."""

from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator, model_validator

from src.models.base import DomainModel, JsonValue, ensure_timezone_aware, utc_now
from src.models.common import (
    AuditInformation,
    Confidence,
    DecisionLog,
    Metadata,
    Provenance,
    ValidationResult,
)
from src.models.enums import (
    IdentifierType,
    LinkType,
    PayloadFormat,
    RemotePreference,
    SkillCategory,
    SourceType,
)

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_LIKE_PATTERN = re.compile(r"\+?\d[\d\s().-]{6,}\d")
PARTIAL_DATE_PATTERN = re.compile(
    r"^\d{4}(?:-(?:0[1-9]|1[0-2])(?:-(?:0[1-9]|[12]\d|3[01]))?)?$"
)
COUNTRY_CODE_PATTERN = re.compile(r"^[A-Z]{2}$")


def _require_non_empty(value: str, field_name: str) -> str:
    if not value:
        raise ValueError(f"{field_name} must be non-empty")
    return value


def _validate_email(value: str, field_name: str) -> str:
    if not EMAIL_PATTERN.match(value):
        raise ValueError(f"{field_name} must be a valid email address")
    return value


def _validate_url(value: str, field_name: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{field_name} must be a valid URL")
    return value


def _validate_partial_date(value: str | None, field_name: str) -> str | None:
    if value is not None and not PARTIAL_DATE_PATTERN.match(value):
        raise ValueError(f"{field_name} must be YYYY, YYYY-MM, or YYYY-MM-DD")
    return value


def _date_key(value: str) -> tuple[int, int, int]:
    parts = [int(part) for part in value.split("-")]
    year = parts[0]
    month = parts[1] if len(parts) > 1 else 1
    day = parts[2] if len(parts) > 2 else 1
    return (year, month, day)


class RawCandidateRecord(DomainModel):
    """Immutable source record captured before canonical interpretation."""

    record_id: str
    source_type: SourceType
    source_system: str
    source_record_id: str | None = None
    ingested_at: datetime = Field(default_factory=utc_now)
    payload_format: PayloadFormat
    payload: dict[str, JsonValue]
    raw_text: str | None = None
    checksum: str
    metadata: Metadata = Field(default_factory=Metadata)

    @field_validator("record_id", "source_system", "checksum")
    @classmethod
    def required_strings_must_be_non_empty(cls, value: str) -> str:
        return _require_non_empty(value, "raw record field")

    @field_validator("ingested_at")
    @classmethod
    def ingested_at_must_be_aware(cls, value: datetime) -> datetime:
        return ensure_timezone_aware(value, "ingested_at")

    @field_validator("payload")
    @classmethod
    def payload_must_not_be_empty(
        cls, value: dict[str, JsonValue]
    ) -> dict[str, JsonValue]:
        if not value:
            raise ValueError("payload must not be empty")
        return value


class Identifier(DomainModel):
    """Stable identity evidence for grouping, deduplication, and traceability."""

    identifier_type: IdentifierType
    value: str
    normalized_value: str
    source_system: str | None = None
    is_primary: bool = False
    confidence: Confidence = Field(default_factory=Confidence)
    provenance: list[Provenance] = Field(default_factory=list)

    @field_validator("value", "normalized_value")
    @classmethod
    def identifier_values_must_be_non_empty(cls, value: str) -> str:
        return _require_non_empty(value, "identifier value")

    @model_validator(mode="after")
    def validate_identifier_format(self) -> Identifier:
        if self.identifier_type == IdentifierType.EMAIL:
            _validate_email(self.value, "value")
            _validate_email(self.normalized_value, "normalized_value")
        if self.identifier_type in {
            IdentifierType.LINKEDIN_URL,
            IdentifierType.GITHUB_URL,
        }:
            _validate_url(self.value, "value")
            _validate_url(self.normalized_value, "normalized_value")
        return self


class ContactInfo(DomainModel):
    """Candidate communication channels."""

    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    preferred_email: str | None = None
    preferred_phone: str | None = None
    confidence: Confidence = Field(default_factory=Confidence)
    provenance: list[Provenance] = Field(default_factory=list)

    @field_validator("emails")
    @classmethod
    def emails_must_be_valid_and_unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("duplicate emails are not allowed")
        for email in value:
            _validate_email(email, "emails")
        return value

    @field_validator("phones")
    @classmethod
    def phones_must_be_unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("duplicate phones are not allowed")
        if any(not phone for phone in value):
            raise ValueError("phones must not contain empty strings")
        return value

    @field_validator("preferred_email")
    @classmethod
    def preferred_email_must_be_valid(cls, value: str | None) -> str | None:
        if value is not None:
            return _validate_email(value, "preferred_email")
        return value

    @model_validator(mode="after")
    def preferred_values_must_exist_in_collections(self) -> ContactInfo:
        if self.preferred_email is not None and self.preferred_email not in self.emails:
            raise ValueError("preferred_email must exist in emails")
        if self.preferred_phone is not None and self.preferred_phone not in self.phones:
            raise ValueError("preferred_phone must exist in phones")
        return self


class Location(DomainModel):
    """Structured geographic or remote work location."""

    display_name: str | None = None
    city: str | None = None
    region: str | None = None
    country: str | None = None
    country_code: str | None = None
    postal_code: str | None = None
    timezone: str | None = None
    remote_preference: RemotePreference | None = None
    confidence: Confidence = Field(default_factory=Confidence)
    provenance: list[Provenance] = Field(default_factory=list)

    @field_validator("country_code")
    @classmethod
    def country_code_must_be_iso_alpha_2(cls, value: str | None) -> str | None:
        if value is not None and not COUNTRY_CODE_PATTERN.match(value):
            raise ValueError("country_code must be two uppercase letters")
        return value

    @field_validator("timezone")
    @classmethod
    def timezone_must_be_valid(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                ZoneInfo(value)
            except ZoneInfoNotFoundError as exc:
                raise ValueError("timezone must be a valid IANA timezone") from exc
        return value


class Skill(DomainModel):
    """Normalized skill, tool, language, platform, or competency."""

    skill_id: str
    name: str
    raw_name: str | None = None
    category: SkillCategory | None = None
    aliases: list[str] = Field(default_factory=list)
    years_experience: float | None = Field(default=None, ge=0.0)
    last_used: str | None = None
    evidence_count: int = Field(default=0, ge=0)
    confidence: Confidence = Field(default_factory=Confidence)
    provenance: list[Provenance] = Field(default_factory=list)

    @field_validator("skill_id", "name")
    @classmethod
    def required_strings_must_be_non_empty(cls, value: str) -> str:
        return _require_non_empty(value, "skill field")

    @field_validator("aliases")
    @classmethod
    def aliases_must_be_non_empty(cls, value: list[str]) -> list[str]:
        if any(not alias for alias in value):
            raise ValueError("aliases must not contain empty strings")
        return value

    @field_validator("last_used")
    @classmethod
    def last_used_must_be_partial_date(cls, value: str | None) -> str | None:
        return _validate_partial_date(value, "last_used")


class Experience(DomainModel):
    """Professional role, project, internship, contract, or employment entry."""

    experience_id: str
    title: str | None = None
    organization: str | None = None
    location: Location | None = None
    start_date: str | None = None
    end_date: str | None = None
    is_current: bool = False
    description: str | None = None
    highlights: list[str] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    confidence: Confidence = Field(default_factory=Confidence)
    provenance: list[Provenance] = Field(default_factory=list)

    @field_validator("experience_id")
    @classmethod
    def experience_id_must_be_non_empty(cls, value: str) -> str:
        return _require_non_empty(value, "experience_id")

    @field_validator("start_date", "end_date")
    @classmethod
    def dates_must_be_partial_dates(cls, value: str | None) -> str | None:
        return _validate_partial_date(value, "experience date")

    @field_validator("highlights")
    @classmethod
    def highlights_must_be_non_empty(cls, value: list[str]) -> list[str]:
        if any(not highlight for highlight in value):
            raise ValueError("highlights must not contain empty strings")
        return value

    @model_validator(mode="after")
    def validate_experience_entry(self) -> Experience:
        if self.title is None and self.organization is None:
            raise ValueError("title or organization must exist for an experience entry")
        if (
            self.start_date is not None
            and self.end_date is not None
            and _date_key(self.start_date) > _date_key(self.end_date)
        ):
            raise ValueError("start_date must not be after end_date")
        return self


class Education(DomainModel):
    """Formal education, degree, certificate, or training entry."""

    education_id: str
    institution: str | None = None
    credential: str | None = None
    field_of_study: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    grade: str | None = None
    confidence: Confidence = Field(default_factory=Confidence)
    provenance: list[Provenance] = Field(default_factory=list)

    @field_validator("education_id")
    @classmethod
    def education_id_must_be_non_empty(cls, value: str) -> str:
        return _require_non_empty(value, "education_id")

    @field_validator("start_date", "end_date")
    @classmethod
    def dates_must_be_partial_dates(cls, value: str | None) -> str | None:
        return _validate_partial_date(value, "education date")

    @model_validator(mode="after")
    def validate_education_entry(self) -> Education:
        if (
            self.institution is None
            and self.credential is None
            and self.field_of_study is None
        ):
            raise ValueError(
                "institution, credential, or field_of_study must exist "
                "for an education entry"
            )
        if (
            self.start_date is not None
            and self.end_date is not None
            and _date_key(self.start_date) > _date_key(self.end_date)
        ):
            raise ValueError("start_date must not be after end_date")
        return self


class Link(DomainModel):
    """External profile, portfolio, repository, resume, or source URL."""

    link_type: LinkType
    url: str
    normalized_url: str
    label: str | None = None
    is_primary: bool = False
    confidence: Confidence = Field(default_factory=Confidence)
    provenance: list[Provenance] = Field(default_factory=list)

    @field_validator("url", "normalized_url")
    @classmethod
    def urls_must_be_valid(cls, value: str) -> str:
        return _validate_url(_require_non_empty(value, "url"), "url")


class Identity(DomainModel):
    """Candidate name and identity attributes."""

    full_name: str | None = None
    given_name: str | None = None
    middle_name: str | None = None
    family_name: str | None = None
    preferred_name: str | None = None
    headline: str | None = None
    confidence: Confidence = Field(default_factory=Confidence)
    provenance: list[Provenance] = Field(default_factory=list)

    @field_validator(
        "full_name",
        "given_name",
        "middle_name",
        "family_name",
        "preferred_name",
        "headline",
    )
    @classmethod
    def name_fields_must_not_contain_contact_values(
        cls, value: str | None
    ) -> str | None:
        if value is None:
            return value
        if EMAIL_PATTERN.search(value):
            raise ValueError("identity fields must not contain email addresses")
        if PHONE_LIKE_PATTERN.search(value):
            raise ValueError("identity fields must not contain phone numbers")
        return value


class CanonicalCandidate(DomainModel):
    """Aggregate root for the internal canonical candidate profile."""

    candidate_id: str
    identifiers: list[Identifier] = Field(default_factory=list)
    identity: Identity = Field(default_factory=Identity)
    contact_info: ContactInfo = Field(default_factory=ContactInfo)
    location: Location | None = None
    experiences: list[Experience] = Field(default_factory=list)
    duplicate_experiences: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    duplicate_education: list[Education] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    links: list[Link] = Field(default_factory=list)
    summary: str | None = None
    confidence: Confidence = Field(default_factory=Confidence)
    provenance: list[Provenance] = Field(default_factory=list)
    decision_logs: list[DecisionLog] = Field(default_factory=list)
    validation: ValidationResult | None = None
    metadata: Metadata = Field(default_factory=Metadata)
    audit_information: AuditInformation | None = None

    @field_validator("candidate_id")
    @classmethod
    def candidate_id_must_be_non_empty(cls, value: str) -> str:
        return _require_non_empty(value, "candidate_id")

    @model_validator(mode="after")
    def enforce_candidate_collection_invariants(self) -> CanonicalCandidate:
        identifier_keys: set[tuple[str, str]] = set()
        primary_identifier_types: set[str] = set()
        for identifier in self.identifiers:
            key = (str(identifier.identifier_type), identifier.normalized_value)
            if key in identifier_keys:
                raise ValueError("duplicate identifiers are not allowed")
            identifier_keys.add(key)
            if identifier.is_primary:
                identifier_type = str(identifier.identifier_type)
                if identifier_type in primary_identifier_types:
                    raise ValueError("only one primary identifier is allowed per type")
                primary_identifier_types.add(identifier_type)

        skill_names: set[str] = set()
        for skill in self.skills:
            normalized_name = skill.name.casefold()
            if normalized_name in skill_names:
                raise ValueError("duplicate skill names are not allowed")
            skill_names.add(normalized_name)

        link_urls: set[str] = set()
        primary_link_types: set[str] = set()
        for link in self.links:
            if link.normalized_url in link_urls:
                raise ValueError("duplicate normalized URLs are not allowed")
            link_urls.add(link.normalized_url)
            if link.is_primary:
                link_type = str(link.link_type)
                if link_type in primary_link_types:
                    raise ValueError("only one primary link is allowed per type")
                primary_link_types.add(link_type)

        experience_ids: set[str] = set()
        for experience in self.experiences:
            if experience.experience_id in experience_ids:
                raise ValueError("experience_id must be unique within a candidate")
            experience_ids.add(experience.experience_id)

        education_ids: set[str] = set()
        for education in self.education:
            if education.education_id in education_ids:
                raise ValueError("education_id must be unique within a candidate")
            education_ids.add(education.education_id)

        return self
