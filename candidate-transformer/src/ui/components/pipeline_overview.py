"""Pipeline overview component."""

import streamlit as st
from src.agents.models import PresentationResult


def render_pipeline_overview(result: PresentationResult) -> None:
    """Render the pipeline processing dashboard."""
    st.subheader("Processing Dashboard")

    summary = result.pipeline_summary
    proc = result.processing_summary

    raw = summary.get("raw_record_count")
    groups = summary.get("candidate_group_count")
    canon = summary.get("canonical_candidate_count")
    decisions = proc.get("number_of_decisions")

    cols = st.columns(4)
    with cols[0]:
        st.metric("Raw Records", str(raw) if raw is not None else "-")
    with cols[1]:
        st.metric("Duplicate Groups", str(groups) if groups is not None else "-")
    with cols[2]:
        st.metric("Canonical Candidates", str(canon) if canon is not None else "-")
    with cols[3]:
        st.metric("Merge Decisions", str(decisions) if decisions is not None else "-")

    st.divider()
