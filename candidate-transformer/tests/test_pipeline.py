"""Pipeline skeleton tests."""

import pytest

from src.pipeline import CandidatePipeline
from src.pipeline.engine import PipelineStageResult


def test_pipeline_initializes_without_business_logic() -> None:
    """Pipeline initialization returns a foundation-stage result."""
    pipeline = CandidatePipeline()

    result = pipeline.initialize()

    assert result == PipelineStageResult(stage="initialize", status="initialized")


def test_pipeline_exposes_planned_stages() -> None:
    """Pipeline exposes the planned Sprint 1 stage list."""
    pipeline = CandidatePipeline()

    assert pipeline.stages == (
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


def test_future_pipeline_stages_are_not_implemented() -> None:
    """Future business stages remain intentionally unimplemented."""
    pipeline = CandidatePipeline()

    with pytest.raises(NotImplementedError):
        pipeline.ingest()
