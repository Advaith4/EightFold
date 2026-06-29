# Candidate Intelligence Transformation Engine

Candidate Intelligence Transformation Engine is a foundation for transforming heterogeneous candidate data into a canonical, explainable, validated representation. Sprint 1 establishes the engineering baseline only: configuration, logging, package boundaries, interfaces, a pipeline skeleton, a Streamlit landing page, and initial tests.

No candidate transformation business logic is implemented in this sprint.

## Architecture Philosophy

The project follows Clean Architecture principles with explicit boundaries between UI, pipeline orchestration, services, adapters, configuration, and shared models. The foundation favors small focused classes, constructor-based dependency injection, explicit typing, fail-fast configuration errors, graceful runtime failures, and reusable interfaces.

## Architecture Overview

```text
Streamlit UI
    |
    v
Application Shell (app.py)
    |
    +--> ConfigurationLoader
    +--> ProjectLogger
    +--> AdapterRegistry
    |
    v
CandidatePipeline
    |
    v
PipelineContext
```

The application shell wires dependencies together. The pipeline receives dependencies through constructor injection and moves a lightweight `PipelineContext` through future stages. Interfaces define extension points, while concrete business behavior is intentionally absent until later phases.

## Module Responsibilities

- `src/config`: YAML configuration loading, caching, and graceful reload behavior.
- `src/logging`: Loguru-based console and rotating file logger setup.
- `src/pipeline`: Pipeline orchestration skeleton and `PipelineContext` state object.
- `src/adapters`: Adapter registry for externally created adapters.
- `src/interfaces`: Abstract contracts for adapters, validators, projectors, rules, services, and future processing engines.
- `src/ui`: Minimal Streamlit developer status page.
- `src/exceptions`: Application-specific exception hierarchy.
- `src/constants`: Reserved package for future static mapping and priority values.


## Dependency Graph

```text
UI
|
v
Application Shell
|
v
ServiceContainer
|
+--> Configuration
+--> Logging
+--> AdapterRegistry
|
v
Pipeline
|
v
PipelineContext / StageResult
|
v
Interfaces
|
v
Adapters / Services / Models / Utilities
```

Dependencies flow inward through explicit constructor injection. The pipeline receives infrastructure through `ServiceContainer` and does not construct adapters, loggers, or configuration loaders internally.

## Stable Public APIs

The following interfaces are considered stable for Phase 2 extension work:

- `BaseAdapter`
- `AdapterRegistry`
- `PipelineContext`
- `CandidatePipeline`

Future changes should preserve these contracts unless a formal migration is documented.

## Folder Structure

```text
candidate-transformer/
├── app.py
├── pyproject.toml
├── README.md
├── .gitignore
├── .env.example
├── config/
│   ├── default.yaml
│   └── logging.yaml
├── docs/
├── inputs/
├── outputs/
├── logs/
├── tests/
└── src/
    ├── adapters/
    ├── constants/
    ├── interfaces/
    ├── models/
    ├── pipeline/
    ├── services/
    ├── config/
    ├── logging/
    ├── exceptions/
    ├── utils/
    └── ui/
```

## Technology Stack

- Python 3.12+
- Streamlit
- Pydantic v2
- Loguru
- PyYAML
- Pytest
- Poetry
- Black
- Ruff
- Mypy

## Installation

```bash
poetry install
```

## Running Locally

```bash
poetry run streamlit run app.py
```

## Testing

```bash
poetry run pytest
```

## Engineering Principles

- Preserve clean boundaries between UI, orchestration, configuration, logging, and future domain behavior.
- Inject dependencies explicitly instead of constructing hidden runtime collaborators inside the pipeline.
- Keep Phase 1 free of candidate-specific transformation logic.
- Favor small interfaces and lightweight data structures that future phases can extend.
- Fail fast for invalid configuration and fail clearly for missing registry entries.

## Phase Roadmap

- Phase 1: Engineering foundation, configuration, logging, interfaces, registry, pipeline context, and developer UI.
- Phase 2: Source adapter implementations and raw source ingestion contracts.
- Phase 3: Canonical candidate model, mapping, and normalization.
- Phase 4: Grouping, merge behavior, confidence scoring, and provenance.
- Phase 5: Projection, validation, exports, and audit reporting.

## Roadmap

Sprint 1 creates the engineering foundation. Future sprints can add concrete adapters, canonical candidate models, normalization, grouping, merge behavior, confidence scoring, provenance tracking, schema projection, validation, exports, and audit logging.

## Future Sprints

- Source adapters for Recruiter CSV, ATS JSON, and resume documents
- Canonical candidate model and schema evolution
- Normalization and entity grouping
- Candidate merge and confidence scoring
- Provenance-aware validation and projection
- Explainable audit outputs

