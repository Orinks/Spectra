"""In-memory request history."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class HistoryItem:
    method: str
    url: str
    headers: dict[str, str]
    body: str
    status_code: int | None = None


class RequestHistory:
    def __init__(self, max_items: int = 50) -> None:
        self.max_items = max_items
        self._items: list[HistoryItem] = []

    def add(self, item: HistoryItem) -> None:
        self._items.insert(0, item)
        if len(self._items) > self.max_items:
            self._items = self._items[: self.max_items]

    def list_items(self) -> list[HistoryItem]:
        return list(self._items)

    def get(self, index: int) -> HistoryItem:
        return self._items[index]

    def clear(self) -> None:
        self._items.clear()
