"""Tests for recent files persistence."""

from __future__ import annotations

from pathlib import Path

from ui.recent_files import RecentFilesStore


def test_recent_files_store_limit_and_order(tmp_path: Path) -> None:
    storage = tmp_path / "recent.json"
    files = [tmp_path / f"doc{i}.pdf" for i in range(3)]
    for file_path in files:
        file_path.write_text("pdf", encoding="utf-8")

    store = RecentFilesStore(storage, limit=2)
    store.add(files[0])
    store.add(files[1])
    store.add(files[2])
    store.add(files[0])

    paths = store.paths()
    assert len(paths) == 2
    assert paths[0] == files[0]
    assert paths[1] == files[2]


def test_recent_files_skips_missing(tmp_path: Path) -> None:
    storage = tmp_path / "recent.json"
    existing = tmp_path / "keep.pdf"
    existing.write_text("x", encoding="utf-8")
    missing = tmp_path / "gone.pdf"
    missing.write_text("x", encoding="utf-8")

    store = RecentFilesStore(storage, limit=10)
    store.add(missing)
    store.add(existing)
    missing.unlink()

    assert store.paths() == [existing]
