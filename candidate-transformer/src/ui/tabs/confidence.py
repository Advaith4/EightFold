"""Confidence tab component."""

import streamlit as st
from src.agents.models import PresentationResult


def render_confidence_tab(result: PresentationResult) -> None:
    """Render the Confidence tab."""
    st.markdown("### Confidence Summary")
    conf = result.confidence

    st.metric(label="Overall Confidence", value=conf.overall_score)
    st.markdown(f"**Confidence Level:** {conf.confidence_level}")
    st.markdown(f"**Method:** {conf.method}")
    
    if conf.details:
        st.markdown("#### Scoring Breakdown")
        for detail in conf.details:
            st.markdown(f"- {detail}")
    else:
        st.markdown(f"**Reason:** {conf.reason}")
