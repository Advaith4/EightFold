"""Pipeline context tests."""

from src.pipeline import PipelineContext


def test_pipeline_context_defaults_are_isolated() -> None:
    """Pipeline context default collections are not shared."""
    first = PipelineContext()
    second = PipelineContext()

    first.warnings.append("first warning")
    first.metadata["key"] = "value"

    assert second.warnings == []
    assert second.metadata == {}
