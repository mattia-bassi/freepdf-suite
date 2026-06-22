"""Branded QMessageBox helpers with consistent titles and tone."""

from __future__ import annotations

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMessageBox, QWidget

from .bootstrap import LOGO_ICO_PATH, LOGO_PATH
from .i18n import tr


def _app_icon() -> QIcon:
    if LOGO_ICO_PATH.is_file():
        return QIcon(str(LOGO_ICO_PATH))
    if LOGO_PATH.is_file():
        return QIcon(str(LOGO_PATH))
    return QIcon()


def _prepare(parent: QWidget | None) -> QMessageBox:
    box = QMessageBox(parent)
    box.setWindowTitle(tr("app_title"))
    icon = _app_icon()
    if not icon.isNull():
        box.setWindowIcon(icon)
    return box


def show_warning(parent: QWidget | None, text: str) -> None:
    """Show a branded warning message."""
    box = _prepare(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setText(text)
    box.exec()


def show_critical(parent: QWidget | None, text: str) -> None:
    """Show a branded error message."""
    box = _prepare(parent)
    box.setIcon(QMessageBox.Icon.Critical)
    box.setText(text)
    box.exec()


def show_information(parent: QWidget | None, text: str) -> None:
    """Show a branded information message."""
    box = _prepare(parent)
    box.setIcon(QMessageBox.Icon.Information)
    box.setText(text)
    box.exec()


def ask_yes_no(parent: QWidget | None, text: str) -> bool:
    """Ask a yes/no question with the app title in the window bar."""
    box = _prepare(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setText(text)
    box.setStandardButtons(
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    box.setDefaultButton(QMessageBox.StandardButton.No)
    return box.exec() == QMessageBox.StandardButton.Yes


def ask_save_discard_cancel(parent: QWidget | None, text: str) -> str:
    """Ask whether to save, discard, or cancel. Returns ``save``, ``discard``, or ``cancel``."""
    box = _prepare(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setText(text)
    save_button = box.addButton(tr("save"), QMessageBox.ButtonRole.AcceptRole)
    discard_button = box.addButton(tr("discard_changes"), QMessageBox.ButtonRole.DestructiveRole)
    cancel_button = box.addButton(tr("cancel"), QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(cancel_button)
    box.exec()
    clicked = box.clickedButton()
    if clicked is save_button:
        return "save"
    if clicked is discard_button:
        return "discard"
    return "cancel"
