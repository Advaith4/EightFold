"""Application startup tests."""

from typing import Any

import app


class _RendererSpy:
    rendered = False

    @staticmethod
    def render(*args: Any, **kwargs: Any) -> None:
        _RendererSpy.rendered = True


class MockSessionState(dict[str, Any]):
    def __getattr__(self, item: str) -> Any:
        return self.get(item)

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value


def test_application_startup(monkeypatch: Any) -> None:
    """Verify startup initializes dependencies and reaches rendering."""
    _RendererSpy.rendered = False
    monkeypatch.setattr(app, "render_main_layout", _RendererSpy.render)

    import streamlit as st

    monkeypatch.setattr(st, "set_page_config", lambda *args, **kwargs: None)
    monkeypatch.setattr(st, "error", lambda x: None)
    monkeypatch.setattr(st, "warning", lambda x: None)
    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: None)
    monkeypatch.setattr(st, "text_input", lambda *args, **kwargs: None)
    monkeypatch.setattr(st, "button", lambda *args, **kwargs: False)
    monkeypatch.setattr(st, "session_state", MockSessionState())
    monkeypatch.setattr(st, "rerun", lambda: None)

    class MockSidebar:
        def __enter__(self) -> "MockSidebar":
            return self

        def __exit__(self, *args: Any) -> None:
            pass

    monkeypatch.setattr(st, "sidebar", MockSidebar())
    monkeypatch.setattr(st, "header", lambda *args, **kwargs: None)

    app.main()

    assert _RendererSpy.rendered is True
