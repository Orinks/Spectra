from __future__ import annotations

import pytest
import wx


@pytest.fixture(scope="session")
def wx_app() -> wx.App:
    app = wx.App(False)
    yield app
    app.Destroy()
