# ADR 0001: Plugin-Oriented Adapter Architecture

## Decision

Adapters are registered through `AdapterRegistry` instead of being discovered or instantiated automatically.

## Motivation

Phase 2 will introduce source-specific adapters. Explicit registration keeps construction, configuration, and lifecycle ownership outside the pipeline.

## Alternatives Considered

- Automatic adapter discovery
- Hard-coded adapter construction inside the pipeline

## Consequences

The pipeline remains decoupled from adapter implementations. Future phases must provide adapter instances explicitly.
