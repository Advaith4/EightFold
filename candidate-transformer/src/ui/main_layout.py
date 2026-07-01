"""Main UI layout orchestration."""

import streamlit as st

from src.agents.models import PresentationResult
from src.ui.components.pipeline_overview import render_pipeline_overview
from src.ui.tabs.candidate import render_candidate_tab
from src.ui.tabs.confidence import render_confidence_tab
from src.ui.tabs.decision_log import render_decision_log_tab
from src.ui.tabs.provenance import render_provenance_tab
from src.ui.tabs.raw_json import render_raw_json_tab
from src.ui.tabs.recruiter import render_recruiter_tab


def render_page_header() -> None:
    """Render the application header with glassmorphic aesthetic."""
    st.markdown(
        """
        <div style="padding: 0 0 2rem 0; text-align: center;">
            <h1 style="font-size: 4rem; font-weight: 800; margin-bottom: 0.2rem;
                background: -webkit-linear-gradient(45deg, #1e3a8a, #3b82f6);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;">
                CITE.ai
            </h1>
            <p style="font-size: 1.3rem; color: #334155;
                font-weight: 500; margin-bottom: 0.2rem;">
                Candidate Intelligence Transformation Engine
            </p>
            <p style="font-size: 1rem; color: #64748b;
                font-weight: 400; margin-top: 0;">
                Deterministic Multi-Source Candidate Resolution Platform
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown(
        """
        <div style="display: flex; justify-content: center; gap: 2rem;
            color: #334155; font-size: 0.9rem; flex-wrap: wrap;">
            <span>✨ Multi-source ingestion</span>
            <span>✨ Identity resolution</span>
            <span>✨ Duplicate detection</span>
            <span>✨ Canonical generation</span>
            <span>✨ Provenance tracking</span>
            <span>✨ Confidence scoring</span>
        </div>
        """,
        unsafe_allow_html=True,
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
        render_confidence_tab(presentation, result, selected_index)
    with tab4:
        render_provenance_tab(presentation)
    with tab5:
        render_recruiter_tab(presentation)
    with tab6:
        render_raw_json_tab(result.selected_candidate)

