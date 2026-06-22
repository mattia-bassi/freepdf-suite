"""Branded splash screen shown while the main window loads."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QApplication, QSplashScreen

from .bootstrap import LOGO_PATH
from .i18n import tr
from .style import (
    BG_CONTENT,
    BG_DARKEST,
    INTERACTION_BORDER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


def _build_splash_pixmap() -> QPixmap:
    """Render the splash artwork with gradient background and rounded corners."""
    width, height = 400, 280
    radius = 12
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    clip = QPainterPath()
    clip.addRoundedRect(0, 0, width, height, radius, radius)
    painter.setClipPath(clip)

    gradient = QLinearGradient(0, 0, 0, height)
    gradient.setColorAt(0, QColor(BG_DARKEST))
    gradient.setColorAt(1, QColor(BG_CONTENT))
    painter.fillRect(0, 0, width, height, gradient)

    painter.setClipping(False)
    glow = QColor(INTERACTION_BORDER)
    glow.setAlpha(80)
    painter.setPen(QPen(glow, 1))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(0.5, 0.5, width - 1, height - 1, radius, radius)

    logo_size = 96
    logo_y = 52
    if LOGO_PATH.is_file():
        logo = QPixmap(str(LOGO_PATH)).scaled(
            logo_size,
            logo_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        logo_x = (width - logo.width()) // 2
        painter.drawPixmap(logo_x, logo_y, logo)

    title_font = QFont()
    title_font.setPixelSize(18)
    title_font.setWeight(QFont.Weight.Bold)
    painter.setFont(title_font)
    painter.setPen(QColor(TEXT_PRIMARY))
    title = tr("app_title")
    title_y = logo_y + logo_size + 28
    painter.drawText(0, title_y, width, 24, int(Qt.AlignmentFlag.AlignHCenter), title)

    subtitle_font = QFont()
    subtitle_font.setPixelSize(11)
    painter.setFont(subtitle_font)
    painter.setPen(QColor(TEXT_SECONDARY))
    painter.drawText(
        0,
        title_y + 26,
        width,
        18,
        int(Qt.AlignmentFlag.AlignHCenter),
        tr("loading"),
    )

    painter.end()
    return pixmap


class BrandedSplashScreen(QSplashScreen):
    """Application splash with brand gradient, logo, and loading subtitle."""

    def __init__(self) -> None:
        pixmap = _build_splash_pixmap()
        super().__init__(
            pixmap,
            Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint,
        )
        self.setMask(pixmap.mask())

    @classmethod
    def show_while_loading(cls, app: QApplication) -> BrandedSplashScreen:
        """Display the splash and process pending events once."""
        splash = cls()
        splash.show()
        app.processEvents()
        return splash
