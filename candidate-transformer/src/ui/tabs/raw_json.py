"""Raw JSON tab component."""

import streamlit as st
from src.agents.models import PresentationResult


def render_raw_json_tab(result: PresentationResult) -> None:
    """Render the Raw JSON tab."""
    st.markdown("### Raw Records")
    raw_records = [
        record.model_dump(mode="json")
        for group in result.candidate_groups
        for record in group.records
    ]
    if raw_records:
        st.json(raw_records)
    else:
        st.info("No raw records available.")

    st.markdown("### Candidate Groups")
    if result.candidate_groups:
        st.json([group.model_dump(mode="json") for group in result.candidate_groups])
    else:
        st.info("No candidate groups available.")

    st.markdown("### Canonical Candidates")
    if result.candidates:
        st.json([candidate.model_dump(mode="json") for candidate in result.candidates])
    else:
        st.info("No canonical candidates available.")

    st.markdown("### Raw Presentation Output")
    st.code(result.raw_json_dump, language="json")