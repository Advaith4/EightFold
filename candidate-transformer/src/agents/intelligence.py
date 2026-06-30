"""Deterministic candidate intelligence and canonical merge logic."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from uuid import UUID, uuid5

from src.agents.models import (
    CandidateGroup,
    DecisionContext,
    IntelligenceResult,
    WorkflowStatus,
)
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
    Provenance,
    RawCandidateRecord,
    Skill,
    SourceType,
)
from src.models.base import JsonValue


@dataclass(frozen=True)
class FieldEvidence:
    """Explicit raw value available for a canonical field."""

    field_path: str
    value: JsonValue
    record: RawCandidateRecord
    record_index: int
    source_field: str


@dataclass(frozen=True)
class SourceConfidencePolicy:
    """Configurable deterministic confidence policy by source."""

    source_scores: tuple[tuple[str, float], ...] = (
        (SourceType.ATS.value, 0.95),
        (SourceType.RESUME.value, 0.85),
        (SourceType.GITHUB.value, 0.80),
        (SourceType.CSV.value, 0.75),
        (SourceType.LINKEDIN.value, 0.80),
    )
    default_score: float = 0.50
    method: str = "deterministic_source_precedence"

    def score_for(self, source_label: str) -> float:
        """Return the configured deterministic score for a source."""
        return dict(self.source_scores).get(source_label, self.default_score)


class CandidateIntelligenceAgent:
    """Map and merge raw candidate records with deterministic reasoning."""

    id_namespace = UUID("8e7fa96b-81c7-5f94-b18b-4f9738f96f84")

    required_fields = (
        "identity.full_name",
        "contact_info.emails",
        "contact_info.phones",
        "education",
        "skills",
    )
    important_fields = (
        "full_name",
        "email",
        "phone",
        "education",
        "experience",
        "skills",
        "certifications",
    )
    source_precedence = {
        SourceType.ATS.value: 0,
        SourceType.RESUME.value: 1,
        SourceType.GITHUB.value: 2,
        SourceType.CSV.value: 3,
        SourceType.LINKEDIN.value: 4,
    }

    def __init__(self, confidence_policy: SourceConfidencePolicy | None = None) -> None:
        """Initialize deterministic reasoning policies."""
        self._confidence_policy = confidence_policy or SourceConfidencePolicy()

    def process(self, raw_records: list[RawCandidateRecord]) -> IntelligenceResult:
        """Produce canonical candidates and explainable decision context."""
        groups = self.group_records(raw_records)
        if not groups:
            return self._build_result([]).model_copy(
                update={"candidate_groups": (), "canonical_candidates": ()}
            )

        group_results = [self._build_result(list(group.records)) for group in groups]
        candidates = tuple(result.selected_candidate for result in group_results)
        primary = group_results[0]
        return primary.model_copy(
            update={
                "candidate_groups": tuple(groups),
                "canonical_candidates": candidates,
                "selected_candidate": candidates[0],
                "canonical_candidate": candidates[0],
            }
        )

    def analyze(self, raw_records: list[RawCandidateRecord]) -> IntelligenceResult:
        """Backward-compatible orchestration entry point."""
        return self.process(raw_records)

    def group_records(
        self, raw_records: list[RawCandidateRecord]
    ) -> list[CandidateGroup]:
        """Create one compatibility group per raw record without deduplication."""
        return [
            CandidateGroup(
                group_id=self._stable_id("group", record.record_id),
                records=(record,),
                match_keys=(f"record:{record.record_id}",),
            )
            for record in raw_records
        ]

    def _build_result(
        self, raw_records: list[RawCandidateRecord]
    ) -> IntelligenceResult:
        evidence = self._collect_evidence(raw_records)
        provenance_by_key = self._build_provenance(evidence)
        selected, decision_logs, conflicting_fields = self._merge_scalar_fields(
            evidence=evidence,
            provenance_by_key=provenance_by_key,
        )
        candidate = self._build_candidate(
            raw_records=raw_records,
            evidence=evidence,
            selected=selected,
            provenance_by_key=provenance_by_key,
            decision_logs=decision_logs,
        )
        context = self._build_decision_context(
            raw_records=raw_records,
            evidence=evidence,
            conflicting_fields=conflicting_fields,
            candidate=candidate,
        )
        return IntelligenceResult(
            decision_context=context,
            candidate_groups=(),
            canonical_candidates=(candidate,),
            selected_candidate=candidate,
            canonical_candidate=candidate,
        )

    def _collect_evidence(
        self, raw_records: list[RawCandidateRecord]
    ) -> dict[str, list[FieldEvidence]]:
        evidence: dict[str, list[FieldEvidence]] = defaultdict(list)
        for index, record in enumerate(raw_records):
            for item in self._evidence_from_record(record, index):
                evidence[item.field_path].append(item)
        return dict(evidence)

    def _evidence_from_record(
        self, record: RawCandidateRecord, record_index: int
    ) -> list[FieldEvidence]:
        payload = record.payload
        profile = self._dict_value(payload.get("profile"))
        items: list[FieldEvidence] = []
        self._add_string_evidence(
            items,
            "identity.full_name",
            self._first_string(payload, ("full_name", "name", "display_name"))
            or self._first_string(profile, ("name",)),
            record,
            record_index,
            "name",
        )
        self._add_string_evidence(
            items,
            "contact_info.preferred_email",
            self._first_string(payload, ("email", "preferred_email"))
            or self._first_string(profile, ("email",)),
            record,
            record_index,
            "email",
        )
        self._add_string_evidence(
            items,
            "contact_info.preferred_phone",
            self._first_string(payload, ("phone", "preferred_phone")),
            record,
            record_index,
            "phone",
        )
        self._add_string_evidence(
            items,
            "location.display_name",
            self._first_string(payload, ("location",))
            or self._first_string(profile, ("location",)),
            record,
            record_index,
            "location",
        )
        self._add_string_evidence(
            items,
            "summary",
            self._first_string(payload, ("summary",))
            or self._first_string(profile, ("bio",)),
            record,
            record_index,
            "summary",
        )
        return items

    def _build_provenance(
        self, evidence: dict[str, list[FieldEvidence]]
    ) -> dict[tuple[str, int], Provenance]:
        provenance: dict[tuple[str, int], Provenance] = {}
        for field_path, values in evidence.items():
            for index, item in enumerate(values):
                provenance[(field_path, index)] = Provenance(
                    provenance_id=self._provenance_id(item, index),
                    raw_record_id=item.record.record_id,
                    source_type=item.record.source_type,
                    source_system=item.record.source_system,
                    source_field=item.source_field,
                    source_value=item.value,
                    source_location=item.record.source_record_id,
                    extracted_at=item.record.ingested_at,
                )
        return provenance

    def _merge_scalar_fields(
        self,
        *,
        evidence: dict[str, list[FieldEvidence]],
        provenance_by_key: dict[tuple[str, int], Provenance],
    ) -> tuple[dict[str, FieldEvidence], list[DecisionLog], tuple[str, ...]]:
        selected: dict[str, FieldEvidence] = {}
        decision_logs: list[DecisionLog] = []
        conflicting_fields: list[str] = []
        for field_path, values in sorted(evidence.items()):
            if not values:
                continue
            chosen = min(
                enumerate(values),
                key=lambda item: (
                    self._source_priority(item[1].record),
                    item[1].record_index,
                ),
            )
            chosen_index, chosen_evidence = chosen
            selected[field_path] = chosen_evidence
            unique_values = tuple(dict.fromkeys(item.value for item in values))
            rejected = [
                value for value in unique_values if value != chosen_evidence.value
            ]
            decision_type = DecisionType.MERGE if rejected else DecisionType.MAPPING
            if rejected:
                conflicting_fields.append(field_path)
            decision_logs.append(
                DecisionLog(
                    decision_id=self._decision_id(field_path),
                    decision_type=decision_type,
                    field_path=field_path,
                    input_values=list(unique_values),
                    selected_value=chosen_evidence.value,
                    rejected_values=rejected,
                    reason=self._decision_reason(
                        field_path=field_path,
                        values=values,
                        chosen_evidence=chosen_evidence,
                        rejected_values=rejected,
                    ),
                    rule_id="source_precedence_v1",
                    provenance_ids=[
                        provenance_by_key[(field_path, chosen_index)].provenance_id
                    ],
                    created_at=chosen_evidence.record.ingested_at,
                )
            )
        return selected, decision_logs, tuple(conflicting_fields)

    def _build_candidate(
        self,
        *,
        raw_records: list[RawCandidateRecord],
        evidence: dict[str, list[FieldEvidence]],
        selected: dict[str, FieldEvidence],
        provenance_by_key: dict[tuple[str, int], Provenance],
        decision_logs: list[DecisionLog],
    ) -> CanonicalCandidate:
        all_provenance = list(provenance_by_key.values())
        identity = Identity(
            full_name=self._selected_string(selected, "identity.full_name"),
            confidence=self._confidence_for_selection(
                selected.get("identity.full_name")
            ),
            provenance=self._selected_provenance(
                "identity.full_name", evidence, selected, provenance_by_key
            ),
        )
        contact_info = ContactInfo(
            emails=self._unique_values(
                evidence.get("contact_info.preferred_email", [])
            ),
            phones=self._unique_values(
                evidence.get("contact_info.preferred_phone", [])
            ),
            preferred_email=self._selected_string(
                selected, "contact_info.preferred_email"
            ),
            preferred_phone=self._selected_string(
                selected, "contact_info.preferred_phone"
            ),
            confidence=self._confidence_for_selection(
                selected.get("contact_info.preferred_email")
                or selected.get("contact_info.preferred_phone")
            ),
            provenance=self._selected_provenance(
                "contact_info.preferred_email", evidence, selected, provenance_by_key
            )
            + self._selected_provenance(
                "contact_info.preferred_phone", evidence, selected, provenance_by_key
            ),
        )
        location_value = self._selected_string(selected, "location.display_name")
        location = (
            Location(
                display_name=location_value,
                confidence=self._confidence_for_selection(
                    selected.get("location.display_name")
                ),
                provenance=self._selected_provenance(
                    "location.display_name", evidence, selected, provenance_by_key
                ),
            )
            if location_value is not None
            else None
        )
        experiences = self._build_experiences(raw_records)
        education = self._build_education(raw_records)
        skills = self._build_skills(raw_records)
        links = self._build_links(raw_records)

        base_confidence = self._confidence_for_records(raw_records)
        penalty = 0.0
        bonus = 0.0

        if not experiences:
            penalty += 0.15
        else:
            bonus += 0.05

        if not education:
            penalty += 0.15
        else:
            bonus += 0.05

        if not skills:
            penalty += 0.10
        else:
            bonus += 0.01

        if not contact_info.preferred_email and not contact_info.preferred_phone:
            penalty += 0.10

        if links:
            bonus += 0.01

        final_score = min(0.99, max(0.0, base_confidence.score - penalty + bonus))
        confidence = Confidence(
            score=final_score,
            method="Dynamic Completeness Scoring",
        )

        candidate = CanonicalCandidate(
            candidate_id=self._candidate_id(raw_records, selected),
            identifiers=self._build_identifiers(
                raw_records, evidence, provenance_by_key
            ),
            identity=identity,
            contact_info=contact_info,
            location=location,
            experiences=experiences,
            education=education,
            skills=skills,
            links=links,
            summary=self._selected_string(selected, "summary"),
            confidence=confidence,
            provenance=all_provenance,
            decision_logs=decision_logs,
            audit_information=AuditInformation(
                raw_record_count=len(raw_records),
                provenance_count=len(all_provenance),
                decision_count=len(decision_logs),
            ),
        )
        return candidate

    def _build_decision_context(
        self,
        *,
        raw_records: list[RawCandidateRecord],
        evidence: dict[str, list[FieldEvidence]],
        conflicting_fields: tuple[str, ...],
        candidate: CanonicalCandidate,
    ) -> DecisionContext:
        source_order = tuple(self._source_label(record) for record in raw_records)
        source_counts = Counter(source_order)
        record_counts = Counter(record.record_id for record in raw_records)
        duplicate_sources = tuple(
            dict.fromkeys(
                source for source in source_order if source_counts[source] > 1
            )
        )
        duplicate_record_ids = tuple(
            record_id for record_id, count in record_counts.items() if count > 1
        )
        available_fields = self._available_fields_by_source(raw_records)
        missing_fields = self._missing_important_fields(available_fields, candidate)
        return DecisionContext(
            record_count=len(raw_records),
            detected_sources=tuple(dict.fromkeys(source_order)),
            duplicate_sources=duplicate_sources,
            duplicate_record_ids=duplicate_record_ids,
            required_fields=self.required_fields,
            missing_important_fields=missing_fields,
            conflicting_fields=conflicting_fields,
            available_fields_by_source=available_fields,
            workflow_status=self._workflow_status(missing_fields, conflicting_fields),
            decision_log=self._context_log(
                source_order=source_order,
                available_fields=available_fields,
                missing_fields=missing_fields,
                conflicting_fields=conflicting_fields,
                duplicate_sources=duplicate_sources,
                duplicate_record_ids=duplicate_record_ids,
                decision_count=len(candidate.decision_logs),
            ),
        )

    def _build_identifiers(
        self,
        raw_records: list[RawCandidateRecord],
        evidence: dict[str, list[FieldEvidence]],
        provenance_by_key: dict[tuple[str, int], Provenance],
    ) -> list[Identifier]:
        identifiers: list[Identifier] = []
        seen: set[tuple[IdentifierType, str]] = set()
        for field_path, identifier_type in (
            ("contact_info.preferred_email", IdentifierType.EMAIL),
            ("contact_info.preferred_phone", IdentifierType.PHONE),
        ):
            for index, item in enumerate(evidence.get(field_path, [])):
                if not isinstance(item.value, str):
                    continue
                normalized = item.value.strip().casefold()
                key = (identifier_type, normalized)
                if key in seen:
                    continue
                seen.add(key)
                identifiers.append(
                    Identifier(
                        identifier_type=identifier_type,
                        value=item.value,
                        normalized_value=normalized,
                        source_system=item.record.source_system,
                        confidence=self._confidence_for_selection(item),
                        provenance=[provenance_by_key[(field_path, index)]],
                    )
                )
        for record in raw_records:
            if record.source_record_id is None:
                continue
            normalized = f"{record.source_system}:{record.source_record_id}".casefold()
            key = (IdentifierType.SOURCE_RECORD_ID, normalized)
            if key in seen:
                continue
            seen.add(key)
            identifiers.append(
                Identifier(
                    identifier_type=IdentifierType.SOURCE_RECORD_ID,
                    value=record.source_record_id,
                    normalized_value=normalized,
                    source_system=record.source_system,
                    confidence=self._confidence_for_records([record]),
                    provenance=[],
                )
            )
        return identifiers

    def _build_links(self, raw_records: list[RawCandidateRecord]) -> list[Link]:
        links: list[Link] = []
        seen: set[str] = set()
        for record in raw_records:
            payload = record.payload
            profile = self._dict_value(payload.get("profile"))
            candidates = (
                (
                    LinkType.GITHUB,
                    self._first_string(payload, ("github_url",))
                    or self._first_string(profile, ("html_url",)),
                ),
                (LinkType.LINKEDIN, self._first_string(payload, ("linkedin_url",))),
                (
                    LinkType.PORTFOLIO,
                    self._first_string(payload, ("portfolio_url", "blog"))
                    or self._first_string(profile, ("blog",)),
                ),
                (LinkType.RESUME, self._first_string(payload, ("resume_url",))),
            )
            for link_type, url in candidates:
                if url is None or url in seen:
                    continue
                seen.add(url)
                links.append(
                    Link(
                        link_type=link_type,
                        url=url,
                        normalized_url=url,
                        confidence=self._confidence_for_records([record]),
                        provenance=[],
                    )
                )
        return links

    def _build_skills(self, raw_records: list[RawCandidateRecord]) -> list[Skill]:
        skills: list[Skill] = []
        seen: set[str] = set()
        for record in raw_records:
            raw_skills = self._list_value(record.payload.get("skills"))
            skill_names = [
                name
                for raw_skill in raw_skills
                if (name := self._skill_name(raw_skill))
            ]
            skill_names.extend(self._github_language_names(record))
            for name in skill_names:
                key = name.casefold()
                if key in seen:
                    continue
                seen.add(key)
                skills.append(
                    Skill(
                        skill_id=self._stable_id("skill", name.casefold()),
                        name=name,
                        raw_name=name,
                        confidence=self._confidence_for_records([record]),
                        provenance=[],
                    )
                )
        return skills

    def _github_language_names(self, record: RawCandidateRecord) -> list[str]:
        if self._source_label(record) != SourceType.GITHUB.value:
            return []
        languages = record.payload.get("languages")
        if not isinstance(languages, dict):
            return []
        names: list[str] = []
        for language_map in languages.values():
            if not isinstance(language_map, dict):
                continue
            for language_name in language_map:
                if isinstance(language_name, str) and language_name.strip():
                    names.append(language_name)
        return names

    def _build_education(
        self, raw_records: list[RawCandidateRecord]
    ) -> list[Education]:
        education: list[Education] = []
        for record in raw_records:
            for raw_item in self._list_or_single_dict(record.payload.get("education")):
                institution = self._first_string(raw_item, ("institution", "school"))
                credential = self._first_string(raw_item, ("credential", "degree"))
                field_of_study = self._first_string(
                    raw_item, ("field_of_study", "major")
                )
                start_date = self._first_string(raw_item, ("start_date", "start"))
                end_date = self._first_string(raw_item, ("end_date", "end"))
                if (
                    institution is None
                    and credential is None
                    and field_of_study is None
                ):
                    continue
                education.append(
                    Education(
                        education_id=self._stable_id(
                            "education",
                            institution or "",
                            credential or "",
                            start_date or "",
                        ),
                        institution=institution,
                        credential=credential,
                        field_of_study=field_of_study,
                        start_date=start_date,
                        end_date=end_date,
                        confidence=self._confidence_for_records([record]),
                        provenance=[],
                    )
                )
        return education

    def _build_experiences(
        self, raw_records: list[RawCandidateRecord]
    ) -> list[Experience]:
        experiences: list[Experience] = []
        for record in raw_records:
            raw_experiences = record.payload.get(
                "experiences", record.payload.get("experience")
            )
            for raw_item in self._list_or_single_dict(raw_experiences):
                title = self._first_string(raw_item, ("title", "role"))
                organization = self._first_string(raw_item, ("organization", "company"))
                start_date = self._first_string(raw_item, ("start_date", "start"))
                end_date = self._first_string(raw_item, ("end_date", "end"))
                if title is None and organization is None:
                    continue
                experiences.append(
                    Experience(
                        experience_id=self._stable_id(
                            "experience",
                            organization or "",
                            title or "",
                            start_date or "",
                        ),
                        title=title,
                        organization=organization,
                        start_date=start_date,
                        end_date=end_date,
                        description=self._first_string(raw_item, ("description",)),
                        confidence=self._confidence_for_records([record]),
                        provenance=[],
                    )
                )
        return experiences

    def _source_label(self, record: RawCandidateRecord) -> str:
        source_type = record.source_type
        value = getattr(source_type, "value", source_type)
        return str(value)

    def _source_priority(self, record: RawCandidateRecord) -> int:
        return self.source_precedence.get(self._source_label(record), 99)

    def _confidence_for_records(self, records: list[RawCandidateRecord]) -> Confidence:
        if not records:
            return Confidence(score=0.0, method=self._confidence_policy.method)
        score = max(
            self._confidence_policy.score_for(self._source_label(record))
            for record in records
        )
        return Confidence(
            score=score,
            method=self._confidence_policy.method,
            reasons=["Assigned from source reliability policy."],
        )

    def _confidence_for_selection(self, evidence: FieldEvidence | None) -> Confidence:
        if evidence is None:
            return Confidence(score=0.0, method="deterministic_source_precedence")
        return self._confidence_for_records([evidence.record])

    def _candidate_id(
        self,
        raw_records: list[RawCandidateRecord],
        selected: dict[str, FieldEvidence],
    ) -> str:
        if not raw_records:
            return self._stable_id("candidate", "empty")
        email = self._selected_string(selected, "contact_info.preferred_email") or ""
        full_name = self._selected_string(selected, "identity.full_name") or ""
        sources = "|".join(self._source_label(record) for record in raw_records)
        fallback = "|".join(record.record_id for record in raw_records)
        return self._stable_id("candidate", sources, email, full_name, fallback)

    def _selected_string(
        self, selected: dict[str, FieldEvidence], field_path: str
    ) -> str | None:
        item = selected.get(field_path)
        return item.value if item is not None and isinstance(item.value, str) else None

    def _selected_provenance(
        self,
        field_path: str,
        evidence: dict[str, list[FieldEvidence]],
        selected: dict[str, FieldEvidence],
        provenance_by_key: dict[tuple[str, int], Provenance],
    ) -> list[Provenance]:
        selected_item = selected.get(field_path)
        if selected_item is None:
            return []
        for index, item in enumerate(evidence.get(field_path, [])):
            if item == selected_item:
                return [provenance_by_key[(field_path, index)]]
        return []

    def _unique_values(self, values: list[FieldEvidence]) -> list[str]:
        unique: list[str] = []
        seen: set[str] = set()
        for item in values:
            if not isinstance(item.value, str):
                continue
            if item.value in seen:
                continue
            seen.add(item.value)
            unique.append(item.value)
        return unique

    def _available_fields_by_source(
        self, raw_records: list[RawCandidateRecord]
    ) -> dict[str, tuple[str, ...]]:
        fields_by_source: dict[str, set[str]] = defaultdict(set)
        for record in raw_records:
            source = self._source_label(record)
            fields_by_source[source].update(record.payload)
            if record.raw_text is not None:
                fields_by_source[source].add("raw_text")
        return {
            source: tuple(sorted(fields))
            for source, fields in sorted(fields_by_source.items())
        }

    def _missing_important_fields(
        self,
        available_fields: dict[str, tuple[str, ...]],
        candidate: CanonicalCandidate,
    ) -> tuple[str, ...]:
        all_fields = {field for fields in available_fields.values() for field in fields}
        missing: list[str] = []
        checks = {
            "full_name": candidate.identity.full_name is not None,
            "email": bool(candidate.contact_info.emails),
            "phone": bool(candidate.contact_info.phones),
            "education": bool(candidate.education),
            "experience": bool(candidate.experiences),
            "skills": bool(candidate.skills),
            "certifications": "certifications" in all_fields,
        }
        for field in self.important_fields:
            if not checks[field]:
                missing.append(field)
        return tuple(missing)

    def _workflow_status(
        self,
        missing_fields: tuple[str, ...],
        conflicting_fields: tuple[str, ...],
    ) -> WorkflowStatus:
        if conflicting_fields:
            return WorkflowStatus.REQUIRES_HUMAN_REVIEW
        if missing_fields:
            return WorkflowStatus.INCOMPLETE_PROFILE
        return WorkflowStatus.READY_FOR_PRESENTATION

    def _context_log(
        self,
        *,
        source_order: tuple[str, ...],
        available_fields: dict[str, tuple[str, ...]],
        missing_fields: tuple[str, ...],
        conflicting_fields: tuple[str, ...],
        duplicate_sources: tuple[str, ...],
        duplicate_record_ids: tuple[str, ...],
        decision_count: int,
    ) -> tuple[str, ...]:
        if not source_order:
            return (
                "Received 0 candidate records.",
                "No sources detected.",
                f"Workflow status: {WorkflowStatus.INCOMPLETE_PROFILE.value}.",
                "No conflicts analyzed yet.",
            )
        lines = [
            f"Received {len(source_order)} candidate record(s).",
            "Received sources: " + ", ".join(dict.fromkeys(source_order)),
        ]
        for source, fields in available_fields.items():
            field_list = ", ".join(fields) if fields else "none"
            lines.append(f"{source} contains: {field_list}.")
        lines.append(
            "Duplicate sources detected: " + ", ".join(duplicate_sources)
            if duplicate_sources
            else "No duplicate sources detected."
        )
        if duplicate_record_ids:
            lines.append(
                "Duplicate records detected: " + ", ".join(duplicate_record_ids)
            )
        missing = ", ".join(missing_fields) if missing_fields else "none"
        lines.append(f"Missing: {missing}.")
        conflicts = ", ".join(conflicting_fields) if conflicting_fields else "none"
        lines.append(f"Conflicting fields: {conflicts}.")
        status = self._workflow_status(missing_fields, conflicting_fields)
        lines.append(f"Workflow status: {status.value}.")
        lines.append(f"Structured decisions generated: {decision_count}.")
        return tuple(lines)

    def _decision_reason(
        self,
        *,
        field_path: str,
        values: list[FieldEvidence],
        chosen_evidence: FieldEvidence,
        rejected_values: list[JsonValue],
    ) -> str:
        sources = tuple(
            dict.fromkeys(self._source_label(item.record) for item in values)
        )
        source_text = " and ".join(sources)
        affected_field = self._affected_field(field_path)
        observation = f"{affected_field} present in {source_text}"
        reason = (
            "Multiple explicit values detected"
            if rejected_values
            else "Single explicit value detected"
        )
        rule = (
            "Prefer ATS over Resume over GitHub; "
            "keep first encountered for equal priority"
        )
        selected_source = self._source_label(chosen_evidence.record)
        decision = f"Selected {selected_source} value"
        return (
            f"Observation: {observation}. "
            f"Reason: {reason}. "
            f"Rule Applied: {rule}. "
            f"Decision: {decision}. "
            f"Affected Field: {affected_field}."
        )

    def _affected_field(self, field_path: str) -> str:
        return field_path.split(".")[-1]

    def _provenance_id(self, evidence: FieldEvidence, index: int) -> str:
        return self._safe_id(
            f"prov_{evidence.record.record_id}_{evidence.field_path}_{index}"
        )

    def _decision_id(self, field_path: str) -> str:
        return self._safe_id(f"decision_{field_path}")

    def _stable_id(self, prefix: str, *parts: str) -> str:
        seed = "|".join(part.strip().casefold() for part in parts)
        return f"{prefix}_{uuid5(self.id_namespace, seed).hex}"

    def _safe_id(self, value: str) -> str:
        return "".join(character if character.isalnum() else "_" for character in value)

    def _add_string_evidence(
        self,
        items: list[FieldEvidence],
        field_path: str,
        value: str | None,
        record: RawCandidateRecord,
        record_index: int,
        source_field: str,
    ) -> None:
        if value is None:
            return
        items.append(
            FieldEvidence(
                field_path=field_path,
                value=value,
                record=record,
                record_index=record_index,
                source_field=source_field,
            )
        )

    def _first_string(
        self, value: dict[str, JsonValue], keys: tuple[str, ...]
    ) -> str | None:
        for key in keys:
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate
        return None

    def _dict_value(self, value: JsonValue) -> dict[str, JsonValue]:
        return value if isinstance(value, dict) else {}

    def _list_value(self, value: JsonValue) -> list[JsonValue]:
        return value if isinstance(value, list) else []

    def _list_or_single_dict(self, value: JsonValue) -> list[dict[str, JsonValue]]:
        if isinstance(value, dict):
            return [value]
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        return []

    def _skill_name(self, value: JsonValue) -> str | None:
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, dict):
            return self._first_string(value, ("name", "skill", "raw_name"))
        return None
