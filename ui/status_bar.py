"""Status bar helpers with brief highlight feedback."""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QStatusBar

_FLASH_MS = 900


def _clear_status_flash(bar: QStatusBar) -> None:
    if bar.property("flash") != "true":
        return
    bar.setProperty("flash", "false")
    bar.style().unpolish(bar)
    bar.style().polish(bar)
    bar.update()


def show_status_message(bar: QStatusBar, message: str, *, flash: bool = True) -> None:
    """Show a status message with an optional accent-color flash."""
    _clear_status_flash(bar)
    bar.showMessage(message)
    if not flash or not message.strip():
        return
    bar.setProperty("flash", "true")
    bar.style().unpolish(bar)
    bar.style().polish(bar)
    bar.update()
    QTimer.singleShot(_FLASH_MS, lambda: _clear_status_flash(bar))
