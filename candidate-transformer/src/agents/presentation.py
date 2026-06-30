"""Presentation orchestration shell."""

from __future__ import annotations


class PresentationAgent:
    """Future owner of validation, projection, export, and presentation."""

    def present(self, candidate_output: object) -> object:
        """Return the supplied object unchanged for this sprint."""
        return candidate_output
