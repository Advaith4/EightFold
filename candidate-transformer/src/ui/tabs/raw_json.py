"""Raw JSON tab component."""

import streamlit as st
from src.agents.models import CandidatePresentation


def render_raw_json_tab(presentation: CandidatePresentation) -> None:
    """Render the Raw JSON tab."""
    st.markdown("### Raw Presentation Output")
    st.info("Displaying JSON representation of the final Canonical Candidate object.")
    st.json(presentation.model_dump(mode="json"))
