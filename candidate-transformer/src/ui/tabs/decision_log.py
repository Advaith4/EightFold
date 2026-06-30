"""Decision Log tab component."""

import streamlit as st
from src.agents.models import PresentationResult


def render_decision_log_tab(result: PresentationResult) -> None:
    """Render the Decision Log tab."""
    st.markdown("### Decision Timeline")
    if result.decision_log:
        for log in result.decision_log:
            st.markdown(f"**{log.step}**: ✓ {log.observation}")
    else:
        st.info("No decisions logged.")
