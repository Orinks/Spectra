"""Panel displaying HTTP response details."""

from __future__ import annotations

import json

import wx


class ResponsePanel(wx.Panel):
    def __init__(self, parent: wx.Window) -> None:
        super().__init__(parent)

        self.status_label = wx.StaticText(self, label="Status: N/A")
        self.status_label.SetName("Response Status")

        self.headers_text = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.headers_text.SetName("Response Headers")

        self.body_text = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.body_text.SetName("Response Body")

        copy_button = wx.Button(self, label="Copy Body")
        copy_button.SetName("Copy Body")
        copy_button.Bind(wx.EVT_BUTTON, self._on_copy_body)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.status_label, 0, wx.EXPAND | wx.ALL, 4)
        sizer.Add(wx.StaticText(self, label="Headers"), 0, wx.LEFT | wx.TOP, 4)
        sizer.Add(self.headers_text, 1, wx.EXPAND | wx.ALL, 4)
        sizer.Add(wx.StaticText(self, label="Body"), 0, wx.LEFT | wx.TOP, 4)
        sizer.Add(self.body_text, 2, wx.EXPAND | wx.ALL, 4)
        sizer.Add(copy_button, 0, wx.ALL | wx.ALIGN_RIGHT, 4)
        self.SetSizer(sizer)

    def show_response(self, status_code: int, headers: dict[str, str], body: str) -> None:
        self.status_label.SetLabel(f"Status: {status_code}")
        header_lines = [f"{k}: {v}" for k, v in sorted(headers.items())]
        self.headers_text.SetValue("\n".join(header_lines))

        pretty_body = body
        try:
            parsed = json.loads(body)
            pretty_body = json.dumps(parsed, indent=2, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            pass
        self.body_text.SetValue(pretty_body if isinstance(pretty_body, str) else str(pretty_body))

    def clear(self) -> None:
        self.status_label.SetLabel("Status: N/A")
        self.headers_text.SetValue("")
        self.body_text.SetValue("")

    def _on_copy_body(self, _event: wx.CommandEvent) -> None:
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(self.body_text.GetValue()))
            wx.TheClipboard.Close()
