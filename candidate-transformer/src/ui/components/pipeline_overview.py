"""Pipeline overview component."""

import streamlit as st


def render_pipeline_overview() -> None:
    """Render the pipeline processing stages.

    Note: Since we are running the backend synchronously, if we have a result,
    it means all stages completed successfully.
    """
    st.subheader("Pipeline Overview")

    # In Phase 1, we just show them as completed since this runs post-processing
    col1, col2, col3 = st.columns(3)

    with col1:
        st.success("✅ Intake Agent")
    with col2:
        st.success("✅ Candidate Intelligence Agent")
    with col3:
        st.success("✅ Presentation Agent")

    st.divider()
