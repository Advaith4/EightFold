"""Confidence tab component."""

import streamlit as st
from src.agents.models import CandidatePresentation


def render_confidence_tab(presentation: CandidatePresentation) -> None:
    """Render the Confidence tab."""
    st.markdown("### Confidence Summary")
    conf = presentation.confidence

    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Overall Confidence", value=conf.overall_score)
        try:
            val = int(conf.overall_score.replace("%", ""))
            st.progress(val / 100.0)
        except ValueError:
            st.progress(0.0)
    with col2:
        merges = len(presentation.engineering_projection.merge_decisions)
        st.metric(label="Merge Decisions", value=str(merges))

    st.divider()

    st.markdown("#### Reason")
    if conf.details:
        for detail in conf.details:
            if "conflict" in detail.lower() or "missing" in detail.lower():
                st.markdown(f"⚠ {detail}")
            else:
                st.markdown(f"✓ {detail}")
    else:
        st.markdown(f"✓ {conf.reason}")

    st.divider()
    st.markdown(f"**Method:** {conf.method}")
    st.markdown(f"**Confidence Level:** {conf.confidence_level}")
