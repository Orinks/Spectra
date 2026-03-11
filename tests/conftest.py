from __future__ import annotations

import pytest

try:
    import wx
except ImportError:  # pragma: no cover - depends on local test environment.
    wx = None


@pytest.fixture(scope="session")
def wx_app():
    if wx is None:
        pytest.skip("wxPython is not installed")
    app = wx.App(False)
    yield app
    app.Destroy()
