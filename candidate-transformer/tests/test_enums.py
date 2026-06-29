"""Infrastructure enum tests."""

from src.enums import LogLevel, PipelineStage, PipelineStatus, SourceType


def test_pipeline_status_values_are_stable() -> None:
    """Pipeline status enum exposes stable values."""
    assert PipelineStatus.FOUNDATION_READY.value == "Foundation ready"


def test_pipeline_stage_values_match_pipeline_order() -> None:
    """Pipeline stage enum preserves planned stage names."""
    assert PipelineStage.INITIALIZE.value == "initialize"
    assert PipelineStage.EXPORT.value == "export"


def test_source_type_values_are_future_ready_identifiers() -> None:
    """Source type enum exposes source identifiers without implementations."""
    assert SourceType.CSV.value == "CSV"
    assert SourceType.RESUME.value == "Resume"


def test_log_level_values_are_supported_by_logger() -> None:
    """Log level enum exposes Loguru-compatible levels."""
    assert LogLevel.INFO.value == "INFO"
