"""Deterministic duplicate detection for raw candidate records."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse
from uuid import UUID, uuid5

from src.agents.models import CandidateGroup
from src.models import RawCandidateRecord
from src.models.base import JsonValue
from src.models.enums import SourceType


@dataclass(frozen=True)
class MatchRule:
    """Ordered duplicate detection rule."""

    name: str
    field_name: str
    reason: str


@dataclass(frozen=True)
class MatchDecision:
    """Explainable record-to-record grouping decision."""

    left_record_id: str
    right_record_id: str
    rule: str
    matched_field: str
    reason: str

    def describe(self) -> str:
        return (
            f"Matched Record: {self.left_record_id}. "
            f"Matched With: {self.right_record_id}. "
            f"Rule: {self.rule}. "
            f"Matched Fields: {self.matched_field}. "
            f"Reason: {self.reason}"
        )


@dataclass(frozen=True)
class RecordSignals:
    """Normalized identity signals extracted from one raw record."""

    emails: frozenset[str]
    phones: frozenset[str]
    github_profiles: frozenset[str]
    ats_candidate_ids: frozenset[str]
    names: frozenset[str]
    organizations: frozenset[str]
    institutions: frozenset[str]


class DuplicateDetectionAgent:
    """Group raw records using deterministic identity resolution rules."""

    id_namespace = UUID("a89a1748-46db-5a16-b82d-8f2b3d8c26bb")
    rules = (
        MatchRule(
            "Exact Email Match",
            "email",
            "Primary email addresses are identical.",
        ),
        MatchRule(
            "Exact Phone Match",
            "phone",
            "Normalized phone numbers are identical.",
        ),
        MatchRule(
            "GitHub Profile Match",
            "github",
            "GitHub profile usernames are identical.",
        ),
        MatchRule(
            "ATS Candidate ID",
            "ats_candidate_id",
            "ATS candidate identifiers are identical.",
        ),
        MatchRule(
            "Name + Organization",
            "name+organization",
            "Normalized full name and current organization are identical.",
        ),
        MatchRule(
            "Name + Educational Institution",
            "name+education",
            "Normalized full name and primary education institution are identical.",
        ),
    )

    def process(self, raw_records: list[RawCandidateRecord]) -> list[CandidateGroup]:
        """Return deterministic candidate groups for the supplied records."""
        if not raw_records:
            return []

        signals = [self._signals_for(record) for record in raw_records]
        parents = list(range(len(raw_records)))
        decisions_by_root: dict[int, list[MatchDecision]] = {}

        for left_index, left_signals in enumerate(signals):
            for right_index in range(left_index + 1, len(raw_records)):
                decision = self._match_decision(
                    raw_records[left_index],
                    left_signals,
                    raw_records[right_index],
                    signals[right_index],
                )
                if decision is None:
                    continue
                root = self._union(parents, left_index, right_index)
                decisions_by_root.setdefault(root, []).append(decision)

        grouped_indexes: dict[int, list[int]] = {}
        for index in range(len(raw_records)):
            root = self._find(parents, index)
            grouped_indexes.setdefault(root, []).append(index)

        return [
            self._build_group(
                records=tuple(raw_records[index] for index in indexes),
                signals=tuple(signals[index] for index in indexes),
                decisions=tuple(decisions_by_root.get(root, ())),
            )
            for root, indexes in grouped_indexes.items()
        ]

    def detect(self, raw_records: list[RawCandidateRecord]) -> list[CandidateGroup]:
        """Backward-compatible alias for process."""
        return self.process(raw_records)

    def _match_decision(
        self,
        left_record: RawCandidateRecord,
        left: RecordSignals,
        right_record: RawCandidateRecord,
        right: RecordSignals,
    ) -> MatchDecision | None:
        for rule in self.rules:
            if self._rule_matches(rule, left, right):
                return MatchDecision(
                    left_record_id=left_record.record_id,
                    right_record_id=right_record.record_id,
                    rule=rule.name,
                    matched_field=rule.field_name,
                    reason=rule.reason,
                )
        return None

    def _rule_matches(
        self, rule: MatchRule, left: RecordSignals, right: RecordSignals
    ) -> bool:
        if rule.name == "Exact Email Match":
            return bool(left.emails & right.emails)
        if rule.name == "Exact Phone Match":
            return bool(left.phones & right.phones)
        if rule.name == "GitHub Profile Match":
            return bool(left.github_profiles & right.github_profiles)
        if rule.name == "ATS Candidate ID":
            return bool(left.ats_candidate_ids & right.ats_candidate_ids)
        if rule.name == "Name + Organization":
            return bool(
                (left.names & right.names)
                and (left.organizations & right.organizations)
            )
        if rule.name == "Name + Educational Institution":
            return bool(
                (left.names & right.names) and (left.institutions & right.institutions)
            )
        return False

    def _build_group(
        self,
        *,
        records: tuple[RawCandidateRecord, ...],
        signals: tuple[RecordSignals, ...],
        decisions: tuple[MatchDecision, ...],
    ) -> CandidateGroup:
        matched_fields = tuple(
            dict.fromkeys(decision.matched_field for decision in decisions)
        )
        match_keys = self._match_keys(signals)
        source_types = tuple(
            dict.fromkeys(self._source_label(record) for record in records)
        )
        matching_rule = decisions[0].rule if decisions else "No Match"
        seed_parts = tuple(record.record_id for record in records) + match_keys
        return CandidateGroup(
            group_id=self._stable_id("group", *seed_parts),
            records=records,
            match_keys=match_keys,
            matched_fields=matched_fields,
            matching_rule=matching_rule,
            source_types=source_types,
            grouping_decisions=tuple(decision.describe() for decision in decisions),
        )

    def _match_keys(self, signals: tuple[RecordSignals, ...]) -> tuple[str, ...]:
        keys: list[str] = []
        for signal in signals:
            keys.extend(f"email:{value}" for value in sorted(signal.emails))
            keys.extend(f"phone:{value}" for value in sorted(signal.phones))
            keys.extend(f"github:{value}" for value in sorted(signal.github_profiles))
            keys.extend(
                f"ats_candidate_id:{value}"
                for value in sorted(signal.ats_candidate_ids)
            )
            for name in sorted(signal.names):
                keys.extend(
                    f"name_organization:{name}|{organization}"
                    for organization in sorted(signal.organizations)
                )
                keys.extend(
                    f"name_education:{name}|{institution}"
                    for institution in sorted(signal.institutions)
                )
        return tuple(dict.fromkeys(keys))

    def _signals_for(self, record: RawCandidateRecord) -> RecordSignals:
        payload = record.payload
        profile = self._dict_value(payload.get("profile"))
        return RecordSignals(
            emails=self._emails(payload, profile),
            phones=self._phones(payload),
            github_profiles=self._github_profiles(record, payload, profile),
            ats_candidate_ids=self._ats_candidate_ids(record, payload),
            names=self._names(payload, profile),
            organizations=self._organizations(payload, profile),
            institutions=self._institutions(payload),
        )

    def _emails(
        self, payload: dict[str, JsonValue], profile: dict[str, JsonValue]
    ) -> frozenset[str]:
        values = self._string_values(payload, ("email", "preferred_email"))
        values.extend(
            self._string_values(self._dict_value(payload.get("contact")), ("email",))
        )
        values.extend(self._string_values(profile, ("email",)))
        return frozenset(value.strip().casefold() for value in values if value.strip())

    def _phones(self, payload: dict[str, JsonValue]) -> frozenset[str]:
        values = self._string_values(payload, ("phone", "preferred_phone"))
        values.extend(
            self._string_values(self._dict_value(payload.get("contact")), ("phone",))
        )
        normalized = [self._normalize_phone(value) for value in values]
        return frozenset(value for value in normalized if value)

    def _github_profiles(
        self,
        record: RawCandidateRecord,
        payload: dict[str, JsonValue],
        profile: dict[str, JsonValue],
    ) -> frozenset[str]:
        values = self._string_values(
            payload,
            ("github", "github_url", "github_username", "username"),
        )
        values.extend(self._string_values(profile, ("login", "html_url")))
        if record.source_type == SourceType.GITHUB and record.source_record_id:
            values.append(record.source_record_id)
        normalized = [self._normalize_github(value) for value in values]
        return frozenset(value for value in normalized if value)

    def _ats_candidate_ids(
        self, record: RawCandidateRecord, payload: dict[str, JsonValue]
    ) -> frozenset[str]:
        if record.source_type != SourceType.ATS:
            return frozenset()
        values = self._string_values(
            payload,
            ("candidate_id", "ats_candidate_id", "applicant_id", "id"),
        )
        normalized = [self._normalize_text(value) for value in values]
        return frozenset(value for value in normalized if value)

    def _names(
        self, payload: dict[str, JsonValue], profile: dict[str, JsonValue]
    ) -> frozenset[str]:
        values = self._string_values(payload, ("full_name", "name", "display_name"))
        values.extend(self._string_values(profile, ("name",)))
        normalized = [self._normalize_text(value) for value in values]
        return frozenset(value for value in normalized if value)

    def _organizations(
        self, payload: dict[str, JsonValue], profile: dict[str, JsonValue]
    ) -> frozenset[str]:
        values = self._string_values(
            payload,
            ("company", "organization", "current_organization"),
        )
        values.extend(self._string_values(profile, ("company",)))
        experiences = payload.get("experiences", payload.get("experience"))
        for item in self._list_or_single_dict(experiences):
            values.extend(self._string_values(item, ("organization", "company")))
        normalized = [self._normalize_text(value) for value in values]
        return frozenset(value for value in normalized if value)

    def _institutions(self, payload: dict[str, JsonValue]) -> frozenset[str]:
        values: list[str] = []
        for item in self._list_or_single_dict(payload.get("education")):
            values.extend(self._string_values(item, ("institution", "school")))
        normalized = [self._normalize_text(value) for value in values]
        return frozenset(value for value in normalized if value)

    def _string_values(
        self, value: dict[str, JsonValue], keys: tuple[str, ...]
    ) -> list[str]:
        results: list[str] = []
        for key in keys:
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                results.append(candidate)
            elif isinstance(candidate, list):
                results.extend(item for item in candidate if isinstance(item, str))
        return results

    def _normalize_phone(self, value: str) -> str | None:
        digits = re.sub(r"\D+", "", value)
        if digits.startswith("00"):
            digits = digits[2:]
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]
        return digits or None

    def _normalize_github(self, value: str) -> str | None:
        candidate = value.strip().strip("/").casefold()
        if not candidate:
            return None
        parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
        if parsed.netloc.endswith("github.com"):
            path_parts = [part for part in parsed.path.split("/") if part]
            return path_parts[0] if len(path_parts) == 1 else None
        return candidate.lstrip("@")

    def _normalize_text(self, value: str) -> str | None:
        normalized = " ".join(value.strip(" \t\r\n.,;:()[]{}'").casefold().split())
        return normalized or None

    def _dict_value(self, value: JsonValue) -> dict[str, JsonValue]:
        return value if isinstance(value, dict) else {}

    def _list_or_single_dict(self, value: JsonValue) -> list[dict[str, JsonValue]]:
        if isinstance(value, dict):
            return [value]
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        return []

    def _union(self, parents: list[int], left: int, right: int) -> int:
        left_root = self._find(parents, left)
        right_root = self._find(parents, right)
        if left_root == right_root:
            return left_root
        keep = min(left_root, right_root)
        replace = max(left_root, right_root)
        parents[replace] = keep
        return keep

    def _find(self, parents: list[int], index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def _source_label(self, record: RawCandidateRecord) -> str:
        value = getattr(record.source_type, "value", record.source_type)
        return str(value)

    def _stable_id(self, prefix: str, *parts: str) -> str:
        seed = "|".join(part.strip().casefold() for part in parts)
        return f"{prefix}_{uuid5(self.id_namespace, seed).hex}"
