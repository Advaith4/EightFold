"""Pipeline skeleton tests."""

from pathlib import Path

import pytest
from src.adapters import AdapterRegistry
from src.config.models import (
    ApplicationSettings,
    LoggingConfig,
    LoggingSettings,
    PathSettings,
    PipelineSettings,
    ProjectConfig,
)
from src.enums import LogLevel, PipelineStatus
from src.logging import ProjectLogger
from src.pipeline import CandidatePipeline, PipelineContext, StageResult
from src.services import ServiceContainer


def _service_container(tmp_logs: str = "logs") -> ServiceContainer:
    """Create a test service container."""
    app_config = ProjectConfig(
        application=ApplicationSettings(name="Test", environment="test"),
        pipeline=PipelineSettings(
            current_sprint="Phase 1",
            status=PipelineStatus.FOUNDATION_READY,
            stages=[],
        ),
        paths=PathSettings(inputs="inputs", outputs="outputs", logs=tmp_logs),
    )
    logging_config = LoggingConfig(
        logging=LoggingSettings(
            level=LogLevel.INFO,
            directory=tmp_logs,
            file_name="application.log",
            rotation="00:00",
            retention="1 day",
            compression="zip",
            format="{time} | {level} | {message}",
        )
    )
    return ServiceContainer(
        app_config=app_config,
        logging_config=logging_config,
        logger=ProjectLogger(logging_config),
        adapter_registry=AdapterRegistry(),
    )


def test_pipeline_initializes_context_without_business_logic(tmp_path: Path) -> None:
    """Pipeline initialization returns a foundation stage result."""
    pipeline = CandidatePipeline(services=_service_container(str(tmp_path)))

    result = pipeline.initialize()

    assert isinstance(result, StageResult)
    assert result.success is True
    assert isinstance(result.payload, PipelineContext)
    assert result.payload.metadata["pipeline_initialized"] is True
    assert result.payload.raw_records == []


def test_pipeline_receives_service_container() -> None:
    """Pipeline stores constructor-injected service container."""
    services = _service_container()

    pipeline = CandidatePipeline(services=services)

    assert pipeline.services is services
    assert pipeline.services.adapter_registry is services.adapter_registry


def test_pipeline_exposes_planned_stages() -> None:
    """Pipeline exposes the planned Sprint 1 stage list."""
    pipeline = CandidatePipeline(services=_service_container())

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
    pipeline = CandidatePipeline(services=_service_container())

    with pytest.raises(NotImplementedError):
        pipeline.ingest(PipelineContext())
