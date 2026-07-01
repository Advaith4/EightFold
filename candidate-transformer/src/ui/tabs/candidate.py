"""Candidate tab component."""

import streamlit as st
from src.agents.models import CandidatePresentation


def render_candidate_tab(presentation: CandidatePresentation) -> None:
    """Render the Candidate tab showing Identity, Contact, Education, etc."""
    overview = presentation.overview
    header = presentation.header

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Name", header.name if header.name else "Unknown")
        st.metric("Email", header.primary_email if header.primary_email else "Unknown")
    with col2:
        current_role = (
            overview.experience[0].title
            if overview.experience and overview.experience[0].title
            else "Unknown"
        )
        st.metric("Current Role", current_role)
        st.metric("Phone", header.primary_phone if header.primary_phone else "Unknown")
    with col3:
        current_org = (
            overview.experience[0].company
            if overview.experience and overview.experience[0].company
            else "Unknown"
        )
        st.metric("Current Organization", current_org)
        st.metric("Profile Confidence", presentation.confidence.overall_score)

    st.divider()

    col4, col5 = st.columns(2)
    with col4:
        st.markdown("### Missing Fields")
        if presentation.hr_projection.missing_fields:
            for mf in presentation.hr_projection.missing_fields:
                st.warning(f"Missing: {mf}")
        else:
            st.success("No critical fields missing.")

    with col5:
        st.markdown("### Merge Decisions")
        if presentation.engineering_projection.merge_decisions:
            for cf in presentation.engineering_projection.merge_decisions:
                st.warning(f"Merge: {cf}")
        else:
            st.success("No complex merges required.")

    st.divider()

    st.markdown("### Skills")
    if overview.skills:
        tags = "".join(
            f"<span class='skill-chip'>{skill.name}</span>"
            for skill in overview.skills
        )
        st.markdown(tags, unsafe_allow_html=True)
    else:
        st.info("No skills detected.")

    if header.github_url or header.linkedin_url:
        st.markdown("### Links")
        if header.github_url:
            st.markdown(f"- [GitHub]({header.github_url})")
        if header.linkedin_url:
            st.markdown(f"- [LinkedIn]({header.linkedin_url})")
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

    if getattr(overview, "duplicate_experiences", []) or getattr(
        overview, "duplicate_education", []
    ):
        st.markdown("### Duplicate Records (Removed from Profile)")

        if getattr(overview, "duplicate_experiences", []):
            st.markdown("#### Duplicate Experience")
            for exp in overview.duplicate_experiences:
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

        if getattr(overview, "duplicate_education", []):
            st.markdown("#### Duplicate Education")
            for edu in overview.duplicate_education:
                if edu.degree and edu.field:
                    st.markdown(f"**{edu.degree}** in {edu.field}")
                elif edu.degree:
                    st.markdown(f"**{edu.degree}**")

                if edu.institution:
                    st.markdown(f"{edu.institution}")

                st.markdown(f"*{edu.duration}*")
                st.markdown("---")


