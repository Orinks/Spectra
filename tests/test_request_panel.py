from __future__ import annotations

import base64

import wx

from spectra.history import RequestHistory
from spectra.request_panel import RequestPanel
from spectra.spec_parser import Endpoint


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


def test_prefill_postman_request_fields_and_variables(wx_app: wx.App) -> None:
    panel = make_panel(wx_app)
    panel.set_variables({"baseUrl": "https://api.example.com", "userId": "42"})
    endpoint = Endpoint(
        method="GET",
        path="/users/{{userId}}",
        summary="",
        description="",
        request_url="{{baseUrl}}/users/{{userId}}",
        request_headers={"Accept": "application/json", "X-User": "{{userId}}"},
        request_body_text='{"id":"{{userId}}"}',
    )

    panel.prefill_from_endpoint(endpoint)

    assert panel.url_text.GetValue() == "https://api.example.com/users/42"
    assert panel.headers_text.GetValue() == "Accept: application/json\nX-User: 42"
    assert panel.body_text.GetValue() == '{"id":"42"}'


def test_apply_variables_preserves_unknown_placeholders(wx_app: wx.App) -> None:
    panel = make_panel(wx_app)
    panel.set_variables({"baseUrl": "https://api.example.com"})
    endpoint = Endpoint(
        method="GET",
        path="/users/{{userId}}",
        summary="",
        description="",
        request_url="{{baseUrl}}/users/{{userId}}",
    )

    panel.prefill_from_endpoint(endpoint)

    assert panel.url_text.GetValue() == "https://api.example.com/users/{{userId}}"


def test_clear_keeps_variable_values(wx_app: wx.App) -> None:
    panel = make_panel(wx_app)
    panel.set_variables({"baseUrl": "https://api.example.com"})
    panel.url_text.SetValue("https://api.example.com/users")

    panel.clear()

    assert panel.variables_text.GetValue() == "baseUrl=https://api.example.com"
    assert panel.url_text.GetValue() == ""


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
