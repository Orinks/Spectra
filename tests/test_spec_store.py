"""Tests for SpecStore."""

from __future__ import annotations

from pathlib import Path

import pytest

from spectra.spec_store import SavedSpec, SpecStore


@pytest.fixture()
def store(tmp_path: Path) -> SpecStore:
    return SpecStore(path=tmp_path / "specs.json")


def test_add_and_list(store: SpecStore) -> None:
    spec = SavedSpec(name="petstore", source="/tmp/petstore.yaml")
    store.add(spec)
    specs = store.list_specs()
    assert len(specs) == 1
    assert specs[0].name == "petstore"
    assert specs[0].source == "/tmp/petstore.yaml"


def test_duplicate_name_raises(store: SpecStore) -> None:
    store.add(SavedSpec(name="api", source="/tmp/a.yaml"))
    with pytest.raises(ValueError, match="already exists"):
        store.add(SavedSpec(name="api", source="/tmp/b.yaml"))


def test_remove(store: SpecStore) -> None:
    store.add(SavedSpec(name="one", source="/tmp/one.yaml"))
    store.add(SavedSpec(name="two", source="/tmp/two.yaml"))
    store.remove("one")
    names = [s.name for s in store.list_specs()]
    assert names == ["two"]


def test_remove_nonexistent_is_silent(store: SpecStore) -> None:
    store.remove("ghost")


def test_update(store: SpecStore) -> None:
    store.add(SavedSpec(name="api", source="/tmp/old.yaml"))
    store.update(SavedSpec(name="api", source="/tmp/new.yaml"))
    specs = store.list_specs()
    assert specs[0].source == "/tmp/new.yaml"


def test_touch_updates_timestamp(store: SpecStore) -> None:
    store.add(SavedSpec(name="api", source="/tmp/api.yaml"))
    assert store.list_specs()[0].last_loaded == ""
    store.touch("api")
    assert store.list_specs()[0].last_loaded != ""


def test_persist_and_reload(tmp_path: Path) -> None:
    path = tmp_path / "specs.json"
    store1 = SpecStore(path=path)
    store1.add(SavedSpec(name="a", source="/a.yaml"))
    store1.add(SavedSpec(name="b", source="/b.yaml"))

    store2 = SpecStore(path=path)
    names = [s.name for s in store2.list_specs()]
    assert names == ["a", "b"]


def test_list_returns_copy(store: SpecStore) -> None:
    store.add(SavedSpec(name="x", source="/x.yaml"))
    specs = store.list_specs()
    specs.clear()
    assert len(store.list_specs()) == 1
