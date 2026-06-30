"""Provenance tab component."""

import streamlit as st
from src.agents.models import CandidatePresentation, ProvenanceRow


def render_provenance_tab(presentation: CandidatePresentation) -> None:
    """Render the Provenance tab."""
    st.markdown("### Provenance")
    if presentation.provenance:
        # Group rows by Field
        grouped: dict[str, list[ProvenanceRow]] = {}
        for row in presentation.provenance:
            if row.field not in grouped:
                grouped[row.field] = []
            grouped[row.field].append(row)
            
        for field, rows in grouped.items():
            st.markdown(f"#### {field}")
            formatted_data = []
            for row in rows:
                formatted_data.append(
                    {
                        "Canonical Value": row.value,
                        "Source": row.source,
                        "Original Value": row.original_value or "",
                        "Status": row.status or "",
                        "Rule": row.method,
                        "Confidence": row.confidence if row.confidence != "N/A" else "",
                    }
                )
            st.table(formatted_data)
            st.markdown(
                "<hr style='margin: 1rem 0; opacity: 0.2;'/>",
                unsafe_allow_html=True,
            )
    else:
        st.info("No provenance data available.")
