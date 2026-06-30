"""Domain model tests for Phase 3."""

from datetime import datetime, timezone
from typing import Any, cast

import pytest
from pydantic import ValidationError
from src.models import (
    AuditInformation,
    CanonicalCandidate,
    Confidence,
    ContactInfo,
    DecisionLog,
    DecisionType,
    Education,
    Experience,
    Identifier,
    IdentifierType,
    Identity,
    Link,
    LinkType,
    Location,
    Metadata,
    PayloadFormat,
    Provenance,
    RawCandidateRecord,
    RemotePreference,
    Skill,
    SkillCategory,
    SourceType,
    ValidationResult,
    ValidationStatus,
)

UTC_NOW = datetime(2026, 6, 30, 9, 30, tzinfo=timezone.utc)  # noqa: UP017


def test_raw_candidate_record_serializes_and_deserializes() -> None:
    """Raw records preserve source payloads and serialize to enum strings."""
    record = RawCandidateRecord(
        record_id="raw_001",
        source_type=SourceType.CSV,
        source_system="recruiter_csv",
        source_record_id="row_17",
        ingested_at=UTC_NOW,
        payload_format=PayloadFormat.CSV_ROW,
        payload={"email": "anika.rao@example.com"},
        raw_text=None,
        checksum="sha256:abc123",
        metadata=Metadata(created_at=UTC_NOW),
    )

    dumped = record.model_dump(mode="json")
    reloaded = RawCandidateRecord.model_validate(dumped)

    assert dumped["source_type"] == "CSV"
    assert dumped["payload_format"] == "csv_row"
    assert reloaded == record


def test_raw_candidate_record_rejects_empty_payload_and_naive_time() -> None:
    """Raw record model enforces payload and timezone invariants."""
    with pytest.raises(ValidationError):
        RawCandidateRecord(
            record_id="raw_001",
            source_type=SourceType.CSV,
            source_system="recruiter_csv",
            ingested_at=datetime(2026, 6, 30, 9, 30),
            payload_format=PayloadFormat.CSV_ROW,
            payload={},
            checksum="sha256:abc123",
        )


def test_confidence_validates_score_method_reasons_and_time() -> None:
    """Confidence models reject invalid score and explanation values."""
    confidence = Confidence(score=1.0, method="direct_source", reasons=["provided"])

    assert confidence.model_dump()["score"] == 1.0

    with pytest.raises(ValidationError):
        Confidence(score=1.1, method="direct_source")
    with pytest.raises(ValidationError):
        Confidence(score=0.5, method="")
    with pytest.raises(ValidationError):
        Confidence(score=0.5, method="direct_source", reasons=[""])
    with pytest.raises(ValidationError):
        Confidence(calculated_at=datetime(2026, 6, 30, 9, 30))


def test_identifier_validates_email_and_url_types() -> None:
    """Identifier model validates type-specific values."""
    email_identifier = Identifier(
        identifier_type=IdentifierType.EMAIL,
        value="anika.rao@example.com",
        normalized_value="anika.rao@example.com",
        is_primary=True,
    )
    url_identifier = Identifier(
        identifier_type=IdentifierType.GITHUB_URL,
        value="https://github.com/anikarao",
        normalized_value="https://github.com/anikarao",
    )

    assert email_identifier.identifier_type == "email"
    assert url_identifier.identifier_type == "github_url"

    with pytest.raises(ValidationError):
        Identifier(
            identifier_type=IdentifierType.EMAIL,
            value="not-email",
            normalized_value="not-email",
        )
    with pytest.raises(ValidationError):
        Identifier(
            identifier_type=IdentifierType.LINKEDIN_URL,
            value="not-a-url",
            normalized_value="not-a-url",
        )


