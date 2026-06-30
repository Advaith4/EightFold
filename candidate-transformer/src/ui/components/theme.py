"""Theme and CSS injection component."""

from pathlib import Path

import streamlit as st


def inject_custom_theme() -> None:
    """Load and inject custom glassmorphic CSS into the Streamlit app."""
    css_path = Path(__file__).parent.parent / "assets" / "style.css"
    if css_path.exists():
        with open(css_path, encoding="utf-8") as f:
            css_content = f.read()
            st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    else:
        st.warning(f"Theme CSS not found at {css_path}")
