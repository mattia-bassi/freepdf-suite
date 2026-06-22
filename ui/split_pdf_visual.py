"""Visual widgets for the split-PDF dialog."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

SPLIT_ACTIVE = QColor("#448aff")
SPLIT_INACTIVE = QColor("#55585c")
SPLIT_HOVER = QColor("#7eb0ff")
THUMB_WIDTH = 80
THUMB_HEIGHT = 110
SPLIT_HIT_WIDTH = 20


class SplitPointWidget(QWidget):
    """Clickable split marker between two page thumbnails."""

    toggled = Signal(int)

    def __init__(self, index: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._index = index
        self._active = False
        self._hovered = False
        self.setFixedWidth(SPLIT_HIT_WIDTH)
        self.setMinimumHeight(THUMB_HEIGHT + 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("")

    @property
    def split_index(self) -> int:
        return self._index

    def is_active(self) -> bool:
        return self._active

    def set_active(self, active: bool) -> None:
        self._active = active
        self.update()

    def enterEvent(self, event) -> None:  # noqa: ANN001, N802
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: ANN001, N802
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: ANN001, N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._active = not self._active
            self.update()
            self.toggled.emit(self._index)
        super().mousePressEvent(event)

    def paintEvent(self, _event) -> None:  # noqa: ANN001, N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        center_x = self.width() / 2.0
        top = 8.0
        bottom = float(self.height() - 20)

        if self._active:
            color = SPLIT_ACTIVE
        elif self._hovered:
            color = SPLIT_HOVER
        else:
            color = SPLIT_INACTIVE

        pen = QPen(color)
        pen.setWidth(2 if self._active or self._hovered else 1)
        painter.setPen(pen)
        painter.drawLine(int(center_x), int(top), int(center_x), int(bottom))

        painter.setPen(color)
        font = painter.font()
        font.setPointSize(11 if self._active or self._hovered else 9)
        painter.setFont(font)
        painter.drawText(self.rect(), int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter), "✂")
        painter.end()


class PageThumbWidget(QWidget):
    """Single page thumbnail with page number label."""

    def __init__(self, page_index: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._page_index = page_index
        self.setFixedWidth(THUMB_WIDTH + 8)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._image = QLabel()
        self._image.setObjectName("splitPdfThumbImage")
        self._image.setFixedSize(THUMB_WIDTH, THUMB_HEIGHT)
        self._image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image.setStyleSheet("background-color: #1e1e1e; border-radius: 4px;")

        self._label = QLabel(str(page_index + 1))
        self._label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._label.setObjectName("splitPdfThumbLabel")

        layout.addWidget(self._image, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._label)

    def set_pixmap(self, pixmap: QPixmap) -> None:
        scaled = pixmap.scaled(
            THUMB_WIDTH,
            THUMB_HEIGHT,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._image.setPixmap(scaled)


class SplitPdfThumbnailStrip(QWidget):
    """Horizontally scrollable strip of page thumbnails with split markers."""

    split_changed = Signal()

    def __init__(
        self,
        parent: QWidget | None,
        *,
        engine: Any,
        doc: Any,
        page_count: int,
    ) -> None:
        super().__init__(parent)
        self._engine = engine
        self._doc = doc
        self._page_count = page_count
        self._splitters: dict[int, SplitPointWidget] = {}
        self._thumbs: list[PageThumbWidget] = []
        self._pending: list[int] = []
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._load_next_batch)

        row_host = QWidget()
        self._row = QHBoxLayout(row_host)
        self._row.setContentsMargins(8, 8, 8, 8)
        self._row.setSpacing(0)

        for index in range(page_count):
            thumb = PageThumbWidget(index, row_host)
            self._thumbs.append(thumb)
            self._row.addWidget(thumb)
            if index < page_count - 1:
                splitter = SplitPointWidget(index, row_host)
                splitter.toggled.connect(self._on_split_toggled)
                self._splitters[index] = splitter
                self._row.addWidget(splitter)

        self._row.addStretch(1)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setWidget(row_host)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self._pending = list(range(page_count))
        if self._pending:
            self._timer.start(0)

    def active_split_points(self) -> list[int]:
        return sorted(index for index, widget in self._splitters.items() if widget.is_active())

    def _on_split_toggled(self, _index: int) -> None:
        self.split_changed.emit()

    def _load_next_batch(self) -> None:
        if not self._pending:
            self._timer.stop()
            return
        for _ in range(3):
            if not self._pending:
                break
            index = self._pending.pop(0)
            try:
                rendered = self._engine.render_page(self._doc, index, dpi=48)
                image = QImage.fromData(rendered.image_bytes, "PNG")
                self._thumbs[index].set_pixmap(QPixmap.fromImage(image))
            except Exception:
                pass
        if self._pending:
            self._timer.start(10)
        else:
            self._timer.stop()
