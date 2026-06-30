"""Minimal deterministic candidate intelligence observations."""

from __future__ import annotations

from collections import Counter, defaultdict

from src.agents.models import DecisionContext
from src.models import RawCandidateRecord


class CandidateIntelligenceAgent:
    """Produce deterministic observations from raw candidate records."""

    important_fields = (
        "email",
        "phone",
        "education",
        "experience",
        "skills",
        "certifications",
    )

    def analyze(self, raw_records: list[RawCandidateRecord]) -> DecisionContext:
        """Analyze raw records without modifying, mapping, or merging data."""
        source_order = tuple(self._source_label(record) for record in raw_records)
        source_counts = Counter(source_order)
        duplicate_sources = tuple(
            source for source in source_order if source_counts[source] > 1
        )
        unique_duplicate_sources = tuple(dict.fromkeys(duplicate_sources))
        available_fields = self._available_fields_by_source(raw_records)
        missing_fields = self._missing_important_fields(available_fields)
        return DecisionContext(
            record_count=len(raw_records),
            detected_sources=tuple(dict.fromkeys(source_order)),
            duplicate_sources=unique_duplicate_sources,
            missing_important_fields=missing_fields,
            available_fields_by_source=available_fields,
            decision_log=self._decision_log(
                source_order=source_order,
                available_fields=available_fields,
                missing_fields=missing_fields,
                duplicate_sources=unique_duplicate_sources,
            ),
        )

    def _source_label(self, record: RawCandidateRecord) -> str:
        source_type = record.source_type
        value = getattr(source_type, "value", source_type)
        return str(value)

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
        self, available_fields: dict[str, tuple[str, ...]]
    ) -> tuple[str, ...]:
        all_fields = {field for fields in available_fields.values() for field in fields}
        return tuple(
            field for field in self.important_fields if field not in all_fields
        )

    def _decision_log(
        self,
        *,
        source_order: tuple[str, ...],
        available_fields: dict[str, tuple[str, ...]],
        missing_fields: tuple[str, ...],
        duplicate_sources: tuple[str, ...],
    ) -> tuple[str, ...]:
        if not source_order:
            return (
                "Received 0 candidate records.",
                "No sources detected.",
                "No conflicts analyzed yet.",
            )
        lines = [
            f"Received {len(source_order)} candidate record(s).",
            "Received sources: " + ", ".join(dict.fromkeys(source_order)),
        ]
        for source, fields in available_fields.items():
            field_list = ", ".join(fields) if fields else "none"
            lines.append(f"{source} contains: {field_list}.")
        if duplicate_sources:
            lines.append("Duplicate sources detected: " + ", ".join(duplicate_sources))
        else:
            lines.append("No duplicate sources detected.")
        missing = ", ".join(missing_fields) if missing_fields else "none"
        lines.append(f"Missing: {missing}.")
        lines.append("No conflicts analyzed yet.")
        return tuple(lines)
