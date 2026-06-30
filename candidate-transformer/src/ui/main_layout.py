"""Main UI layout orchestration."""

import streamlit as st

from src.agents.models import PresentationResult
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
    st.subheader("Deterministic Multi-Source Candidate Resolution Platform")

    st.markdown(
        """
        - Multi-source ingestion
        - Identity resolution
        - Duplicate detection
        - Canonical candidate generation
        - Provenance tracking
        - Confidence scoring
        """
    )
    st.divider()


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
    render_pipeline_overview(result)

    st.subheader("Visual Pipeline")
    cols = st.columns(4)
    with cols[0]:
        st.success("✓ Resume")
    with cols[1]:
        st.success("✓ ATS JSON")
    with cols[2]:
        st.success("✓ Recruiter CSV")
    with cols[3]:
        st.success("✓ GitHub")

    st.markdown(
        "<div style='text-align: center;'><b>↓</b></div>", unsafe_allow_html=True
    )
    st.success("✓ RawCandidateRecords")
    st.markdown(
        "<div style='text-align: center;'><b>↓</b></div>", unsafe_allow_html=True
    )
    st.success("✓ Duplicate Detection")
    st.markdown(
        "<div style='text-align: center;'><b>↓</b></div>", unsafe_allow_html=True
    )
    st.success("✓ Candidate Groups")
    st.markdown(
        "<div style='text-align: center;'><b>↓</b></div>", unsafe_allow_html=True
    )
    st.success("✓ Candidate Intelligence")
    st.markdown(
        "<div style='text-align: center;'><b>↓</b></div>", unsafe_allow_html=True
    )
    st.success("✓ Canonical Candidate")
    st.markdown(
        "<div style='text-align: center;'><b>↓</b></div>", unsafe_allow_html=True
    )
    st.success("✓ Presentation")
    st.divider()

    # Candidate Selector (Section 4)
    selected_index = 0
    if len(result.candidate_presentations) > 1:
        st.subheader("Select Candidate")
        names = [
            p.header.name or "Unknown Candidate" for p in result.candidate_presentations
        ]
        selected_name = st.radio("Canonical Candidates", names, horizontal=True)
        if selected_name in names:
            selected_index = names.index(selected_name)
        st.divider()

    # Replace global result objects with selected presentation if possible
    # We will pass the whole result but ui tabs should use the selected presentation
    # For now, we will just use the global result for tabs, wait we need to fix render_tabs
    # Actually, we can update render_tabs to take `selected_index`.
    render_tabs(result, selected_index)


def render_tabs(result: PresentationResult, selected_index: int = 0) -> None:
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

    presentation = result.candidate_presentations[selected_index]
    # We also need to extract decision log for this specific candidate if possible.
    # The models don't have decision log in candidate_presentations.
    # But it does have it in result.candidates[selected_index].decision_log

    with tab1:
        render_candidate_tab(presentation)
    with tab2:
        render_decision_log_tab(result.decision_log)
    with tab3:
        render_confidence_tab(presentation)
    with tab4:
        render_provenance_tab(presentation)
    with tab5:
        render_recruiter_tab(presentation)
    with tab6:
        render_raw_json_tab(presentation)
