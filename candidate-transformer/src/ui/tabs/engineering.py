"""Engineering projection tab component."""

import streamlit as st
from src.agents.models import PresentationResult


def render_engineering_tab(result: PresentationResult) -> None:
    """Render the Engineering tab."""
    st.markdown("### Engineering View")
    proj = result.engineering_projection

    st.markdown("#### Raw Sources")
    st.write(proj.raw_sources)

    st.markdown("#### Merge Decisions")
    st.write(proj.merge_decisions)

    st.markdown(f"**Confidence Details:** {proj.confidence_details}")
    st.markdown(f"**Available Fields:** {', '.join(proj.available_fields)}")
    st.markdown(f"**Processing Summary:** {proj.processing_summary}")
