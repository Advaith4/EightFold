# ADR 0002: Pipeline Context

## Decision

Pipeline stages exchange a lightweight `PipelineContext` containing raw records, warnings, errors, and metadata.

## Motivation

Future stages need a shared infrastructure object without introducing candidate-specific fields during Phase 1.

## Alternatives Considered

- Passing raw dictionaries between stages
- Creating candidate-specific domain models early

## Consequences

Stage boundaries are clearer and type-safe. Business fields remain deferred to future phases.
