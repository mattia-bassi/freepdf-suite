"""PDF page label with drag-to-select text and copy support."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, Qt, QRectF, Signal
from PySide6.QtGui import (
    QAction,
    QColor,
    QGuiApplication,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
)
from PySide6.QtWidgets import QLabel, QMenu

from core.text_selection import Rect, WordEntry, selected_words_anchor_focus

from .i18n import tr

if TYPE_CHECKING:
    from .pdf_reader import PdfReaderWidget

SELECTION_FILL = QColor(68, 138, 255, 76)
SELECTION_OUTLINE = QColor(68, 138, 255, 180)
DRAG_THRESHOLD_PX = 4


class PageViewLabel(QLabel):
    """Rendered PDF page with mouse text selection overlay."""

    selection_changed = Signal()

    def __init__(self, page_index: int, *, reader: PdfReaderWidget) -> None:
        super().__init__(reader._container)
        self._page_index = page_index
        self._reader = reader
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setProperty("page_index", page_index)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
        self.setMargin(0)
        self.setContentsMargins(0, 0, 0, 0)

        self._press_pos: QPointF | None = None
        self._drag_pos: QPointF | None = None
        self._dragging = False
        self._word_cache: list[WordEntry] | None = None
        self._highlight_rects: list[Rect] = []
        self._highlight_text = ""
        self._drag_rects: list[Rect] = []

    @property
    def page_index(self) -> int:
        return self._page_index

    @property
    def selected_text(self) -> str:
        return self._highlight_text

    def has_selection(self) -> bool:
        return bool(self._highlight_text)

    def clear_selection(self) -> None:
        self._press_pos = None
        self._drag_pos = None
        self._dragging = False
        self._highlight_rects = []
        self._highlight_text = ""
        self._drag_rects = []
        self.update()

    def copy_selection(self) -> bool:
        if not self._highlight_text:
            return False
        clipboard = QGuiApplication.clipboard()
        if clipboard is None:
            return False
        clipboard.setText(self._highlight_text)
        return True

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        self._reader.clear_selection(except_page=self._page_index)
        self._highlight_rects = []
        self._highlight_text = ""
        self._drag_rects = []
        self._press_pos = event.position()
        self._drag_pos = self._press_pos
        self._dragging = False
        self.setFocus()
        self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._press_pos is None or not (event.buttons() & Qt.MouseButton.LeftButton):
            super().mouseMoveEvent(event)
            return
        self._drag_pos = event.position()
        if not self._dragging:
            delta = self._drag_pos - self._press_pos
            if delta.manhattanLength() < DRAG_THRESHOLD_PX:
                return
            self._dragging = True
            self._reader.clear_selection(except_page=self._page_index)
            self._highlight_rects = []
            self._highlight_text = ""
        self._update_drag_preview()
        self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self._press_pos is not None:
            if self._dragging and self._drag_pos is not None:
                rects, text = self._anchor_focus_selection(
                    self._press_pos, self._drag_pos
                )
                self._highlight_rects = rects
                self._highlight_text = text
                self._drag_rects = []
                self.selection_changed.emit()
            elif not self._dragging:
                self.clear_selection()
                self._reader.clear_selection(except_page=self._page_index)
                self.selection_changed.emit()
            self._press_pos = None
            self._drag_pos = None
            self._dragging = False
            self.update()
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event) -> None:  # noqa: ANN001, N802
        if not self._highlight_text:
            return
        menu = QMenu(self)
        copy_action = QAction(tr("viewer_copy"), self)
        copy_action.triggered.connect(self.copy_selection)
        menu.addAction(copy_action)
        menu.exec(event.globalPos())

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        super().paintEvent(event)
        rects = self._drag_rects if self._dragging else self._highlight_rects
        if not rects:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(SELECTION_OUTLINE)
        pen.setWidth(1)
        painter.setPen(pen)
        for pdf_rect in rects:
            widget_rect = self._reader.pdf_rect_to_widget(self._page_index, pdf_rect)
            if widget_rect is None:
                continue
            x0, y0, x1, y1 = widget_rect
            painter.fillRect(QRectF(x0, y0, x1 - x0, y1 - y0), SELECTION_FILL)
            painter.drawRect(QRectF(x0, y0, x1 - x0, y1 - y0))
        painter.end()

    def _words(self) -> list[WordEntry]:
        if self._word_cache is None:
            self._word_cache = self._reader.words_for_page(self._page_index)
        return self._word_cache

    def invalidate_word_cache(self) -> None:
        self._word_cache = None

    def _page_width_pt(self) -> float | None:
        if self._reader._engine is None or self._reader._doc is None:
            return None
        try:
            info = self._reader._engine.page_info(
                self._reader._doc, self._page_index
            )
            return float(info.width)
        except Exception:
            return None

    def _anchor_focus_selection(
        self, start: QPointF, end: QPointF
    ) -> tuple[list[Rect], str]:
        anchor, focus = self._selection_points_pdf(start, end)
        return selected_words_anchor_focus(
            self._words(),
            anchor,
            focus,
            page_width=self._page_width_pt(),
        )

    def _update_drag_preview(self) -> None:
        if self._press_pos is None or self._drag_pos is None:
            self._drag_rects = []
            return
        rects, _text = self._anchor_focus_selection(self._press_pos, self._drag_pos)
        self._drag_rects = rects

    def _selection_points_pdf(
        self, start: QPointF, end: QPointF
    ) -> tuple[tuple[float, float], tuple[float, float]]:
        anchor = self._reader.widget_point_to_pdf(
            self._page_index, start.x(), start.y()
        )
        focus = self._reader.widget_point_to_pdf(self._page_index, end.x(), end.y())
        return anchor, focus
