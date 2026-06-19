"""Page thumbnail sidebar with lazy background loading."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, QTimer, Signal, QSize
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from .i18n import tr
from .thumbnail_delegate import ThumbnailItemDelegate


class ThumbnailPanel(QWidget):
    """Vertical list of page thumbnails; loads lazily via a timer queue."""

    page_selected = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("thumbnailPanel")
        self.setMinimumWidth(120)
        self.setMaximumWidth(180)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 4, 4)
        self._title = QLabel(tr("pages"))
        self._title.setObjectName("thumbnailTitle")
        layout.addWidget(self._title)

        self._list = QListWidget()
        self._list.setObjectName("thumbnailList")
        self._list.setIconSize(QSize(80, 110))
        self._list.setSpacing(4)
        self._list.setMouseTracking(True)
        self._list.viewport().setMouseTracking(True)
        self._list.setItemDelegate(ThumbnailItemDelegate(self._list))
        self._list.currentRowChanged.connect(self._on_row_changed)
        layout.addWidget(self._list)

        self._block_signals = False
        self._engine: Any = None
        self._doc: Any = None
        self._thumb_dpi = 48
        self._pending: list[int] = []
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._load_next_batch)

    def retranslate_ui(self) -> None:
        """Refresh panel labels for the active language."""
        self._title.setText(tr("pages"))

    def clear_thumbnails(self) -> None:
        self.stop_lazy_load()
        self._list.clear()

    def prepare(self, page_count: int) -> None:
        """Create placeholder items without rendering."""
        self.clear_thumbnails()
        for index in range(page_count):
            item = QListWidgetItem(str(index + 1))
            item.setData(Qt.ItemDataRole.UserRole, index)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._list.addItem(item)

    def start_lazy_load(self, engine: Any, doc: Any, *, dpi: int = 48) -> None:
        """Queue thumbnail renders processed in small batches."""
        self._engine = engine
        self._doc = doc
        self._thumb_dpi = dpi
        self._pending = list(range(int(getattr(doc, "page_count", 0))))
        if self._pending:
            self._timer.start(0)

    def stop_lazy_load(self) -> None:
        self._timer.stop()
        self._pending.clear()
        self._engine = None
        self._doc = None

    def set_current_page(self, page_index: int) -> None:
        if page_index < 0 or page_index >= self._list.count():
            return
        self._block_signals = True
        self._list.setCurrentRow(page_index)
        self._list.scrollToItem(self._list.item(page_index))
        self._block_signals = False

    def _load_next_batch(self) -> None:
        if not self._pending or self._engine is None or self._doc is None:
            self._timer.stop()
            return
        for _ in range(3):
            if not self._pending:
                break
            index = self._pending.pop(0)
            item = self._list.item(index)
            if item is None:
                continue
            try:
                rendered = self._engine.render_page(self._doc, index, dpi=self._thumb_dpi)
                image = QImage.fromData(rendered.image_bytes, "PNG")
                item.setIcon(QIcon(QPixmap.fromImage(image)))
            except Exception:
                pass
        if self._pending:
            self._timer.start(10)
        else:
            self._timer.stop()

    def _on_row_changed(self, row: int) -> None:
        if self._block_signals or row < 0:
            return
        item = self._list.item(row)
        if item is None:
            return
        page_index = item.data(Qt.ItemDataRole.UserRole)
        if page_index is not None:
            self.page_selected.emit(int(page_index))
