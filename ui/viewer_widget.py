"""Scrollable PDF page viewer.

Renders pages via the core ``PDFEngine.render_page`` call surface (contract 6.2),
consuming the ``RenderedPage.image_bytes`` PNG payload. Falls back to a placeholder
when no engine/document is wired (e.g. backend not yet merged in this wave).
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget


class ViewerWidget(QScrollArea):
    """Vertical stack of rendered page images."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self._engine: Any = None
        self._doc: Any = None

        self._container = QWidget()
        self._layout = QVBoxLayout(self._container)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._layout.setSpacing(12)
        self.setWidget(self._container)

        self._placeholder = QLabel("Open a PDF to start  (File ▸ Open…)")
        self._placeholder.setObjectName("viewerPlaceholder")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self._placeholder)

    def attach_engine(self, engine: Any) -> None:
        self._engine = engine

    def show_document(self, doc: Any) -> None:
        """Render every page of an opened core ``Document``."""
        self._doc = doc
        self._clear()
        if self._engine is None or doc is None:
            self._show_message("Viewer unavailable: core engine not wired yet.")
            return

        page_count = getattr(doc, "page_count", 0)
        for index in range(page_count):
            try:
                rendered = self._engine.render_page(doc, index)
                self._layout.addWidget(self._page_label(rendered))
            except Exception as exc:  # keep rendering remaining pages
                self._layout.addWidget(QLabel(f"[page {index} failed: {exc}]"))

    # -- internals -----------------------------------------------------------

    def _page_label(self, rendered: Any) -> QLabel:
        image = QImage.fromData(rendered.image_bytes, rendered.image_format.upper())
        label = QLabel()
        label.setPixmap(QPixmap.fromImage(image))
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label

    def _show_message(self, text: str) -> None:
        self._placeholder.setText(text)
        self._layout.addWidget(self._placeholder)

    def _clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None and widget is not self._placeholder:
                widget.deleteLater()
