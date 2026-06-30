"""Streamlit entry point for the candidate transformer foundation."""

from pathlib import Path

import streamlit as st
from src.adapters import AdapterRegistry
from src.config import ConfigurationLoader, LoggingConfig, ProjectConfig
from src.exceptions import ApplicationError
from src.logging import ProjectLogger
from src.services.candidate_processing import CandidateProcessingService
from src.services.container import ServiceContainer
from src.ui.helpers.upload import save_uploaded_file
from src.ui.main_layout import render_main_layout


def init_services() -> CandidateProcessingService:
    """Initialize core services and configuration."""
    if "processing_service" in st.session_state:
        from typing import cast

        return cast(CandidateProcessingService, st.session_state.processing_service)

    root = Path(__file__).parent
    app_config = ConfigurationLoader(root / "config" / "default.yaml").load()
    logging_config = ConfigurationLoader(root / "config" / "logging.yaml").load()

    if not isinstance(app_config, ProjectConfig):
        raise ApplicationError("Default configuration did not produce ProjectConfig.")
    if not isinstance(logging_config, LoggingConfig):
        raise ApplicationError("Logging configuration did not produce LoggingConfig.")

    project_logger = ProjectLogger(logging_config)
    logger = project_logger.get_logger()
    logger.info("Application startup completed")

    services = ServiceContainer(
        app_config=app_config,
        logging_config=logging_config,
        logger=project_logger,
        adapter_registry=AdapterRegistry(),
    )

    processing_service = CandidateProcessingService(services=services)
    st.session_state.processing_service = processing_service
    return processing_service


def main() -> None:
    """Run the Streamlit application."""
    # Must be the first Streamlit command
    st.set_page_config(layout="wide")

    # Initialize session state for the result
    if "result" not in st.session_state:
        st.session_state.result = None

    try:
        processing_service = init_services()
    except Exception as e:
        st.error(f"Failed to initialize services: {str(e)}")
        return

    # Render Sidebar
    with st.sidebar:
        st.header("Candidate Intake")

        resume_files = st.file_uploader(
            "Resume Upload", type=["pdf", "docx"], accept_multiple_files=True
        )
        ats_files = st.file_uploader(
            "ATS JSON Upload", type=["json"], accept_multiple_files=True
        )
        recruiter_files = st.file_uploader(
            "Recruiter CSV Upload", type=["csv"], accept_multiple_files=True
        )
        github_url = st.text_area(
            "GitHub URLs", placeholder="One GitHub profile URL per line"
        )

        analyze_clicked = st.button(
            "Analyze Candidate", type="primary", use_container_width=True
        )
        reset_clicked = st.button("Reset", use_container_width=True)

    if reset_clicked:
        st.session_state.result = None
        st.rerun()

    if analyze_clicked:
        # Avoid processing if all inputs are empty
        if not any([resume_files, ats_files, recruiter_files, github_url]):
            st.warning("Please provide at least one input.")
        else:
            with st.spinner("Analyzing candidate..."):
                try:
                    # Convert Streamlit UploadedFiles to Paths
                    resume_paths = [
                        path
                        for uploaded_file in resume_files or []
                        if (path := save_uploaded_file(uploaded_file)) is not None
                    ]
                    ats_paths = [
                        path
                        for uploaded_file in ats_files or []
                        if (path := save_uploaded_file(uploaded_file)) is not None
                    ]
                    recruiter_paths = [
                        path
                        for uploaded_file in recruiter_files or []
                        if (path := save_uploaded_file(uploaded_file)) is not None
                    ]

                    # Call the backend service
                    result = processing_service.process_candidate(
                        resume_pdf=[
                            path for path in resume_paths if path.suffix == ".pdf"
                        ],
                        resume_docx=[
                            path for path in resume_paths if path.suffix == ".docx"
                        ],
                        ats_json=ats_paths,
                        recruiter_csv=recruiter_paths,
                        github_url=github_url if github_url else None,
                    )

                    st.session_state.result = result
                    st.success("✓ Candidate processed successfully.")
                except Exception as e:
                    # Catch backend exceptions gracefully without stack traces
                    st.error(f"⚠ Processing failed: {str(e)}")
                    st.session_state.result = None

    # Pass the result (if any) to the main layout for rendering
    render_main_layout(st.session_state.result)


if __name__ == "__main__":
    try:
        main()
    except ApplicationError as error:
        raise SystemExit(str(error)) from error
