from __future__ import annotations

import base64
from unittest.mock import MagicMock, patch

from spectra.history import RequestHistory
from spectra.request_panel import RequestPanel, join_url
from spectra.spec_parser import Endpoint


def make_panel() -> RequestPanel:
    """Create a RequestPanel with fully mocked wx controls."""
    with patch("spectra.request_panel.wx"):
        panel = RequestPanel.__new__(RequestPanel)
        panel._on_response = MagicMock()
        panel._on_status = MagicMock()
        panel._on_error = MagicMock()
        panel._history = RequestHistory()

        panel.base_url_combo = MagicMock()
        panel.method_choice = MagicMock()
        panel.url_text = MagicMock()
        panel.auth_choice = MagicMock()
        panel.auth_text = MagicMock()
        panel.headers_text = MagicMock()
        panel.body_text = MagicMock()

        return panel


def test_prefill_url_is_path() -> None:
    panel = make_panel()
    endpoint = Endpoint(method="GET", path="/users", summary="", description="")
    panel.method_choice.FindString.return_value = 0

    panel.prefill_from_endpoint(endpoint)

    panel.url_text.SetValue.assert_called_once_with("/users")


def test_join_url() -> None:
    assert join_url("", "/users") == "/users"
    assert join_url("https://api.example.com/v0", "/users") == "https://api.example.com/v0/users"
    assert join_url("https://api.example.com/v0/", "users") == "https://api.example.com/v0/users"
    assert join_url("https://api.example.com", "http://other.test/x") == "http://other.test/x"


def test_set_servers_selects_first() -> None:
    panel = make_panel()

    panel.set_servers(["https://a.test", "https://b.test"])

    panel.base_url_combo.Set.assert_called_once_with(["https://a.test", "https://b.test"])
    panel.base_url_combo.SetValue.assert_called_once_with("https://a.test")


def test_send_prefixes_base_url() -> None:
    panel = make_panel()
    panel.base_url_combo.GetValue.return_value = "https://api.example.com/v0/"
    panel.url_text.GetValue.return_value = "/users"
    panel.method_choice.GetStringSelection.return_value = "GET"
    panel.body_text.GetValue.return_value = ""

    with patch("spectra.request_panel.threading.Thread"):
        panel.on_send()

    assert panel._history.get(0).url == "https://api.example.com/v0/users"


def test_prefill_method() -> None:
    panel = make_panel()
    endpoint = Endpoint(method="POST", path="/users", summary="", description="")
    panel.method_choice.FindString.return_value = 1

    panel.prefill_from_endpoint(endpoint)

    panel.method_choice.SetSelection.assert_called_once_with(1)


def test_parse_headers_ignores_invalid_lines() -> None:
    panel = make_panel()
    panel.headers_text.GetValue.return_value = (
        "Accept: application/json\nInvalidLine\nX-Test: one"
    )

    headers = panel.parse_headers()

    assert headers == {"Accept": "application/json", "X-Test": "one"}


def test_build_auth_headers_bearer() -> None:
    panel = make_panel()
    panel.auth_choice.GetStringSelection.return_value = "Bearer"
    panel.auth_text.GetValue.return_value = "abc123"

    headers = panel.build_auth_headers()

    assert headers["Authorization"] == "Bearer abc123"


def test_build_auth_headers_basic() -> None:
    panel = make_panel()
    panel.auth_choice.GetStringSelection.return_value = "Basic"
    panel.auth_text.GetValue.return_value = "user:pass"

    headers = panel.build_auth_headers()

    expected = base64.b64encode(b"user:pass").decode("ascii")
    assert headers["Authorization"] == f"Basic {expected}"
