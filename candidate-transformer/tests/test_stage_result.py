"""Stage result tests."""

from src.pipeline import StageResult


def test_stage_result_defaults_are_isolated() -> None:
    """Stage result default collections are not shared."""
    first = StageResult(success=True)
    second = StageResult(success=True)

    first.warnings.append("warning")
    first.errors.append("error")

    assert second.warnings == []
    assert second.errors == []
