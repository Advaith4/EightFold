"""Raw JSON tab component."""

import streamlit as st
from src.agents.models import PresentationResult


def render_raw_json_tab(result: PresentationResult) -> None:
    """Render the Raw JSON tab."""
    st.markdown("### Raw Presentation Output")
    st.code(result.raw_json_dump, language="json")
