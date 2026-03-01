"""Spec Manager dialog for saving and recalling OpenAPI specs."""

from __future__ import annotations

import wx

from spectra.spec_store import SavedSpec, SpecStore


class _SpecEditDialog(wx.Dialog):
    """Small inner dialog for adding or editing a saved spec."""

    def __init__(self, parent: wx.Window, title: str, spec: SavedSpec | None = None) -> None:
        super().__init__(parent, title=title, size=(450, 200))
        self.SetName(title)

        panel = wx.Panel(self)
        panel.SetName("Spec Edit Panel")

        name_label = wx.StaticText(panel, label="Name:")
        name_label.SetName("Name Label")
        self._name_ctrl = wx.TextCtrl(panel)
        self._name_ctrl.SetName("Name")

        source_label = wx.StaticText(panel, label="Source:")
        source_label.SetName("Source Label")
        self._source_ctrl = wx.TextCtrl(panel)
        self._source_ctrl.SetName("Source")

        browse_btn = wx.Button(panel, label="Browse...")
        browse_btn.SetName("Browse")
        browse_btn.Bind(wx.EVT_BUTTON, self._on_browse)

        ok_btn = wx.Button(panel, wx.ID_OK, "OK")
        ok_btn.SetName("OK")
        cancel_btn = wx.Button(panel, wx.ID_CANCEL, "Cancel")
        cancel_btn.SetName("Cancel")

        if spec:
            self._name_ctrl.SetValue(spec.name)
            self._source_ctrl.SetValue(spec.source)

        source_row = wx.BoxSizer(wx.HORIZONTAL)
        source_row.Add(self._source_ctrl, 1, wx.EXPAND | wx.RIGHT, 4)
        source_row.Add(browse_btn, 0)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        btn_row.AddStretchSpacer()
        btn_row.Add(ok_btn, 0, wx.RIGHT, 4)
        btn_row.Add(cancel_btn, 0)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(name_label, 0, wx.ALL, 4)
        sizer.Add(self._name_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
        sizer.Add(source_label, 0, wx.ALL, 4)
        sizer.Add(source_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
        sizer.AddStretchSpacer()
        sizer.Add(btn_row, 0, wx.EXPAND | wx.ALL, 4)
        panel.SetSizer(sizer)

    def _on_browse(self, _event: wx.CommandEvent) -> None:
        with wx.FileDialog(
            self,
            "Select OpenAPI Spec",
            wildcard=(
                "JSON/YAML files (*.json;*.yaml;*.yml)|*.json;*.yaml;*.yml|All files (*.*)|*.*"
            ),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self._source_ctrl.SetValue(dlg.GetPath())

    def get_spec(self) -> SavedSpec | None:
        name = self._name_ctrl.GetValue().strip()
        source = self._source_ctrl.GetValue().strip()
        if not name or not source:
            return None
        return SavedSpec(name=name, source=source)


class SpecManagerDialog(wx.Dialog):
    """Dialog for managing saved OpenAPI specs."""

    def __init__(self, parent: wx.Window, store: SpecStore) -> None:
        super().__init__(parent, title="Spec Manager", size=(600, 400))
        self.SetName("Spec Manager")

        self._store = store
        self._selected_source: str | None = None
        self._selected_name: str | None = None

        panel = wx.Panel(self)
        panel.SetName("Spec Manager Panel")

        self._list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self._list.SetName("Saved Specs")
        self._list.InsertColumn(0, "Name", width=200)
        self._list.InsertColumn(1, "Source", width=300)
        self._list.InsertColumn(2, "Last Loaded", width=130)

        open_btn = wx.Button(panel, label="Open")
        open_btn.SetName("Open")
        add_btn = wx.Button(panel, label="Add")
        add_btn.SetName("Add")
        edit_btn = wx.Button(panel, label="Edit")
        edit_btn.SetName("Edit")
        remove_btn = wx.Button(panel, label="Remove")
        remove_btn.SetName("Remove")
        close_btn = wx.Button(panel, wx.ID_CANCEL, label="Close")
        close_btn.SetName("Close")

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.Add(open_btn, 0, wx.RIGHT, 4)
        btn_sizer.Add(add_btn, 0, wx.RIGHT, 4)
        btn_sizer.Add(edit_btn, 0, wx.RIGHT, 4)
        btn_sizer.Add(remove_btn, 0, wx.RIGHT, 4)
        btn_sizer.AddStretchSpacer()
        btn_sizer.Add(close_btn, 0)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self._list, 1, wx.EXPAND | wx.ALL, 4)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
        panel.SetSizer(sizer)

        open_btn.Bind(wx.EVT_BUTTON, self._on_open)
        add_btn.Bind(wx.EVT_BUTTON, self._on_add)
        edit_btn.Bind(wx.EVT_BUTTON, self._on_edit)
        remove_btn.Bind(wx.EVT_BUTTON, self._on_remove)

        self.Bind(wx.EVT_CHAR_HOOK, self._on_key)

        self._refresh_list()
        self._list.SetFocus()

    def _refresh_list(self) -> None:
        self._list.DeleteAllItems()
        for i, spec in enumerate(self._store.list_specs()):
            self._list.InsertItem(i, spec.name)
            self._list.SetItem(i, 1, spec.source)
            self._list.SetItem(i, 2, spec.last_loaded)

    def _get_selected_index(self) -> int:
        return self._list.GetFirstSelected()

    def _on_open(self, _event: wx.CommandEvent) -> None:
        idx = self._get_selected_index()
        if idx < 0:
            return
        specs = self._store.list_specs()
        self._selected_source = specs[idx].source
        self._selected_name = specs[idx].name
        self.EndModal(wx.ID_OK)

    def _on_add(self, _event: wx.CommandEvent) -> None:
        dlg = _SpecEditDialog(self, "Add Spec")
        try:
            if dlg.ShowModal() == wx.ID_OK:
                spec = dlg.get_spec()
                if spec:
                    try:
                        self._store.add(spec)
                    except ValueError:
                        wx.MessageBox(
                            f"A spec named '{spec.name}' already exists.",
                            "Duplicate Name",
                            wx.OK | wx.ICON_WARNING,
                        )
                        return
                    self._refresh_list()
        finally:
            dlg.Destroy()

    def _on_edit(self, _event: wx.CommandEvent) -> None:
        idx = self._get_selected_index()
        if idx < 0:
            return
        specs = self._store.list_specs()
        old_spec = specs[idx]
        dlg = _SpecEditDialog(self, "Edit Spec", spec=old_spec)
        try:
            if dlg.ShowModal() == wx.ID_OK:
                new_spec = dlg.get_spec()
                if new_spec:
                    if new_spec.name != old_spec.name:
                        self._store.remove(old_spec.name)
                        try:
                            self._store.add(new_spec)
                        except ValueError:
                            self._store.add(old_spec)
                            wx.MessageBox(
                                f"A spec named '{new_spec.name}' already exists.",
                                "Duplicate Name",
                                wx.OK | wx.ICON_WARNING,
                            )
                            return
                    else:
                        self._store.update(new_spec)
                    self._refresh_list()
        finally:
            dlg.Destroy()

    def _on_remove(self, _event: wx.CommandEvent | None = None) -> None:
        idx = self._get_selected_index()
        if idx < 0:
            return
        specs = self._store.list_specs()
        self._store.remove(specs[idx].name)
        self._refresh_list()
        count = self._list.GetItemCount()
        if count > 0:
            new_idx = min(idx, count - 1)
            self._list.Select(new_idx)
            self._list.Focus(new_idx)
        self._list.SetFocus()

    def _on_key(self, event: wx.KeyEvent) -> None:
        code = event.GetKeyCode()
        if code == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CANCEL)
        elif code == wx.WXK_DELETE:
            self._on_remove()
        elif code == wx.WXK_RETURN:
            self._on_open(event)  # type: ignore[arg-type]
        else:
            event.Skip()

    def get_selected_source(self) -> str | None:
        return self._selected_source

    def get_selected_name(self) -> str | None:
        return self._selected_name
