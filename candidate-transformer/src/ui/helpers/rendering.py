"""Shared rendering helpers for UI components."""

from typing import Any

import streamlit as st


def render_dict_as_table(data: dict[str, Any], title: str | None = None) -> None:
    """Render a dictionary as a simple markdown table or key-value list."""
    if title:
        st.subheader(title)

    if not data:
        st.write("No data available.")
        return

    for key, value in data.items():
        st.markdown(f"**{key}:** {value}")


def render_section_header(title: str, divider: bool = True) -> None:
    """Render a consistent section header."""
    st.header(title, divider=divider)
