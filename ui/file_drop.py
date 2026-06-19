"""Shared drag-and-drop helpers for opening PDF / P7M files."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QMimeData, Qt
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import QWidget

SUPPORTED_SUFFIXES = {".pdf", ".p7m"}


def is_supported_drop_path(path: Path) -> bool:
    """Return True when ``path`` is a PDF or P7M file we can open."""
    name = path.name.lower()
    return path.suffix.lower() in SUPPORTED_SUFFIXES or name.endswith(".pdf.p7m")


def first_dropped_path(mime: QMimeData) -> Path | None:
    """Extract the first supported local file from a drag payload."""
    if not mime.hasUrls():
        return None
    for url in mime.urls():
        if not url.isLocalFile():
            continue
        path = Path(url.toLocalFile())
        if path.is_file() and is_supported_drop_path(path):
            return path
    return None


def accept_file_drag(event: QDragEnterEvent | QDragMoveEvent) -> bool:
    """Accept a drag event when it carries a supported file."""
    if first_dropped_path(event.mimeData()) is not None:
        event.setDropAction(Qt.DropAction.CopyAction)
        event.acceptProposedAction()
        return True
    return False


def path_from_drop(event: QDropEvent) -> Path | None:
    """Accept a drop event and return the file path, if supported."""
    path = first_dropped_path(event.mimeData())
    if path is None:
        return None
    event.setDropAction(Qt.DropAction.CopyAction)
    event.acceptProposedAction()
    return path


def enable_file_drops(widget: QWidget) -> None:
    """Enable drag-and-drop on ``widget``."""
    widget.setAcceptDrops(True)


def enable_file_drops_tree(root: QWidget) -> None:
    """Enable drops on ``root`` and typical child surfaces that intercept them."""
    enable_file_drops(root)
    for child in root.findChildren(QWidget):
        name = child.metaObject().className()
        if name in {
            "QScrollArea",
            "QWidget",
            "QSplitter",
            "QFrame",
            "QListWidget",
            "QScrollAreaWidgetContents",
        }:
            enable_file_drops(child)
