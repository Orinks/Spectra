"""Panel for building and sending HTTP requests."""

from __future__ import annotations

import base64
import threading
from collections.abc import Callable

import requests
import wx

from spectra.history import HistoryItem, RequestHistory
from spectra.spec_parser import Endpoint

ResponseCallback = Callable[[int, dict[str, str], str], None]
StatusCallback = Callable[[str], None]
ErrorCallback = Callable[[str], None]


class RequestPanel(wx.Panel):
    def __init__(
        self,
        parent: wx.Window,
        on_response: ResponseCallback,
        on_status: StatusCallback,
        on_error: ErrorCallback,
        history: RequestHistory,
    ) -> None:
        super().__init__(parent)

        self._on_response = on_response
        self._on_status = on_status
        self._on_error = on_error
        self._history = history

        method_label = wx.StaticText(self, label="Method")
        method_label.SetName("Method Label")
        self.method_choice = wx.Choice(
            self,
            choices=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
        )
        self.method_choice.SetName("Request Method")
        self.method_choice.SetSelection(0)

        url_label = wx.StaticText(self, label="URL")
        url_label.SetName("URL Label")
        self.url_text = wx.TextCtrl(self)
        self.url_text.SetName("Request URL")

        auth_type_label = wx.StaticText(self, label="Auth Type")
        auth_type_label.SetName("Auth Type Label")
        self.auth_choice = wx.Choice(self, choices=["None", "Bearer", "Basic"])
        self.auth_choice.SetName("Auth Type")
        self.auth_choice.SetSelection(0)

        auth_value_label = wx.StaticText(self, label="Auth Value")
        auth_value_label.SetName("Auth Value Label")
        self.auth_text = wx.TextCtrl(self)
        self.auth_text.SetName("Auth Value")

        headers_label = wx.StaticText(self, label="Headers (key:value per line)")
        headers_label.SetName("Headers Label")
        self.headers_text = wx.TextCtrl(self, style=wx.TE_MULTILINE)
        self.headers_text.SetName("Request Headers")

        body_label = wx.StaticText(self, label="Request Body")
        body_label.SetName("Request Body Label")
        self.body_text = wx.TextCtrl(self, style=wx.TE_MULTILINE)
        self.body_text.SetName("Request Body")

        send_button = wx.Button(self, label="Send")
        send_button.SetName("Send Request")
        send_button.Bind(wx.EVT_BUTTON, self.on_send)

        self.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)

        grid = wx.FlexGridSizer(cols=2, hgap=6, vgap=6)
        grid.AddGrowableCol(1, 1)

        grid.Add(method_label, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.method_choice, 1, wx.EXPAND)
        grid.Add(url_label, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.url_text, 1, wx.EXPAND)
        grid.Add(auth_type_label, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.auth_choice, 1, wx.EXPAND)
        grid.Add(auth_value_label, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.auth_text, 1, wx.EXPAND)
        grid.Add(headers_label, 0, wx.ALIGN_TOP)
        grid.Add(self.headers_text, 1, wx.EXPAND)
        grid.Add(body_label, 0, wx.ALIGN_TOP)
        grid.Add(self.body_text, 1, wx.EXPAND)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(grid, 1, wx.EXPAND | wx.ALL, 4)
        sizer.Add(send_button, 0, wx.ALIGN_RIGHT | wx.ALL, 4)
        self.SetSizer(sizer)

    def prefill_from_endpoint(self, endpoint: Endpoint, base_url: str = "") -> None:
        method_index = self.method_choice.FindString(endpoint.method)
        if method_index != wx.NOT_FOUND:
            self.method_choice.SetSelection(method_index)
        self.url_text.SetValue(f"{base_url}{endpoint.path}" if base_url else endpoint.path)

    def parse_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        for line in self.headers_text.GetValue().splitlines():
            line = line.strip()
            if not line:
                continue
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            headers[key.strip()] = value.strip()
        return headers

    def build_auth_headers(self) -> dict[str, str]:
        auth_type = self.auth_choice.GetStringSelection()
        value = self.auth_text.GetValue().strip()
        if auth_type == "Bearer" and value:
            return {"Authorization": f"Bearer {value}"}
        if auth_type == "Basic" and value:
            encoded = base64.b64encode(value.encode("utf-8")).decode("ascii")
            return {"Authorization": f"Basic {encoded}"}
        return {}

    def on_send(self, _event: wx.CommandEvent | None = None) -> None:
        method = self.method_choice.GetStringSelection() or "GET"
        url = self.url_text.GetValue().strip()
        if not url:
            self._on_error("URL is required")
            return

        headers = self.parse_headers()
        headers.update(self.build_auth_headers())
        body = self.body_text.GetValue()

        history_item = HistoryItem(method=method, url=url, headers=headers, body=body)
        self._history.add(history_item)

        self._on_status(f"Request sent: {method} {url}")

        def _worker() -> None:
            try:
                response = requests.request(
                    method,
                    url,
                    headers=headers,
                    data=body.encode("utf-8") if body else None,
                    timeout=30,
                )
                history_item.status_code = response.status_code
                wx.CallAfter(
                    self._on_response,
                    response.status_code,
                    dict(response.headers),
                    response.text,
                )
                wx.CallAfter(self._on_status, f"Response received: HTTP {response.status_code}")
            except requests.RequestException as exc:
                wx.CallAfter(self._on_error, f"Request failed: {exc}")
                wx.CallAfter(self._on_status, "Request failed")

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    def clear(self) -> None:
        self.url_text.SetValue("")
        self.headers_text.SetValue("")
        self.body_text.SetValue("")
        self.auth_choice.SetSelection(0)
        self.auth_text.SetValue("")

    def populate_from_history(self, item: HistoryItem) -> None:
        method_index = self.method_choice.FindString(item.method)
        if method_index != wx.NOT_FOUND:
            self.method_choice.SetSelection(method_index)
        self.url_text.SetValue(item.url)
        self.body_text.SetValue(item.body)
        self.headers_text.SetValue("\n".join(f"{k}: {v}" for k, v in item.headers.items()))

    def _on_char_hook(self, event: wx.KeyEvent) -> None:
        if event.GetKeyCode() == wx.WXK_RETURN and event.ControlDown():
            self.on_send()
            return
        event.Skip()
