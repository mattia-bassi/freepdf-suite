"""Page thumbnail sidebar with lazy background loading and page management."""

from __future__ import annotations

from typing import Any

from core.errors import DocumentOpenError, PageIndexError
from PySide6.QtCore import Qt, QTimer, Signal, QSize, QPoint
from PySide6.QtGui import QAction, QIcon, QImage, QPixmap, QTransform
from PySide6.QtWidgets import (
    QAbstractItemView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QVBoxLayout,
    QWidget,
)

from .i18n import tr
from .thumbnail_delegate import ThumbnailItemDelegate


class ThumbnailListWidget(QListWidget):
    """Thumbnail list with internal drag-and-drop page reordering."""

    pages_reordered = Signal(int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDropIndicatorShown(True)
        self._drag_source_row = -1

    def startDrag(self, supported_actions) -> None:  # noqa: ANN001, N802
        self._drag_source_row = self.currentRow()
        super().startDrag(supported_actions)

    def dropEvent(self, event) -> None:  # noqa: ANN001, N802
        from_row = self._drag_source_row
        if from_row < 0:
            event.ignore()
            return

        point = (
            event.position().toPoint() if hasattr(event, "position") else event.pos()
        )
        target_item = self.itemAt(point)
        if target_item is None:
            to_row = self.count() - 1
        else:
            to_row = self.row(target_item)
            if point.y() > self.visualItemRect(target_item).center().y():
                to_row += 1
        to_row = max(0, min(to_row, self.count() - 1))

        event.setDropAction(Qt.DropAction.IgnoreAction)
        event.accept()
        self._drag_source_row = -1

        if from_row != to_row:
            self.pages_reordered.emit(from_row, to_row)


class ThumbnailPanel(QWidget):
    """Vertical list of page thumbnails; loads lazily via a timer queue."""

    page_selected = Signal(int)
    pages_reordered = Signal(int, int)
    page_rotate_left = Signal(int)
    page_rotate_right = Signal(int)
    page_delete_requested = Signal(int)
    page_insert_requested = Signal(int)

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

        self._list = ThumbnailListWidget()
        self._list.setObjectName("thumbnailList")
        self._list.setIconSize(QSize(80, 110))
        self._list.setSpacing(4)
        self._list.setMouseTracking(True)
        self._list.viewport().setMouseTracking(True)
        self._list.setItemDelegate(ThumbnailItemDelegate(self._list))
        self._list.currentRowChanged.connect(self._on_row_changed)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_context_menu)
        self._list.pages_reordered.connect(self.pages_reordered.emit)
        layout.addWidget(self._list, 1)

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

    def load_document(
        self,
        engine: Any,
        doc: Any,
        *,
        dpi: int = 48,
        current_page: int = 0,
    ) -> None:
        """Clear and reload thumbnails for a different open document."""
        self.stop_lazy_load()
        page_count = int(getattr(doc, "page_count", 0))
        if page_count <= 0:
            self.clear_thumbnails()
            return
        self.prepare(page_count)
        self.start_lazy_load(engine, doc, dpi=dpi)
        self.set_current_page(min(max(0, current_page), page_count - 1))

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

    def refresh(self, engine: Any, doc: Any, *, dpi: int = 48) -> None:
        """Rebuild thumbnails after page structure changes."""
        page_count = int(getattr(doc, "page_count", 0))
        self.prepare(page_count)
        self.start_lazy_load(engine, doc, dpi=dpi)

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

    def list_widget(self) -> ThumbnailListWidget:
        return self._list

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
                rendered = self._engine.render_page(
                    self._doc, index, dpi=self._thumb_dpi
                )
                image = QImage.fromData(rendered.image_bytes, "PNG")
                pixmap = QPixmap.fromImage(image)
                rotation = 0
                try:
                    rotation = int(self._engine.page_info(self._doc, index).rotation)
                except (DocumentOpenError, PageIndexError, OSError, RuntimeError):
                    pass
                if rotation in (90, 180, 270):
                    pixmap = pixmap.transformed(
                        QTransform().rotate(rotation),
                        Qt.TransformationMode.SmoothTransformation,
                    )
                item.setIcon(QIcon(pixmap))
            except (
                DocumentOpenError,
                PageIndexError,
                OSError,
                RuntimeError,
                ValueError,
            ):
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

    def _on_context_menu(self, pos: QPoint) -> None:
        item = self._list.itemAt(pos)
        if item is None:
            return
        page_index = int(item.data(Qt.ItemDataRole.UserRole))
        menu = QMenu(self)
        rotate_left = QAction(tr("page_rotate_left"), self)
        rotate_left.triggered.connect(lambda: self.page_rotate_left.emit(page_index))
        rotate_right = QAction(tr("page_rotate_right"), self)
        rotate_right.triggered.connect(lambda: self.page_rotate_right.emit(page_index))
        insert_pages = QAction(tr("page_insert_here"), self)
        insert_pages.triggered.connect(
            lambda: self.page_insert_requested.emit(page_index)
        )
        delete_page = QAction(tr("page_delete"), self)
        delete_page.triggered.connect(
            lambda: self.page_delete_requested.emit(page_index)
        )
        menu.addAction(rotate_left)
        menu.addAction(rotate_right)
        menu.addSeparator()
        menu.addAction(insert_pages)
        menu.addSeparator()
        menu.addAction(delete_page)
        menu.exec(self._list.mapToGlobal(pos))
