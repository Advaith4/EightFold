"""Provenance tab component."""

import streamlit as st
from src.agents.models import CandidatePresentation


def render_provenance_tab(presentation: CandidatePresentation) -> None:
    """Render the Provenance tab."""
    st.markdown("### Provenance")
    if presentation.provenance:
        # Prepare list of dictionaries with desired column names
        formatted_data = []
        for row in presentation.provenance:
            formatted_data.append(
                {
                    "Field": row.field,
                    "Selected Value": row.value,
                    "Source": row.source,
                    "Reason": row.method,
                }
            )
        st.table(formatted_data)
    else:
        st.info("No provenance data available.")
