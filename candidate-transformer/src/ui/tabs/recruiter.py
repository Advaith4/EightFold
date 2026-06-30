"""Recruiter projection tab component."""

import streamlit as st
from src.agents.models import CandidatePresentation


def render_recruiter_tab(presentation: CandidatePresentation) -> None:
    """Render the Recruiter tab."""
    st.markdown("### 👔 Recruiter Dashboard")
    proj = presentation.recruiter_projection

    # Top level summaries as glassmorphic metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Experience", proj.experience_summary)
    m2.metric("Education", proj.education_summary)
    m3.metric("Profile Confidence", proj.confidence)

    st.markdown("<hr style='margin: 2rem 0; opacity: 0.3;'/>", unsafe_allow_html=True)

    # Two column layout for Identity and Contact
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 👤 Identity")
        st.markdown("<br>", unsafe_allow_html=True)
        for k, v in proj.identity.items():
            if v:
                st.markdown(f"**{k}:** {v}")

    with col2:
        st.markdown("#### 📞 Contact")
        st.markdown("<br>", unsafe_allow_html=True)
        for k, v in proj.contact.items():
            if v:
                st.markdown(f"**{k}:** {v}")

    st.markdown("<hr style='margin: 2rem 0; opacity: 0.3;'/>", unsafe_allow_html=True)

    st.markdown("#### ⚠️ Missing Information")
    if proj.missing_information:
        missing_tags = "".join(
            [
                "<span style='display: inline-block; "
                "background: rgba(234, 88, 12, 0.1); color: #ea580c; "
                "padding: 0.4rem 1rem; border-radius: 20px; "
                "font-size: 0.95rem; font-weight: 600; "
                "margin-right: 0.5rem; margin-bottom: 0.5rem; "
                "border: 1px solid rgba(234, 88, 12, 0.3);'>"
                f"{item.title()}</span>"
                for item in proj.missing_information
            ]
        )
        st.markdown(
            "<div style='padding: 1.5rem; "
            "background: rgba(255,255,255,0.6); "
            "backdrop-filter: blur(10px); border-radius: 12px; "
            "border: 1px solid rgba(234, 88, 12, 0.2);'>"
            f"{missing_tags}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.success("✨ Complete Profile - No missing information.")