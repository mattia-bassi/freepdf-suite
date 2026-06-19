"""Persistent recent-files list for File ▸ Recent Files."""

from __future__ import annotations

import json
from pathlib import Path


class RecentFilesStore:
    """Load/save a bounded list of recently opened document paths."""

    def __init__(self, storage_path: Path, *, limit: int = 10) -> None:
        self._path = storage_path
        self._limit = max(1, limit)
        self._entries: list[str] = []
        self._load()

    @property
    def limit(self) -> int:
        return self._limit

    def paths(self) -> list[Path]:
        """Return existing files only, most recent first."""
        result: list[Path] = []
        for raw in self._entries:
            path = Path(raw)
            if path.is_file():
                result.append(path)
        return result

    def add(self, path: Path) -> None:
        """Record ``path`` as the most recently opened file."""
        try:
            key = str(path.resolve())
        except OSError:
            key = str(path)
        self._entries = [entry for entry in self._entries if entry != key]
        self._entries.insert(0, key)
        self._entries = self._entries[: self._limit]
        self._save()

    def _load(self) -> None:
        if not self._path.is_file():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if isinstance(data, list):
            self._entries = [str(item) for item in data][: self._limit]

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._entries, indent=2),
            encoding="utf-8",
        )
