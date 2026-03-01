"""Endpoint tree view grouped by tags."""

from __future__ import annotations

from collections.abc import Callable

import wx

from spectra.spec_parser import Endpoint

EndpointSelectCallback = Callable[[Endpoint], None]


class EndpointTree(wx.Panel):
    def __init__(self, parent: wx.Window, on_select: EndpointSelectCallback) -> None:
        super().__init__(parent)

        self._on_select = on_select
        self._all_by_tag: dict[str, list[Endpoint]] = {}

        label = wx.StaticText(self, label="Endpoints")
        label.SetName("Endpoint Tree Label")

        self.tree = wx.TreeCtrl(self, style=wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT)
        self.tree.SetName("Endpoint Tree")
        self._root = self.tree.AddRoot("API")

        self.tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self._on_activated)
        self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, self._on_selected)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(label, 0, wx.ALL, 4)
        sizer.Add(self.tree, 1, wx.EXPAND | wx.ALL, 4)
        self.SetSizer(sizer)

    def set_endpoints(self, by_tag: dict[str, list[Endpoint]]) -> None:
        self._all_by_tag = by_tag
        self.apply_filter("")

    def apply_filter(self, search_text: str) -> None:
        query = search_text.strip().lower()
        self.tree.DeleteChildren(self._root)

        for tag in sorted(self._all_by_tag):
            endpoints = self._all_by_tag[tag]
            filtered = []
            for endpoint in endpoints:
                haystack = f"{endpoint.method} {endpoint.path} {endpoint.summary}"
                if not query or query in haystack.lower():
                    filtered.append(endpoint)

            if not filtered:
                continue

            tag_item = self.tree.AppendItem(self._root, tag)
            for endpoint in filtered:
                label = f"{endpoint.method} {endpoint.path}"
                item = self.tree.AppendItem(tag_item, label)
                self.tree.SetItemData(item, endpoint)

        self.tree.Expand(self._root)

    def focus(self) -> None:
        self.tree.SetFocus()

    def _on_selected(self, event: wx.TreeEvent) -> None:
        self._emit_if_endpoint(event.GetItem())
        event.Skip()

    def _on_activated(self, event: wx.TreeEvent) -> None:
        self._emit_if_endpoint(event.GetItem())
        event.Skip()

    def _emit_if_endpoint(self, item: wx.TreeItemId) -> None:
        if not item.IsOk():
            return
        endpoint = self.tree.GetItemData(item)
        if isinstance(endpoint, Endpoint):
            self._on_select(endpoint)
