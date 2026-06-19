"""Semi-transparent OCR progress overlay for the PDF viewer."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from .i18n import register_retranslate, tr


class OcrProcessingOverlay(QWidget):
    """Non-modal dim overlay with message and progress bar."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("ocrProcessingOverlay")
        self.hide()

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        panel = QWidget(self)
        panel.setObjectName("ocrProcessingPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(24, 20, 24, 20)
        panel_layout.setSpacing(10)

        self._message = QLabel(panel)
        self._message.setObjectName("ocrProcessingMessage")
        self._message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_layout.addWidget(self._message)

        self._progress = QProgressBar(panel)
        self._progress.setObjectName("ocrProgressBar")
        self._progress.setFixedWidth(280)
        self._progress.setTextVisible(True)
        panel_layout.addWidget(self._progress, 0, Qt.AlignmentFlag.AlignHCenter)

        layout.addWidget(panel, 0, Qt.AlignmentFlag.AlignCenter)
        self._unregister_i18n = register_retranslate(self.retranslate_ui)
        self.destroyed.connect(lambda _obj=None: self._unregister_i18n())
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self._message.setText(tr("ocr_overlay_message"))

    def set_progress(self, current: int, total: int) -> None:
        maximum = max(1, total)
        self._progress.setMaximum(maximum)
        self._progress.setValue(min(current, maximum))
        percent = int(round(100 * current / maximum))
        self._progress.setFormat(f"{percent}%")

    def show_overlay(self) -> None:
        if self.parentWidget() is not None:
            self.setGeometry(self.parentWidget().rect())
        self.set_progress(0, 1)
        self.show()
        self.raise_()

    def hide_overlay(self) -> None:
        self.hide()

    def resize_with_parent(self) -> None:
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(parent.rect())
