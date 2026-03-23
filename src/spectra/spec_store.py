"""Persistent store for saved OpenAPI spec references."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class SavedSpec:
    name: str
    source: str
    last_loaded: str = ""


_DEFAULT_DIR = Path.home() / ".spectra"
_DEFAULT_FILE = _DEFAULT_DIR / "specs.json"


class SpecStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _DEFAULT_FILE
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._specs: list[SavedSpec] = []
        self.load()

    def list_specs(self) -> list[SavedSpec]:
        return list(self._specs)

    def add(self, spec: SavedSpec) -> None:
        if any(s.name == spec.name for s in self._specs):
            raise ValueError(f"Spec with name '{spec.name}' already exists")
        self._specs.append(spec)
        self.save()

    def update(self, spec: SavedSpec) -> None:
        for i, s in enumerate(self._specs):
            if s.name == spec.name:
                self._specs[i] = spec
                self.save()
                return
        raise KeyError(f"Spec '{spec.name}' not found")

    def remove(self, name: str) -> None:
        self._specs = [s for s in self._specs if s.name != name]
        self.save()

    def touch(self, name: str) -> None:
        for s in self._specs:
            if s.name == name:
                s.last_loaded = datetime.now(tz=UTC).isoformat()
                self.save()
                return

    def save(self) -> None:
        data = [asdict(s) for s in self._specs]
        self._path.write_text(json.dumps(data, indent=2))

    def load(self) -> None:
        if not self._path.exists():
            self._specs = []
            return
        try:
            data = json.loads(self._path.read_text())
            self._specs = [SavedSpec(**item) for item in data]
        except (json.JSONDecodeError, TypeError, KeyError):
            self._specs = []
