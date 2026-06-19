"""Custom paint delegate for page thumbnail list items."""

from __future__ import annotations

from PySide6.QtCore import Qt, QSize, QRect
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem


class ThumbnailItemDelegate(QStyledItemDelegate):
    """Hover rim highlight and selected accent glow border."""

    _ACCENT = QColor("#1565C0")
    _RIM = QColor(68, 138, 255, 128)
    _RIM_GLOW = QColor(68, 138, 255, 40)
    _SELECTED_TINT = QColor(68, 138, 255, 20)
    _HOVER_BG = QColor("#242428")
    _TEXT = QColor("#9a9a9e")

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index,  # noqa: ANN001
    ) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        content = option.rect.adjusted(6, 3, -6, -3)

        if selected:
            painter.fillRect(option.rect, self._SELECTED_TINT)
            painter.fillRect(option.rect.left(), option.rect.top(), 3, option.rect.height(), self._ACCENT)
            glow_rect = content.adjusted(-2, -2, 2, 2)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self._RIM_GLOW)
            painter.drawRoundedRect(glow_rect, 6, 6)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(self._RIM, 1))
            painter.drawRoundedRect(content.adjusted(0, 0, -1, -1), 4, 4)
        elif hovered:
            painter.fillRect(content, self._HOVER_BG)
            painter.setPen(QPen(self._RIM, 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(content.adjusted(0, 0, -1, -1), 4, 4)

        icon = index.data(Qt.ItemDataRole.DecorationRole)
        text = index.data(Qt.ItemDataRole.DisplayRole)
        icon_size = option.decorationSize if not option.decorationSize.isEmpty() else QSize(80, 110)

        if icon is not None:
            icon_rect = self._centered_rect(content, icon_size)
            if hovered and not selected:
                painter.setOpacity(0.92)
                painter.fillRect(icon_rect.adjusted(-1, -1, 1, 1), QColor(255, 255, 255, 18))
                painter.setOpacity(1.0)
            icon.paint(painter, icon_rect, Qt.AlignmentFlag.AlignCenter)

        if text:
            painter.setPen(self._TEXT if not selected else QColor("#e8e8ea"))
            text_rect = content
            text_rect.setTop(content.bottom() - 18)
            painter.drawText(text_rect, int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter), str(text))

        painter.restore()

    @staticmethod
    def _centered_rect(outer: QRect, size: QSize) -> QRect:
        x = outer.x() + max(0, (outer.width() - size.width()) // 2)
        y = outer.y() + max(0, (outer.height() - size.height() - 16) // 2)
        return QRect(x, y, size.width(), size.height())
