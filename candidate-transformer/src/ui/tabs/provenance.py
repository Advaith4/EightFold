"""Provenance tab component."""

import pandas as pd  # type: ignore
import streamlit as st
from src.agents.models import PresentationResult


def render_provenance_tab(result: PresentationResult) -> None:
    """Render the Provenance tab."""
    st.markdown("### Provenance")
    if result.provenance:
        data = [row.model_dump() for row in result.provenance]
        st.dataframe(pd.DataFrame(data), use_container_width=True)
    else:
        st.info("No provenance data available.")
