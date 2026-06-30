"""Recruiter projection tab component."""

import streamlit as st
from src.agents.models import PresentationResult


def render_recruiter_tab(result: PresentationResult) -> None:
    """Render the Recruiter tab."""
    st.markdown("### Recruiter View")
    proj = result.recruiter_projection

    st.markdown("#### Identity")
    for k, v in proj.identity.items():
        if v:
            st.markdown(f"- **{k}:** {v}")

    st.markdown("#### Contact")
    for k, v in proj.contact.items():
        if v:
            st.markdown(f"- **{k}:** {v}")

    st.markdown("#### Missing Information")
    if proj.missing_information:
        st.warning(", ".join(proj.missing_information))
    else:
        st.success("No missing information.")

    st.markdown(f"**Experience:** {proj.experience_summary}")
    st.markdown(f"**Education:** {proj.education_summary}")
    st.markdown(f"**Confidence:** {proj.confidence}")
