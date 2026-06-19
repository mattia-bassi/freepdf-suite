"""Tests for shared file drag-and-drop helpers."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QMimeData, QPoint, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QApplication, QMainWindow

from ui.file_drop import (
    accept_file_drag,
    enable_file_drops,
    first_dropped_path,
    is_supported_drop_path,
    path_from_drop,
)


def _ensure_qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        app = QApplication([])
    return app


def test_is_supported_drop_path() -> None:
    assert is_supported_drop_path(Path("doc.pdf"))
    assert is_supported_drop_path(Path("signed.p7m"))
    assert is_supported_drop_path(Path("file.pdf.p7m"))
    assert not is_supported_drop_path(Path("notes.txt"))


def test_first_dropped_path_from_mime(tmp_path: Path) -> None:
    pdf = tmp_path / "sample.pdf"
    pdf.write_text("x", encoding="utf-8")
    mime = QMimeData()
    mime.setUrls(
        [
            QUrl.fromLocalFile(str(tmp_path / "missing.pdf")),
            QUrl.fromLocalFile(str(pdf)),
        ]
    )
    assert first_dropped_path(mime) == pdf


def test_drop_events_on_main_window_and_reader(tmp_path: Path) -> None:
    _ensure_qapp()
    from ui.pdf_reader import PdfReaderWidget

    window = QMainWindow()
    enable_file_drops(window)
    reader = PdfReaderWidget({})
    window.setCentralWidget(reader)

    assert window.acceptDrops()
    assert reader.acceptDrops()
    assert reader._scroll.viewport().acceptDrops()

    pdf = tmp_path / "drop.pdf"
    pdf.write_text("x", encoding="utf-8")
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(pdf))])

    dropped: list[Path] = []
    reader.file_dropped.connect(lambda path: dropped.append(path))

    enter = QDragEnterEvent(
        QPoint(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    assert accept_file_drag(enter)

    drop = QDropEvent(
        QPoint(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    path = path_from_drop(drop)
    assert path == pdf

    reader._emit_dropped_file(path)
    assert dropped == [pdf]

    window.close()


def test_main_window_class_enables_drops() -> None:
    """MainWindow constructor must call enable_file_drops (PyInstaller fix)."""
    import inspect

    from ui.main_window import MainWindow

    source = inspect.getsource(MainWindow.__init__)
    assert "enable_file_drops(self)" in source
    assert "def dropEvent" in inspect.getsource(MainWindow)
