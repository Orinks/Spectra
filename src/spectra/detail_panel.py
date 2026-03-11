"""Panel displaying endpoint details in readable text."""

from __future__ import annotations

import wx

from spectra.spec_parser import Endpoint


class DetailPanel(wx.Panel):
    def __init__(self, parent: wx.Window) -> None:
        super().__init__(parent)

        label = wx.StaticText(self, label="Endpoint Details")
        label.SetName("Endpoint Details Label")

        self.text = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.text.SetName("Endpoint Details")

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(label, 0, wx.ALL, 4)
        sizer.Add(self.text, 1, wx.EXPAND | wx.ALL, 4)
        self.SetSizer(sizer)

    def show_endpoint(self, endpoint: Endpoint) -> None:
        request_headers = "None"
        if endpoint.request_headers:
            request_headers = "\n".join(
                f"- {key}: {value}" for key, value in endpoint.request_headers.items()
            )

        parameters = "None"
        if endpoint.parameters:
            lines = []
            for param in endpoint.parameters:
                req = "required" if param.required else "optional"
                schema = param.schema or "unspecified"
                lines.append(f"- {param.name} ({param.location}, {req}): {schema}")
            parameters = "\n".join(lines)

        request_body = endpoint.request_body or "None"

        responses = "None"
        if endpoint.responses:
            response_lines = []
            for code, description in sorted(endpoint.responses.items()):
                response_lines.append(f"- {code}: {description or 'No description'}")
            responses = "\n".join(response_lines)

        text = (
            f"Method: {endpoint.method}\n"
            f"URL: {endpoint.url or 'Derived from selection'}\n"
            f"Path: {endpoint.path}\n"
            f"Summary: {endpoint.summary or 'None'}\n"
            f"Description: {endpoint.description or 'None'}\n\n"
            f"Parameters:\n{parameters}\n\n"
            f"Request Headers:\n{request_headers}\n\n"
            f"Request Body:\n{request_body}\n\n"
            f"Responses:\n{responses}"
        )
        self.text.SetValue(text)

    def clear(self) -> None:
        self.text.SetValue("")
