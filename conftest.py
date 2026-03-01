"""Root conftest — stub wx when not installed so tests run headless."""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

if "wx" not in sys.modules:
    try:
        import wx  # noqa: F401
    except ImportError:
        _wx = types.ModuleType("wx")
        _wx.__package__ = "wx"
        _wx.__path__ = []

        class _Base:
            def __init__(self, *args, **kwargs):
                pass

            def SetName(self, *a, **kw):
                pass

            def SetSizer(self, *a, **kw):
                pass

            def Bind(self, *a, **kw):
                pass

            def GetValue(self):
                return ""

            def SetValue(self, *a, **kw):
                pass

            def GetStringSelection(self):
                return ""

            def SetSelection(self, *a, **kw):
                pass

            def FindString(self, *a, **kw):
                return -1

        _wx.Frame = _Base
        _wx.Panel = _Base
        _wx.Dialog = _Base
        _wx.App = _Base
        _wx.Window = _Base
        _wx.Control = _Base
        _wx.TextCtrl = MagicMock
        _wx.StaticText = MagicMock
        _wx.Button = MagicMock
        _wx.Choice = MagicMock
        _wx.CheckBox = MagicMock
        _wx.ListCtrl = MagicMock
        _wx.TreeCtrl = MagicMock
        _wx.TreeItemId = MagicMock
        _wx.TreeItemData = MagicMock
        _wx.SplitterWindow = MagicMock
        _wx.BoxSizer = MagicMock
        _wx.FlexGridSizer = MagicMock
        _wx.AcceleratorTable = MagicMock
        _wx.AcceleratorEntry = MagicMock
        _wx.FileDialog = MagicMock
        _wx.TextEntryDialog = MagicMock
        _wx.Menu = MagicMock
        _wx.MenuBar = MagicMock
        _wx.MenuItem = MagicMock
        _wx.CommandEvent = MagicMock
        _wx.ListEvent = MagicMock
        _wx.TreeEvent = MagicMock
        _wx.KeyEvent = MagicMock

        # Constants
        _wx.ID_ANY = -1
        _wx.ID_OK = 5100
        _wx.ID_CANCEL = 5101
        _wx.ID_OPEN = 5102
        _wx.ID_REFRESH = 5103
        _wx.ID_EXIT = 5104
        _wx.ID_FIND = 5105
        _wx.ID_CLEAR = 5106
        _wx.NOT_FOUND = -1
        _wx.OK = 0x0004
        _wx.CANCEL = 0x0010
        _wx.HORIZONTAL = 4
        _wx.VERTICAL = 8
        _wx.EXPAND = 0x2000
        _wx.ALL = 0x0F
        _wx.LEFT = 0x10
        _wx.TOP = 0x20
        _wx.RIGHT = 0x40
        _wx.BOTTOM = 0x80
        _wx.ALIGN_CENTER_VERTICAL = 0x0200
        _wx.ALIGN_TOP = 0x0100
        _wx.ALIGN_RIGHT = 0x0400
        _wx.LC_REPORT = 0x0020
        _wx.LC_SINGLE_SEL = 0x0200
        _wx.TR_HAS_BUTTONS = 0x0001
        _wx.TR_LINES_AT_ROOT = 0x0008
        _wx.TE_MULTILINE = 0x0020
        _wx.TE_READONLY = 0x0010
        _wx.FD_OPEN = 0x0001
        _wx.FD_FILE_MUST_EXIST = 0x0010
        _wx.ACCEL_CTRL = 0x0002
        _wx.ACCEL_NORMAL = 0x0000
        _wx.WXK_RETURN = 13
        _wx.WXK_ESCAPE = 27
        _wx.WXK_F5 = 344
        _wx.ICON_ERROR = 0x0200
        _wx.ICON_INFORMATION = 0x0100
        _wx.DEFAULT_FRAME_STYLE = 0

        # Events
        for _ev in [
            "EVT_BUTTON", "EVT_MENU", "EVT_CLOSE", "EVT_TIMER",
            "EVT_CHAR_HOOK", "EVT_LIST_ITEM_SELECTED",
            "EVT_TREE_ITEM_ACTIVATED", "EVT_TREE_SEL_CHANGED",
        ]:
            setattr(_wx, _ev, MagicMock())

        _wx.CallAfter = MagicMock()
        _wx.MessageBox = MagicMock()

        sys.modules["wx"] = _wx
