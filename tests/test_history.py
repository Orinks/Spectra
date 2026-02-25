from __future__ import annotations

import pytest

from spectra.history import HistoryItem, RequestHistory


def test_add_and_get_history_item() -> None:
    history = RequestHistory()
    item = HistoryItem(method="GET", url="https://x", headers={}, body="")

    history.add(item)

    assert history.get(0).url == "https://x"


def test_history_latest_first() -> None:
    history = RequestHistory()
    history.add(HistoryItem(method="GET", url="https://a", headers={}, body=""))
    history.add(HistoryItem(method="POST", url="https://b", headers={}, body=""))

    assert history.get(0).url == "https://b"
    assert history.get(1).url == "https://a"


def test_history_max_50_cap() -> None:
    history = RequestHistory(max_items=50)
    for i in range(55):
        history.add(HistoryItem(method="GET", url=f"https://{i}", headers={}, body=""))

    assert len(history.list_items()) == 50
    assert history.get(49).url == "https://5"


def test_history_custom_cap() -> None:
    history = RequestHistory(max_items=3)
    for i in range(5):
        history.add(HistoryItem(method="GET", url=f"https://{i}", headers={}, body=""))

    assert [item.url for item in history.list_items()] == ["https://4", "https://3", "https://2"]


def test_history_clear() -> None:
    history = RequestHistory()
    history.add(HistoryItem(method="GET", url="https://x", headers={}, body=""))

    history.clear()

    assert history.list_items() == []


def test_history_get_out_of_range_raises() -> None:
    history = RequestHistory()

    with pytest.raises(IndexError):
        history.get(0)
