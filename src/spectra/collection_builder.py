"""Dialogs for building manual Spectra collections."""

from __future__ import annotations

from dataclasses import dataclass, field

import wx

from spectra.collection_parser import collection_to_dict
from spectra.spec_parser import Endpoint, Parameter

HTTP_METHOD_CHOICES = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
PARAMETER_LOCATIONS = ["path", "query", "header", "cookie", "body"]


@dataclass(slots=True)
class CollectionGroup:
    name: str
    endpoints: list[Endpoint] = field(default_factory=list)


class ParameterDialog(wx.Dialog):
    def __init__(self, parent: wx.Window, parameter: Parameter | None = None) -> None:
        super().__init__(parent, title="Parameter", size=(450, 280))

        self._build_ui(parameter)

    def _build_ui(self, parameter: Parameter | None) -> None:
        panel = wx.Panel(self)

        self.name_text = wx.TextCtrl(panel)
        self.location_choice = wx.Choice(panel, choices=PARAMETER_LOCATIONS)
        self.location_choice.SetSelection(0)
        self.required_check = wx.CheckBox(panel, label="Required")
        self.type_text = wx.TextCtrl(panel)
        self.description_text = wx.TextCtrl(panel)

        if parameter is not None:
            self.name_text.SetValue(parameter.name)
            self.location_choice.SetStringSelection(parameter.location)
            self.required_check.SetValue(parameter.required)
            self.type_text.SetValue(parameter.schema)
            self.description_text.SetValue(parameter.description)

        grid = wx.FlexGridSizer(cols=2, hgap=6, vgap=6)
        grid.AddGrowableCol(1, 1)
        grid.Add(wx.StaticText(panel, label="Name"), 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.name_text, 1, wx.EXPAND)
        grid.Add(wx.StaticText(panel, label="Location"), 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.location_choice, 1, wx.EXPAND)
        grid.Add(wx.StaticText(panel, label="Type"), 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.type_text, 1, wx.EXPAND)
        grid.Add(wx.StaticText(panel, label="Description"), 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.description_text, 1, wx.EXPAND)
        grid.AddSpacer(0)
        grid.Add(self.required_check)

        buttons = self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(grid, 1, wx.EXPAND | wx.ALL, 12)
        if buttons:
            sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 12)
        panel.SetSizer(sizer)

        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)

    def _on_ok(self, event: wx.CommandEvent) -> None:
        if not self.name_text.GetValue().strip():
            wx.MessageBox("Parameter name is required", "Validation Error", wx.OK | wx.ICON_ERROR)
            return
        if not self.type_text.GetValue().strip():
            wx.MessageBox("Parameter type is required", "Validation Error", wx.OK | wx.ICON_ERROR)
            return
        event.Skip()

    def get_parameter(self) -> Parameter:
        return Parameter(
            name=self.name_text.GetValue().strip(),
            location=self.location_choice.GetStringSelection() or "query",
            required=self.required_check.GetValue(),
            schema=self.type_text.GetValue().strip(),
            description=self.description_text.GetValue().strip(),
        )


