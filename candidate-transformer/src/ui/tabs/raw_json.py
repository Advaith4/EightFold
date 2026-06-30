"""Raw JSON tab component."""

import streamlit as st
from src.models.candidate import CanonicalCandidate


def render_raw_json_tab(candidate: CanonicalCandidate) -> None:
    """Render the Raw JSON tab."""
    from src.pipeline.projection import ConfigurableJSONProjector
    
    st.markdown("### Raw Output Validation")
    
    # 1. Default Output (No Config)
    st.markdown("#### Default Canonical Output")
    st.info("The exact structure of the internal CanonicalCandidate model.")
    default_projector = ConfigurableJSONProjector()
    st.json(default_projector.project(candidate))
    
    st.markdown("---")
    
    # 2. Custom Configured Output
    st.markdown("#### Custom Output Reshaping")
    st.info("Runtime reshaping without modifying the underlying CanonicalCandidate.")
    
    custom_config = {
        "fields": [
            {
                "path": "full_name",
                "type": "string",
                "required": True
            },
            {
                "path": "primary_phone",
                "from": "contact_info.phones[0]",
                "normalize": "E164"
            },
            {
                "path": "primary_email",
                "from": "contact_info.emails[0]"
            },
            {
                "path": "skills",
                "from": "skills[].name"
            },
            {
                "path": "years_experience",
                "from": "experience_summary.years"
            }
        ],
        "include_confidence": True,
        "include_provenance": False,
        "on_missing": "null"
    }
    
    custom_projector = ConfigurableJSONProjector(config=custom_config)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Runtime Configuration**")
        st.json(custom_config)
    with col2:
        st.markdown("**Projected Output**")
        st.json(custom_projector.project(candidate))
