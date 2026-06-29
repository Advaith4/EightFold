# Candidate Intelligence Transformation Engine

Candidate Intelligence Transformation Engine is a foundation for transforming heterogeneous candidate data into a canonical, explainable, validated representation. Sprint 1 establishes the engineering baseline only: configuration, logging, package boundaries, interfaces, a pipeline skeleton, a Streamlit landing page, and initial tests.

No candidate transformation business logic is implemented in this sprint.

## Architecture Philosophy

The project follows Clean Architecture principles with explicit boundaries between UI, pipeline orchestration, services, adapters, configuration, and shared models. The foundation favors small focused classes, constructor-based dependency injection, explicit typing, fail-fast configuration errors, graceful runtime failures, and reusable interfaces.

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

## Roadmap

Sprint 1 creates the engineering foundation. Future sprints can add concrete adapters, canonical candidate models, normalization, grouping, merge behavior, confidence scoring, provenance tracking, schema projection, validation, exports, and audit logging.

## Future Sprints

- Source adapters for Recruiter CSV, ATS JSON, and resume documents
- Canonical candidate model and schema evolution
- Normalization and entity grouping
- Candidate merge and confidence scoring
- Provenance-aware validation and projection
- Explainable audit outputs
