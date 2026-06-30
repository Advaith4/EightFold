"""Helpers for handling Streamlit file uploads."""

import tempfile
from pathlib import Path
from typing import Any


def save_uploaded_file(uploaded_file: Any) -> Path | None:
    """Save a Streamlit UploadedFile to a temporary file and return its Path.

    Args:
        uploaded_file: Streamlit UploadedFile object.

    Returns:
        Path to the temporary file, or None if no file was provided.
    """
    if uploaded_file is None:
        return None

    # Determine extension
    extension = Path(uploaded_file.name).suffix

    # Create temp file with suffix
    fd, path_str = tempfile.mkstemp(suffix=extension)
    path = Path(path_str)

    with open(fd, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return path
