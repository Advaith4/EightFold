"""Candidate summary component."""

import streamlit as st
from src.agents.models import PresentationResult


def render_candidate_summary(result: PresentationResult) -> None:
    """Render the Candidate Summary section."""
    st.subheader("Candidate Summary")

    header = result.header

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**Name:** {header.name}")
        st.markdown(f"**Workflow Status:** {header.workflow_status}")
        st.markdown(f"**Profile Confidence:** {header.overall_confidence_score}")

        sources = ", ".join(header.sources_used) if header.sources_used else "None"
        st.markdown(f"**Sources Used:** {sources}")

    with col2:
        email = header.primary_email or "N/A"
        phone = header.primary_phone or "N/A"
        location = header.location or "N/A"
        st.markdown(f"**Primary Email:** {email}")
        st.markdown(f"**Primary Phone:** {phone}")
        st.markdown(f"**Location:** {location}")

    st.divider()

