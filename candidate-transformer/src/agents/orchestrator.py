"""Agent-level orchestration above the candidate pipeline."""

from __future__ import annotations

from src.agents.intake import CandidateArtifact, IntakeAgent
from src.agents.intelligence import CandidateIntelligenceAgent
from src.agents.presentation import PresentationAgent


class AgentOrchestrator:
    """Coordinate intake, intelligence, and presentation agents."""

    def __init__(
        self,
        *,
        intake_agent: IntakeAgent | None = None,
        intelligence_agent: CandidateIntelligenceAgent | None = None,
        presentation_agent: PresentationAgent | None = None,
    ) -> None:
        """Initialize the orchestrator with injectable stateless agents."""
        self._intake_agent = intake_agent or IntakeAgent()
        self._intelligence_agent = intelligence_agent or CandidateIntelligenceAgent()
        self._presentation_agent = presentation_agent or PresentationAgent()

    def run(self, artifacts: CandidateArtifact | list[CandidateArtifact]) -> object:
        """Run the agent coordination flow."""
        raw_records = self._intake_agent.process(artifacts)
        intelligence_output = self._intelligence_agent.analyze(raw_records)
        return self._presentation_agent.present(intelligence_output)
