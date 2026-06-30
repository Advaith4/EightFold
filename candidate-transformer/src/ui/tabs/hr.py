"""HR projection tab component."""

import streamlit as st
from src.agents.models import PresentationResult


def render_hr_tab(result: PresentationResult) -> None:
    """Render the HR tab."""
    st.markdown("### HR View")
    proj = result.hr_projection

    st.markdown("#### Candidate Timeline")
    if proj.candidate_timeline:
        for event in proj.candidate_timeline:
            st.markdown(f"- {event}")
    else:
        st.info("No timeline events.")

    st.markdown(f"**Provenance Summary:** {proj.provenance_summary}")
    st.markdown(f"**Decision Summary:** {proj.decision_summary}")

    if proj.missing_fields:
        st.warning(f"Missing Fields: {', '.join(proj.missing_fields)}")
