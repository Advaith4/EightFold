"""Pipeline skeleton for future transformation stages."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PipelineStageResult:
    """Placeholder result for a pipeline stage."""

    stage: str
    status: str = "not_implemented"


class CandidatePipeline:
    """Coordinate candidate transformation pipeline stages."""

    @property
    def stages(self) -> tuple[str, ...]:
        """Return the planned pipeline stage names."""
        return (
            "initialize",
            "ingest",
            "map",
            "normalize",
            "group",
            "merge",
            "project",
            "validate",
            "export",
        )

    def initialize(self) -> PipelineStageResult:
        """Initialize pipeline dependencies without running business logic."""
        return PipelineStageResult(stage="initialize", status="initialized")

    def ingest(self) -> Any:
        """Placeholder for source ingestion."""
        raise NotImplementedError("Ingestion is planned for a future sprint.")

    def map(self) -> Any:
        """Placeholder for source-to-canonical mapping."""
        raise NotImplementedError("Mapping is planned for a future sprint.")

    def normalize(self) -> Any:
        """Placeholder for candidate normalization."""
        raise NotImplementedError("Normalization is planned for a future sprint.")

    def group(self) -> Any:
        """Placeholder for candidate grouping."""
        raise NotImplementedError("Grouping is planned for a future sprint.")

    def merge(self) -> Any:
        """Placeholder for candidate merging."""
        raise NotImplementedError("Merging is planned for a future sprint.")

    def project(self) -> Any:
        """Placeholder for output projection."""
        raise NotImplementedError("Projection is planned for a future sprint.")

    def validate(self) -> Any:
        """Placeholder for output validation."""
        raise NotImplementedError("Validation is planned for a future sprint.")

    def export(self) -> Any:
        """Placeholder for output export."""
        raise NotImplementedError("Export is planned for a future sprint.")
