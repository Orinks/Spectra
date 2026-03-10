"""Main frame for Spectra application."""

from __future__ import annotations

from collections.abc import Callable

import wx

from spectra.detail_panel import DetailPanel
from spectra.endpoint_tree import EndpointTree
from spectra.history import RequestHistory
from spectra.request_panel import RequestPanel
from spectra.response_panel import ResponsePanel
from spectra.spec_loader import SpecLoaderError, load_spec
from spectra.spec_parser import Endpoint, parse_spec


class SpecFileDropTarget(wx.FileDropTarget):
    def __init__(self, on_drop: Callable[[str], None]) -> None:
        super().__init__()
        self._on_drop = on_drop

    def OnDropFiles(self, x: int, y: int, filenames: list[str]) -> bool:
        del x, y
        if not filenames:
            return False
        self._on_drop(filenames[0])
        return True


class MainFrame(wx.Frame):
    def __init__(self) -> None:
        super().__init__(None, title="Spectra", size=(1300, 850))

        self.SetName("Spectra Main Frame")
        self._last_source: str = ""
        self._current_endpoint: Endpoint | None = None
        self._history = RequestHistory(max_items=50)

        self._build_ui()
        self._build_menu()
        self._build_shortcuts()
        self.SetDropTarget(SpecFileDropTarget(self._load_spec))

        self.CreateStatusBar()
        self.SetStatusText("Ready")

    def _build_ui(self) -> None:
        splitter = wx.SplitterWindow(self)
        splitter.SetName("Main Splitter")

        self.endpoint_tree = EndpointTree(splitter, on_select=self._on_endpoint_selected)
        self.endpoint_tree.SetName("Endpoint Panel")

        right_panel = wx.Panel(splitter)
        right_panel.SetName("Right Panel")

        self.detail_panel = DetailPanel(right_panel)
        self.detail_panel.SetName("Detail Panel")

        self.request_panel = RequestPanel(
            right_panel,
            on_response=self._handle_response,
            on_status=self.SetStatusText,
            on_error=self._show_error,
            history=self._history,
        )
        self.request_panel.SetName("Request Panel")

        self.response_panel = ResponsePanel(right_panel)
        self.response_panel.SetName("Response Panel")

        self.history_list = wx.ListCtrl(right_panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.history_list.SetName("Request History")
        self.history_list.InsertColumn(0, "Method", width=80)
        self.history_list.InsertColumn(1, "URL", width=420)
        self.history_list.InsertColumn(2, "Status", width=80)
        self.history_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_history_selected)

        right_sizer = wx.BoxSizer(wx.VERTICAL)
        right_sizer.Add(self.detail_panel, 2, wx.EXPAND | wx.ALL, 4)
        right_sizer.Add(self.request_panel, 3, wx.EXPAND | wx.ALL, 4)
        right_sizer.Add(self.response_panel, 3, wx.EXPAND | wx.ALL, 4)
        right_sizer.Add(wx.StaticText(right_panel, label="History"), 0, wx.LEFT | wx.TOP, 4)
        right_sizer.Add(self.history_list, 2, wx.EXPAND | wx.ALL, 4)
        right_panel.SetSizer(right_sizer)

        splitter.SplitVertically(self.endpoint_tree, right_panel, sashPosition=350)
        splitter.SetMinimumPaneSize(250)

        root_sizer = wx.BoxSizer(wx.VERTICAL)
        root_sizer.Add(splitter, 1, wx.EXPAND)
        self.SetSizer(root_sizer)

    def _build_menu(self) -> None:
        menu_bar = wx.MenuBar()

        file_menu = wx.Menu()
        open_file = file_menu.Append(wx.ID_OPEN, "Open Spec File\tCtrl+O")
        open_url = file_menu.Append(wx.ID_ANY, "Open Spec URL\tCtrl+U")
        reload_item = file_menu.Append(wx.ID_REFRESH, "Reload\tF5")
        file_menu.AppendSeparator()
        exit_item = file_menu.Append(wx.ID_EXIT, "Exit")

        edit_menu = wx.Menu()
        filter_item = edit_menu.Append(wx.ID_FIND, "Filter Endpoints\tCtrl+F")
        clear_item = edit_menu.Append(wx.ID_CLEAR, "Clear Request\tEsc")
        history_item = edit_menu.Append(wx.ID_ANY, "Focus History\tCtrl+H")

        menu_bar.Append(file_menu, "File")
        menu_bar.Append(edit_menu, "Edit")
        self.SetMenuBar(menu_bar)

        self.Bind(wx.EVT_MENU, self._on_open_file, open_file)
        self.Bind(wx.EVT_MENU, self._on_open_url, open_url)
        self.Bind(wx.EVT_MENU, self._on_reload, reload_item)
        self.Bind(wx.EVT_MENU, self._on_filter, filter_item)
        self.Bind(wx.EVT_MENU, self._on_clear_request, clear_item)
        self.Bind(wx.EVT_MENU, self._on_focus_history, history_item)
        self.Bind(wx.EVT_MENU, lambda _e: self.Close(), exit_item)

    def _build_shortcuts(self) -> None:
        entries = [
            (wx.ACCEL_CTRL, ord("O"), wx.ID_OPEN),
            (wx.ACCEL_CTRL, ord("U"), wx.ID_ANY + 10),
            (wx.ACCEL_NORMAL, wx.WXK_F5, wx.ID_REFRESH),
            (wx.ACCEL_CTRL, ord("F"), wx.ID_FIND),
            (wx.ACCEL_NORMAL, wx.WXK_ESCAPE, wx.ID_CLEAR),
            (wx.ACCEL_CTRL, ord("H"), wx.ID_ANY + 11),
        ]

        accel_table = wx.AcceleratorTable(entries)
        self.SetAcceleratorTable(accel_table)

        self.Bind(wx.EVT_MENU, self._on_open_url, id=wx.ID_ANY + 10)
        self.Bind(wx.EVT_MENU, self._on_focus_history, id=wx.ID_ANY + 11)

    def _on_open_file(self, _event: wx.CommandEvent) -> None:
        with wx.FileDialog(
            self,
            "Open API Description",
            wildcard=(
                "API description files (*.json;*.yaml;*.yml)|*.json;*.yaml;*.yml|"
                "All files (*.*)|*.*"
            ),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if dialog.ShowModal() == wx.ID_CANCEL:
                return
            self._load_spec(dialog.GetPath())

    def _on_open_url(self, _event: wx.CommandEvent) -> None:
        dialog = wx.TextEntryDialog(self, "Enter OpenAPI, Swagger, or Postman URL", "Open URL")
        dialog.SetValue("https://")
        try:
            if dialog.ShowModal() == wx.ID_OK:
                self._load_spec(dialog.GetValue().strip())
        finally:
            dialog.Destroy()

    def _on_reload(self, _event: wx.CommandEvent) -> None:
        if not self._last_source:
            self._show_error("No spec source to reload")
            return
        self._load_spec(self._last_source)

    def _on_filter(self, _event: wx.CommandEvent) -> None:
        dialog = wx.TextEntryDialog(self, "Filter endpoints by text", "Filter")
        try:
            if dialog.ShowModal() == wx.ID_OK:
                self.endpoint_tree.apply_filter(dialog.GetValue())
                self.SetStatusText("Endpoint filter applied")
        finally:
            dialog.Destroy()

    def _on_clear_request(self, _event: wx.CommandEvent) -> None:
        self.request_panel.clear()
        self.response_panel.clear()
        self.SetStatusText("Request and response cleared")

    def _on_focus_history(self, _event: wx.CommandEvent) -> None:
        self.history_list.SetFocus()
        self.SetStatusText("History focused")

    def _load_spec(self, source: str) -> None:
        try:
            spec = load_spec(source)
            parsed = parse_spec(spec)
        except SpecLoaderError as exc:
            self._show_error(str(exc))
            self.SetStatusText("Spec load failed")
            return

        self._last_source = source
        self.endpoint_tree.set_endpoints(parsed.by_tag)
        self.detail_panel.clear()
        self.request_panel.clear()
        self.request_panel.set_variables(parsed.variables)
        self.response_panel.clear()
        self.SetStatusText(f"Spec loaded: {source} ({len(parsed.endpoints)} endpoints)")

    def _on_endpoint_selected(self, endpoint: Endpoint) -> None:
        self._current_endpoint = endpoint
        self.detail_panel.show_endpoint(endpoint)

        base_url = self._derive_base_url(self._last_source)
        self.request_panel.prefill_from_endpoint(endpoint, base_url=base_url)

        self.SetStatusText(f"Selected endpoint: {endpoint.method} {endpoint.path}")

    def _derive_base_url(self, source: str) -> str:
        if not source:
            return ""
        if source.startswith(("http://", "https://")):
            if source.endswith("/"):
                return source[:-1]
            slash = source.rfind("/")
            return source[:slash] if slash > 8 else source
        return ""

    def _handle_response(self, status_code: int, headers: dict[str, str], body: str) -> None:
        self.response_panel.show_response(status_code, headers, body)
        self._refresh_history_list()

    def _refresh_history_list(self) -> None:
        self.history_list.DeleteAllItems()
        for row, item in enumerate(self._history.list_items()):
            self.history_list.InsertItem(row, item.method)
            self.history_list.SetItem(row, 1, item.url)
            status = str(item.status_code) if item.status_code is not None else "-"
            self.history_list.SetItem(row, 2, status)

    def _on_history_selected(self, event: wx.ListEvent) -> None:
        index = event.GetIndex()
        try:
            item = self._history.get(index)
        except IndexError:
            return
        self.request_panel.populate_from_history(item)
        self.SetStatusText(f"History selected: {item.method} {item.url}")

    def _show_error(self, message: str) -> None:
        wx.MessageBox(message, "Spectra Error", style=wx.OK | wx.ICON_ERROR)
