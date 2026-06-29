"""Application startup tests."""

from typing import Any

import app


class _RendererSpy:
    rendered = False

    def __init__(
        self,
        app_config: dict[str, Any],
        pipeline: Any,
        pipeline_initialized: bool,
        logger_configured: bool,
        version: str,
    ) -> None:
        self.app_config = app_config
        self.pipeline = pipeline
        self.pipeline_initialized = pipeline_initialized
        self.logger_configured = logger_configured
        self.version = version

    def render(self) -> None:
        _RendererSpy.rendered = True


def test_application_startup(monkeypatch: Any) -> None:
    """Verify startup initializes dependencies and reaches rendering."""
    _RendererSpy.rendered = False
    monkeypatch.setattr(app, "LandingPageRenderer", _RendererSpy)

    app.main()

    assert _RendererSpy.rendered is True
