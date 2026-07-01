"""Confidence tab component."""

import streamlit as st
from src.agents.models import CandidatePresentation, PresentationResult


def render_confidence_tab(
    presentation: CandidatePresentation,
    result: PresentationResult | None = None,
    selected_index: int = 0,
) -> None:
    """Render profile-level and source-level confidence information."""
    st.markdown("### Profile Confidence Summary")
    conf = presentation.confidence

    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Profile Confidence", value=conf.overall_score)
        try:
            val = int(conf.overall_score.replace("%", ""))
            st.progress(val / 100.0)
        except ValueError:
            st.progress(0.0)
    with col2:
        merges = len(presentation.engineering_projection.merge_decisions)
        st.metric(label="Merge Decisions", value=str(merges))

    st.caption(
        "This is an aggregate profile score for the selected canonical candidate. "
        "Field-level confidence for specific values is shown in the Provenance tab."
    )

    st.divider()
    _render_source_coverage(presentation, result, selected_index)

    st.divider()

    st.markdown("#### How This Profile Score Was Calculated")
    selected_sources = presentation.header.sources_used
    selected_label = ", ".join(selected_sources) if selected_sources else "None"
    st.markdown(f"**Counted sources:** {selected_label}")
    if result is not None:
        all_sources = _all_pipeline_sources(result)
        if all_sources:
            st.markdown(f"**All sources received:** {', '.join(all_sources)}")
        other_sources = _other_group_sources(result, selected_index)
        if other_sources:
            st.warning(
                "Some sources were not counted in this selected candidate group: "
                f"{', '.join(other_sources)}"
            )
    if conf.details:
        for detail in conf.details:
            st.markdown(f"- {detail}")
    else:
        st.warning(
            "No detailed score breakdown is attached to this result. "
            "Click Reset, then Analyze Candidate again to regenerate it."
        )
        st.markdown(f"- {conf.reason}")

    st.divider()
    st.markdown(f"**Method:** {conf.method}")
    st.markdown(f"**Confidence Level:** {conf.confidence_level}")


def _render_source_coverage(
    presentation: CandidatePresentation,
    result: PresentationResult | None,
    selected_index: int,
) -> None:
    st.markdown("#### Source Coverage")
    selected_sources = presentation.header.sources_used
    selected_label = ", ".join(selected_sources) if selected_sources else "None"
    st.markdown(f"**Sources counted in this selected candidate:** {selected_label}")

    if result is None:
        return

    all_sources = _all_pipeline_sources(result)
    if all_sources:
        st.markdown(f"**Sources received in this run:** {', '.join(all_sources)}")

    other_sources = _other_group_sources(result, selected_index)
    if other_sources:
        st.info(
            "GitHub or other sources may be present in the run but not counted in "
            "this selected candidate when duplicate detection cannot link them by "
            "email, phone, GitHub URL, ATS id, name plus organization, "
            "or name plus education."
        )
        other_label = ", ".join(other_sources)
        st.markdown(f"**Sources in other candidate groups:** {other_label}")


def _all_pipeline_sources(result: PresentationResult) -> list[str]:
    sources: list[str] = []
    for group in result.candidate_groups:
        sources.extend(group.source_types)
    return list(dict.fromkeys(sources))


def _other_group_sources(
    result: PresentationResult,
    selected_index: int,
) -> list[str]:
    sources: list[str] = []
    for index, group in enumerate(result.candidate_groups):
        if index == selected_index:
            continue
        sources.extend(group.source_types)
    return list(dict.fromkeys(sources))


