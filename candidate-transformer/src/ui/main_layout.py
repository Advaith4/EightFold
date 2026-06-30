"""Main UI layout orchestration."""

import streamlit as st

from src.agents.models import PresentationResult
from src.ui.components.candidate_summary import render_candidate_summary
from src.ui.components.pipeline_overview import render_pipeline_overview
from src.ui.components.status_banner import render_status_banner
from src.ui.tabs.candidate import render_candidate_tab
from src.ui.tabs.confidence import render_confidence_tab
from src.ui.tabs.decision_log import render_decision_log_tab
from src.ui.tabs.provenance import render_provenance_tab
from src.ui.tabs.raw_json import render_raw_json_tab
from src.ui.tabs.recruiter import render_recruiter_tab


def render_page_header() -> None:
    """Render the application header."""
    st.title("Candidate Intelligence Transformation Engine")
    st.subheader("Explainable Multi-Agent Candidate Intelligence")
    st.write("Demonstration application for the enterprise AI platform.")
    st.divider()


def render_tabs(result: PresentationResult) -> None:
    """Render the tabbed interface (Section 3)."""
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        [
            "Candidate",
            "Decision Log",
            "Confidence",
            "Provenance",
            "Recruiter View",
            "Raw JSON",
        ]
    )

    with tab1:
        render_candidate_tab(result)
    with tab2:
        render_decision_log_tab(result)
    with tab3:
        render_confidence_tab(result)
    with tab4:
        render_provenance_tab(result)
    with tab5:
        render_recruiter_tab(result)
    with tab6:
        render_raw_json_tab(result)


def render_main_layout(result: PresentationResult | None) -> None:
    """Orchestrate the rendering of the main page sections.

    Args:
        result: The output from the CandidateProcessingService, if analysis is complete.
    """
    render_page_header()

    if result is None:
        st.info(
            "Upload candidate files in the sidebar and "
            "click 'Analyze Candidate' to begin."
        )
        return

    # Render the status banner suggestion
    render_status_banner(result)

    # Section 1
    render_pipeline_overview()

    # Section 2
    render_candidate_summary(result)

    # Section 3
    render_tabs(result)
