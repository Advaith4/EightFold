"""Candidate tab component."""

import streamlit as st
from src.agents.models import PresentationResult


def render_candidate_tab(result: PresentationResult) -> None:
    """Render the Candidate tab showing Identity, Contact, Education, etc."""
    overview = result.overview

    st.markdown("### Skills")
    if overview.skills:
        tags = [f"`{skill.name}`" for skill in overview.skills]
        st.markdown(" ".join(tags))
    else:
        st.info("No skills detected.")

    if result.header.github_url or result.header.linkedin_url:
        st.markdown("### Links")
        if result.header.github_url:
            st.markdown(f"- [GitHub]({result.header.github_url})")
        if result.header.linkedin_url:
            st.markdown(f"- [LinkedIn]({result.header.linkedin_url})")
        st.markdown("<br/>", unsafe_allow_html=True)

    st.markdown("### Experience")
    if overview.experience:
        for exp in overview.experience:
            if exp.title and exp.company:
                st.markdown(f"**{exp.title}** at {exp.company}")
            elif exp.title:
                st.markdown(f"**{exp.title}**")
            elif exp.company:
                st.markdown(f"**{exp.company}**")

            st.markdown(f"*{exp.duration}*")
            if exp.description:
                st.write(exp.description)
            st.markdown("---")
    else:
        st.info("No professional experience detected.")

    st.markdown("### Education")
    if overview.education:
        for edu in overview.education:
            if edu.degree and edu.field:
                st.markdown(f"**{edu.degree}** in {edu.field}")
            elif edu.degree:
                st.markdown(f"**{edu.degree}**")

            if edu.institution:
                st.markdown(f"{edu.institution}")

            st.markdown(f"*{edu.duration}*")
            st.markdown("---")
    else:
        st.info("No education information was detected.")