def test_contact_info_validates_preferred_values_and_duplicates() -> None:
    """Contact info enforces syntactic and preferred-value constraints."""
    contact = ContactInfo(
        emails=["anika.rao@example.com"],
        phones=["+14155550120"],
        preferred_email="anika.rao@example.com",
        preferred_phone="+14155550120",
    )

    assert contact.preferred_email == "anika.rao@example.com"

    with pytest.raises(ValidationError):
        ContactInfo(emails=["bad-email"])
    with pytest.raises(ValidationError):
        ContactInfo(emails=["a@example.com", "a@example.com"])
    with pytest.raises(ValidationError):
        ContactInfo(emails=["a@example.com"], preferred_email="b@example.com")
    with pytest.raises(ValidationError):
        ContactInfo(phones=["+14155550120"], preferred_phone="+44155550120")


def test_location_validates_country_timezone_and_remote_preference() -> None:
    """Location supports structured components and enum preferences."""
    location = Location(
        display_name="Bengaluru, Karnataka, India",
        country_code="IN",
        timezone="Asia/Kolkata",
        remote_preference=RemotePreference.HYBRID,
    )

    assert location.remote_preference == "hybrid"

    with pytest.raises(ValidationError):
        Location(country_code="ind")
    with pytest.raises(ValidationError):
        Location(timezone="Mars/Phobos")
    with pytest.raises(ValidationError):
        Location(remote_preference=cast(Any, "flexible"))


def test_experience_and_education_validate_partial_date_order() -> None:
    """Experience and education preserve partial dates and enforce chronology."""
    experience = Experience(
        experience_id="exp_001",
        title="Senior Data Engineer",
        start_date="2022-04",
        end_date=None,
        is_current=True,
    )
    education = Education(
        education_id="edu_001",
        institution="NITK",
        start_date="2016",
        end_date="2020",
    )

    assert experience.start_date == "2022-04"
    assert education.end_date == "2020"

    with pytest.raises(ValidationError):
        Experience(
            experience_id="exp_001",
            title="Engineer",
            start_date="2024",
            end_date="2023",
        )
    with pytest.raises(ValidationError):
        Experience(experience_id="exp_001")
    with pytest.raises(ValidationError):
        Education(
            education_id="edu_001",
            institution="NITK",
            start_date="2020-13",
        )
    with pytest.raises(ValidationError):
        Education(education_id="edu_001")


def test_skill_and_link_validate_supported_values() -> None:
    """Skill and link models enforce required normalized values."""
    skill = Skill(
        skill_id="skill_python",
        name="Python",
        category=SkillCategory.PROGRAMMING_LANGUAGE,
        aliases=["python3"],
        years_experience=5.0,
        last_used="2026",
        evidence_count=2,
    )
    link = Link(
        link_type=LinkType.GITHUB,
        url="https://github.com/anikarao",
        normalized_url="https://github.com/anikarao",
        is_primary=True,
    )

    assert skill.category == "programming_language"
    assert link.link_type == "github"

    with pytest.raises(ValidationError):
        Skill(skill_id="skill_python", name="", evidence_count=0)
    with pytest.raises(ValidationError):
        Skill(skill_id="skill_python", name="Python", years_experience=-1.0)
    with pytest.raises(ValidationError):
        Link(link_type=LinkType.GITHUB, url="github.com/anikarao", normalized_url="bad")


