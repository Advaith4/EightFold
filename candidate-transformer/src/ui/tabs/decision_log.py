"""Decision Log tab component."""

import streamlit as st
from src.agents.models import DecisionTimeline


def render_decision_log_tab(decision_log: list[DecisionTimeline]) -> None:
    """Render the Decision Log tab."""
    st.markdown("### Decision Timeline")
    if decision_log:
        for i, log in enumerate(decision_log):
            st.success(f"✓ {log.step}")
            st.markdown(f"**Observation**: {log.observation}")
            if log.rule and log.rule != "None":
                st.markdown(f"**Rule**: {log.rule}")
            st.markdown(f"**Decision**: {log.decision}")
            if i < len(decision_log) - 1:
                st.markdown(
                    "<div style='text-align: center; margin: 10px;'><b>↓</b></div>",
                    unsafe_allow_html=True,
                )
    else:
        st.info("No decisions logged.")
