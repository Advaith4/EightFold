"""Project logger tests."""

from pathlib import Path

from src.logging import ProjectLogger


def test_project_logger_initializes_file_sink(tmp_path: Path) -> None:
    """Project logger creates the target log directory."""
    config = {
        "logging": {
            "level": "INFO",
            "directory": str(tmp_path / "logs"),
            "file_name": "application.log",
            "rotation": "00:00",
            "retention": "1 day",
            "compression": "zip",
            "format": "{time} | {level} | {message}",
        }
    }

    project_logger = ProjectLogger(config)
    logger = project_logger.get_logger()
    logger.info("logger test message")

    assert project_logger.is_configured is True
    assert (tmp_path / "logs").exists()