def test_provenance_decision_metadata_audit_and_validation_models() -> None:
    """Supporting audit objects enforce their local invariants."""
    provenance = Provenance(
        provenance_id="prov_001",
        raw_record_id="raw_001",
        source_type=SourceType.RESUME,
        source_system="resume_pdf",
        source_field="skills_section",
        source_value="Python",
        extracted_at=UTC_NOW,
    )
    decision = DecisionLog(
        decision_id="dec_001",
        decision_type=DecisionType.NORMALIZATION,
        field_path="skills[0].name",
        input_values=["python3"],
        selected_value="Python",
        reason="Alias normalized to canonical skill name.",
        provenance_ids=["prov_001"],
        created_at=UTC_NOW,
    )
    metadata = Metadata(created_at=UTC_NOW, updated_at=UTC_NOW)
    audit = AuditInformation(
        raw_record_count=1,
        provenance_count=1,
        decision_count=1,
        validation_status=ValidationStatus.VALID,
        projection_ready=True,
        generated_at=UTC_NOW,
    )
    validation = ValidationResult(
        is_valid=True,
        warnings=["location.country_code is unknown"],
        validated_at=UTC_NOW,
    )

    assert provenance.source_type == "Resume"
    assert decision.decision_type == "normalization"
    assert metadata.created_by == "candidate-transformer"
    assert audit.validation_status == "valid"
    assert validation.is_valid is True

    with pytest.raises(ValidationError):
        AuditInformation(
            validation_status=ValidationStatus.INVALID, projection_ready=True
        )
    with pytest.raises(ValidationError):
        ValidationResult(is_valid=True, errors=["candidate_id missing"])
    with pytest.raises(ValidationError):
        DecisionLog(
            decision_id="dec_001",
            decision_type=DecisionType.MERGE,
            field_path="identity.full_name",
            reason="",
        )
    with pytest.raises(ValidationError):
        DecisionLog(
            decision_id="dec_002",
            decision_type=DecisionType.MERGE,
            field_path="external_schema.full_name",
            reason="External schema path is not canonical.",
        )
    with pytest.raises(ValidationError):
        DecisionLog(
            decision_id="dec_003",
            decision_type=DecisionType.MERGE,
            field_path="skills[].name",
            reason="Array index structure is invalid.",
        )


def test_identity_rejects_contact_values_in_name_fields() -> None:
    """Identity fields reject email and phone-shaped values."""
    identity = Identity(full_name="Anika Rao", headline="Senior Data Engineer")

    assert identity.full_name == "Anika Rao"

    with pytest.raises(ValidationError):
        Identity(full_name="anika.rao@example.com")
    with pytest.raises(ValidationError):
        Identity(given_name="+14155550120")


def test_canonical_candidate_enforces_collection_invariants() -> None:
    """Canonical candidate aggregate root owns duplicate and primary checks."""
    identifier = Identifier(
        identifier_type=IdentifierType.EMAIL,
        value="anika.rao@example.com",
        normalized_value="anika.rao@example.com",
        is_primary=True,
    )
    candidate = CanonicalCandidate(
        candidate_id="cand_001",
        identifiers=[identifier],
        identity=Identity(full_name="Anika Rao"),
        contact_info=ContactInfo(
            emails=["anika.rao@example.com"],
            preferred_email="anika.rao@example.com",
        ),
        experiences=[Experience(experience_id="exp_001", title="Engineer")],
        education=[Education(education_id="edu_001", institution="NITK")],
        skills=[Skill(skill_id="skill_python", name="Python")],
        links=[
            Link(
                link_type=LinkType.GITHUB,
                url="https://github.com/anikarao",
                normalized_url="https://github.com/anikarao",
                is_primary=True,
            )
        ],
        metadata=Metadata(created_at=UTC_NOW),
    )

    assert candidate.candidate_id == "cand_001"
    assert (
        candidate.model_dump(mode="json")["identifiers"][0]["identifier_type"]
        == "email"
    )

    with pytest.raises(ValidationError):
        CanonicalCandidate(
            candidate_id="cand_001", identifiers=[identifier, identifier]
        )
    with pytest.raises(ValidationError):
        CanonicalCandidate(
            candidate_id="cand_001",
            skills=[
                Skill(skill_id="skill_python", name="Python"),
                Skill(skill_id="skill_python_2", name="python"),
            ],
        )
    with pytest.raises(ValidationError):
        CanonicalCandidate(
            candidate_id="cand_001",
            links=[
                Link(
                    link_type=LinkType.GITHUB,
                    url="https://github.com/anikarao",
                    normalized_url="https://github.com/anikarao",
                ),
                Link(
                    link_type=LinkType.PORTFOLIO,
                    url="https://github.com/anikarao",
                    normalized_url="https://github.com/anikarao",
                ),
            ],
        )


def test_domain_models_are_immutable_and_compare_by_value() -> None:
    """Domain entities are immutable Pydantic values with equality semantics."""
    first = Skill(skill_id="skill_python", name="Python")
    second = Skill(skill_id="skill_python", name="Python")

    assert first == second
    with pytest.raises(ValidationError):
        first.name = "Python 3"
