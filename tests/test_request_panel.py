from __future__ import annotations

import base64

import pytest

wx = pytest.importorskip("wx")

from spectra.history import RequestHistory  # noqa: E402
from spectra.request_panel import RequestPanel  # noqa: E402
from spectra.spec_parser import Endpoint  # noqa: E402


def make_panel(wx_app: wx.App) -> RequestPanel:
    frame = wx.Frame(None)
    panel = RequestPanel(
        frame,
        on_response=lambda *_: None,
        on_status=lambda *_: None,
        on_error=lambda *_: None,
        history=RequestHistory(),
    )
    frame.Show(False)
    return panel


def test_prefill_url_without_base(wx_app: wx.App) -> None:
    panel = make_panel(wx_app)
    endpoint = Endpoint(method="GET", path="/users", summary="", description="")

    panel.prefill_from_endpoint(endpoint)

    assert panel.url_text.GetValue() == "/users"


def test_prefill_url_with_base(wx_app: wx.App) -> None:
    panel = make_panel(wx_app)
    endpoint = Endpoint(method="GET", path="/users", summary="", description="")

    panel.prefill_from_endpoint(endpoint, base_url="https://api.example.com")

    assert panel.url_text.GetValue() == "https://api.example.com/users"


def test_prefill_method(wx_app: wx.App) -> None:
    panel = make_panel(wx_app)
    endpoint = Endpoint(method="POST", path="/users", summary="", description="")

    panel.prefill_from_endpoint(endpoint)

    assert panel.method_choice.GetStringSelection() == "POST"


def test_prefill_example_body(wx_app: wx.App) -> None:
    panel = make_panel(wx_app)
    endpoint = Endpoint(
        method="POST",
        path="/users",
        summary="",
        description="",
        example_body='{"name":"Ada"}',
    )

    panel.prefill_from_endpoint(endpoint)

    assert panel.body_text.GetValue() == '{"name":"Ada"}'


def test_parse_headers_ignores_invalid_lines(wx_app: wx.App) -> None:
    panel = make_panel(wx_app)
    panel.headers_text.SetValue("Accept: application/json\nInvalidLine\nX-Test: one")

    headers = panel.parse_headers()

    assert headers == {"Accept": "application/json", "X-Test": "one"}


def test_build_auth_headers_bearer(wx_app: wx.App) -> None:
    panel = make_panel(wx_app)
    panel.auth_choice.SetStringSelection("Bearer")
    panel.auth_text.SetValue("abc123")

    headers = panel.build_auth_headers()

    assert headers["Authorization"] == "Bearer abc123"


def test_build_auth_headers_basic(wx_app: wx.App) -> None:
    panel = make_panel(wx_app)
    panel.auth_choice.SetStringSelection("Basic")
    panel.auth_text.SetValue("user:pass")

    headers = panel.build_auth_headers()

    expected = base64.b64encode(b"user:pass").decode("ascii")
    assert headers["Authorization"] == f"Basic {expected}"