class EndpointDialog(wx.Dialog):
    def __init__(self, parent: wx.Window, endpoint: Endpoint | None = None) -> None:
        super().__init__(parent, title="Endpoint", size=(720, 640))
        self._build_ui(endpoint)

    def _build_ui(self, endpoint: Endpoint | None) -> None:
        panel = wx.Panel(self)

        self.method_choice = wx.Choice(panel, choices=HTTP_METHOD_CHOICES)
        self.method_choice.SetSelection(0)
        self.path_text = wx.TextCtrl(panel)
        self.summary_text = wx.TextCtrl(panel)
        self.description_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE)
        self.request_body_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE)

        self.parameters_list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.parameters_list.InsertColumn(0, "Name", width=120)
        self.parameters_list.InsertColumn(1, "In", width=80)
        self.parameters_list.InsertColumn(2, "Required", width=80)
        self.parameters_list.InsertColumn(3, "Type", width=100)
        self.parameters_list.InsertColumn(4, "Description", width=220)
        self._parameters: list[Parameter] = []

        add_parameter = wx.Button(panel, label="Add Parameter")
        edit_parameter = wx.Button(panel, label="Edit Parameter")
        delete_parameter = wx.Button(panel, label="Delete Parameter")

        add_parameter.Bind(wx.EVT_BUTTON, self._on_add_parameter)
        edit_parameter.Bind(wx.EVT_BUTTON, self._on_edit_parameter)
        delete_parameter.Bind(wx.EVT_BUTTON, self._on_delete_parameter)

        if endpoint is not None:
            self.method_choice.SetStringSelection(endpoint.method)
            self.path_text.SetValue(endpoint.path)
            self.summary_text.SetValue(endpoint.summary)
            self.description_text.SetValue(endpoint.description)
            self.request_body_text.SetValue(endpoint.example_body)
            self._parameters = list(endpoint.parameters)
            self._refresh_parameters()

        grid = wx.FlexGridSizer(cols=2, hgap=6, vgap=6)
        grid.AddGrowableCol(1, 1)
        grid.Add(wx.StaticText(panel, label="Method"), 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.method_choice, 1, wx.EXPAND)
        grid.Add(wx.StaticText(panel, label="URL Template"), 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.path_text, 1, wx.EXPAND)
        grid.Add(wx.StaticText(panel, label="Summary"), 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.summary_text, 1, wx.EXPAND)
        grid.Add(wx.StaticText(panel, label="Description"), 0, wx.ALIGN_TOP)
        grid.Add(self.description_text, 1, wx.EXPAND)

        parameter_buttons = wx.BoxSizer(wx.HORIZONTAL)
        parameter_buttons.Add(add_parameter, 0, wx.RIGHT, 6)
        parameter_buttons.Add(edit_parameter, 0, wx.RIGHT, 6)
        parameter_buttons.Add(delete_parameter, 0)

        buttons = self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 12)
        sizer.Add(wx.StaticText(panel, label="Parameters"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(self.parameters_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(parameter_buttons, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(
            wx.StaticText(panel, label="Example Request Body"),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            12,
        )
        sizer.Add(self.request_body_text, 1, wx.EXPAND | wx.ALL, 12)
        if buttons:
            sizer.Add(buttons, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        panel.SetSizer(sizer)

        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)

    def _refresh_parameters(self) -> None:
        self.parameters_list.DeleteAllItems()
        for index, parameter in enumerate(self._parameters):
            self.parameters_list.InsertItem(index, parameter.name)
            self.parameters_list.SetItem(index, 1, parameter.location)
            self.parameters_list.SetItem(index, 2, "yes" if parameter.required else "no")
            self.parameters_list.SetItem(index, 3, parameter.schema)
            self.parameters_list.SetItem(index, 4, parameter.description)

    def _selected_parameter_index(self) -> int | None:
        index = self.parameters_list.GetFirstSelected()
        if index == -1:
            return None
        return index

    def _on_add_parameter(self, _event: wx.CommandEvent) -> None:
        with ParameterDialog(self) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            self._parameters.append(dialog.get_parameter())
            self._refresh_parameters()

    def _on_edit_parameter(self, _event: wx.CommandEvent) -> None:
        index = self._selected_parameter_index()
        if index is None:
            wx.MessageBox("Select a parameter to edit", "Validation Error", wx.OK | wx.ICON_ERROR)
            return
        with ParameterDialog(self, self._parameters[index]) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            self._parameters[index] = dialog.get_parameter()
            self._refresh_parameters()

    def _on_delete_parameter(self, _event: wx.CommandEvent) -> None:
        index = self._selected_parameter_index()
        if index is None:
            wx.MessageBox("Select a parameter to delete", "Validation Error", wx.OK | wx.ICON_ERROR)
            return
        del self._parameters[index]
        self._refresh_parameters()

    def _on_ok(self, event: wx.CommandEvent) -> None:
        if not self.path_text.GetValue().strip():
            wx.MessageBox(
                "Endpoint URL template is required",
                "Validation Error",
                wx.OK | wx.ICON_ERROR,
            )
            return
        event.Skip()

    def get_endpoint(self, group_name: str) -> Endpoint:
        example_body = self.request_body_text.GetValue()
        return Endpoint(
            method=self.method_choice.GetStringSelection() or "GET",
            path=self.path_text.GetValue().strip(),
            summary=self.summary_text.GetValue().strip(),
            description=self.description_text.GetValue().strip(),
            tags=[group_name],
            parameters=list(self._parameters),
            request_body=example_body,
            example_body=example_body,
        )


class CollectionBuilderDialog(wx.Dialog):
    def __init__(self, parent: wx.Window) -> None:
        super().__init__(parent, title="New Collection", size=(900, 620))
        self._groups: list[CollectionGroup] = []
        self._build_ui()

    def _build_ui(self) -> None:
        panel = wx.Panel(self)

        self.name_text = wx.TextCtrl(panel)
        self.base_url_text = wx.TextCtrl(panel)

        self.group_list = wx.ListBox(panel)
        self.endpoint_list = wx.ListBox(panel)

        self.group_list.Bind(wx.EVT_LISTBOX, self._on_group_selected)
        self.endpoint_list.Bind(wx.EVT_LISTBOX_DCLICK, self._on_edit_endpoint)

        add_group = wx.Button(panel, label="Add Group")
        rename_group = wx.Button(panel, label="Rename Group")
        delete_group = wx.Button(panel, label="Delete Group")
        add_endpoint = wx.Button(panel, label="Add Endpoint")
        edit_endpoint = wx.Button(panel, label="Edit Endpoint")
        delete_endpoint = wx.Button(panel, label="Delete Endpoint")

        add_group.Bind(wx.EVT_BUTTON, self._on_add_group)
        rename_group.Bind(wx.EVT_BUTTON, self._on_rename_group)
        delete_group.Bind(wx.EVT_BUTTON, self._on_delete_group)
        add_endpoint.Bind(wx.EVT_BUTTON, self._on_add_endpoint)
        edit_endpoint.Bind(wx.EVT_BUTTON, self._on_edit_endpoint)
        delete_endpoint.Bind(wx.EVT_BUTTON, self._on_delete_endpoint)

        form = wx.FlexGridSizer(cols=2, hgap=6, vgap=6)
        form.AddGrowableCol(1, 1)
        form.Add(wx.StaticText(panel, label="Collection Name"), 0, wx.ALIGN_CENTER_VERTICAL)
        form.Add(self.name_text, 1, wx.EXPAND)
        form.Add(wx.StaticText(panel, label="Base URL"), 0, wx.ALIGN_CENTER_VERTICAL)
        form.Add(self.base_url_text, 1, wx.EXPAND)

        groups_buttons = wx.BoxSizer(wx.HORIZONTAL)
        groups_buttons.Add(add_group, 0, wx.RIGHT, 6)
        groups_buttons.Add(rename_group, 0, wx.RIGHT, 6)
        groups_buttons.Add(delete_group, 0)

        endpoints_buttons = wx.BoxSizer(wx.HORIZONTAL)
        endpoints_buttons.Add(add_endpoint, 0, wx.RIGHT, 6)
        endpoints_buttons.Add(edit_endpoint, 0, wx.RIGHT, 6)
        endpoints_buttons.Add(delete_endpoint, 0)

        lists = wx.BoxSizer(wx.HORIZONTAL)

        group_column = wx.BoxSizer(wx.VERTICAL)
        group_column.Add(wx.StaticText(panel, label="Groups"), 0, wx.BOTTOM, 6)
        group_column.Add(self.group_list, 1, wx.EXPAND | wx.BOTTOM, 6)
        group_column.Add(groups_buttons, 0)

        endpoint_column = wx.BoxSizer(wx.VERTICAL)
        endpoint_column.Add(wx.StaticText(panel, label="Endpoints"), 0, wx.BOTTOM, 6)
        endpoint_column.Add(self.endpoint_list, 1, wx.EXPAND | wx.BOTTOM, 6)
        endpoint_column.Add(endpoints_buttons, 0)

        lists.Add(group_column, 1, wx.EXPAND | wx.ALL, 12)
        lists.Add(endpoint_column, 2, wx.EXPAND | wx.ALL, 12)

        buttons = self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(form, 0, wx.EXPAND | wx.ALL, 12)
        sizer.Add(lists, 1, wx.EXPAND)
        if buttons:
            sizer.Add(buttons, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        panel.SetSizer(sizer)

        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)

    def _refresh_groups(self) -> None:
        current = self.group_list.GetSelection()
        self.group_list.Set([group.name for group in self._groups])
        if not self._groups:
            self.endpoint_list.Clear()
            return

        if current == wx.NOT_FOUND or current >= len(self._groups):
            current = 0
        self.group_list.SetSelection(current)
        self._refresh_endpoints()

    def _refresh_endpoints(self) -> None:
        group = self._selected_group()
        if group is None:
            self.endpoint_list.Clear()
            return
        self.endpoint_list.Set(
            [f"{endpoint.method} {endpoint.path}" for endpoint in group.endpoints]
        )

    def _selected_group_index(self) -> int | None:
        index = self.group_list.GetSelection()
        if index == wx.NOT_FOUND:
            return None
        return index

    def _selected_group(self) -> CollectionGroup | None:
        index = self._selected_group_index()
        if index is None:
            return None
        return self._groups[index]

    def _selected_endpoint_index(self) -> int | None:
        index = self.endpoint_list.GetSelection()
        if index == wx.NOT_FOUND:
            return None
        return index

    def _prompt_group_name(self, title: str, value: str = "") -> str | None:
        dialog = wx.TextEntryDialog(self, "Group name", title, value)
        try:
            if dialog.ShowModal() != wx.ID_OK:
                return None
            name = dialog.GetValue().strip()
            if not name:
                wx.MessageBox("Group name is required", "Validation Error", wx.OK | wx.ICON_ERROR)
                return None
            return name
        finally:
            dialog.Destroy()

    def _on_group_selected(self, _event: wx.CommandEvent) -> None:
        self._refresh_endpoints()

    def _on_add_group(self, _event: wx.CommandEvent) -> None:
        name = self._prompt_group_name("Add Group")
        if name is None:
            return
        self._groups.append(CollectionGroup(name=name))
        self._refresh_groups()
        self.group_list.SetSelection(len(self._groups) - 1)
        self._refresh_endpoints()

    def _on_rename_group(self, _event: wx.CommandEvent) -> None:
        index = self._selected_group_index()
        if index is None:
            wx.MessageBox("Select a group to rename", "Validation Error", wx.OK | wx.ICON_ERROR)
            return
        name = self._prompt_group_name("Rename Group", self._groups[index].name)
        if name is None:
            return
        self._groups[index].name = name
        for endpoint in self._groups[index].endpoints:
            endpoint.tags = [name]
        self._refresh_groups()

    def _on_delete_group(self, _event: wx.CommandEvent) -> None:
        index = self._selected_group_index()
        if index is None:
            wx.MessageBox("Select a group to delete", "Validation Error", wx.OK | wx.ICON_ERROR)
            return
        del self._groups[index]
        self._refresh_groups()

    def _on_add_endpoint(self, _event: wx.CommandEvent) -> None:
        group = self._selected_group()
        if group is None:
            wx.MessageBox(
                "Add a group before creating endpoints",
                "Validation Error",
                wx.OK | wx.ICON_ERROR,
            )
            return
        with EndpointDialog(self) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            group.endpoints.append(dialog.get_endpoint(group.name))
            self._refresh_endpoints()

    def _on_edit_endpoint(self, _event: wx.CommandEvent) -> None:
        group = self._selected_group()
        index = self._selected_endpoint_index()
        if group is None or index is None:
            wx.MessageBox("Select an endpoint to edit", "Validation Error", wx.OK | wx.ICON_ERROR)
            return
        with EndpointDialog(self, group.endpoints[index]) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            group.endpoints[index] = dialog.get_endpoint(group.name)
            self._refresh_endpoints()
            self.endpoint_list.SetSelection(index)

    def _on_delete_endpoint(self, _event: wx.CommandEvent) -> None:
        group = self._selected_group()
        index = self._selected_endpoint_index()
        if group is None or index is None:
            wx.MessageBox("Select an endpoint to delete", "Validation Error", wx.OK | wx.ICON_ERROR)
            return
        del group.endpoints[index]
        self._refresh_endpoints()

    def _on_ok(self, event: wx.CommandEvent) -> None:
        if not self.name_text.GetValue().strip():
            wx.MessageBox("Collection name is required", "Validation Error", wx.OK | wx.ICON_ERROR)
            return
        if not self._groups:
            wx.MessageBox(
                "At least one group is required",
                "Validation Error",
                wx.OK | wx.ICON_ERROR,
            )
            return
        event.Skip()

    def build_document(self) -> dict:
        by_tag = {group.name: list(group.endpoints) for group in self._groups}
        return collection_to_dict(
            name=self.name_text.GetValue().strip(),
            base_url=self.base_url_text.GetValue().strip(),
            by_tag=by_tag,
        )
