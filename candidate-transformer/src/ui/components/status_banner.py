"""Status banner component."""

import streamlit as st
from src.agents.models import PresentationResult


def render_status_banner(result: PresentationResult) -> None:
    """Render a colored status banner based on workflow status."""
    status = result.header.workflow_status

    if status == "Ready For Review":
        st.success("✅ **Ready For Review** - Candidate profile is complete.")
    elif status == "Needs Human Review":
        st.warning("⚠️ **Needs Human Review** - Conflicting data detected.")
    elif status == "Incomplete Profile":
        st.error("❌ **Incomplete Profile** - Missing critical information.")
    else:
        st.info(f"ℹ️ **Status:** {status}")
