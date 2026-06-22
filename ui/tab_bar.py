"""Document tab strip for multi-file PDF viewing."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileIconProvider,
    QHBoxLayout,
    QMenu,
    QTabBar,
    QToolButton,
    QWidget,
)

from .file_drop import accept_file_drag, enable_file_drops, path_from_drop
from .i18n import tr


class DocumentTabBar(QWidget):
    """Scrollable tab bar with per-tab close buttons and context menu."""

    tab_selected = Signal(int)
    tab_close_requested = Signal(int)
    close_others_requested = Signal(int)
    close_all_requested = Signal()
    file_dropped_on_tab = Signal(int, object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("documentTabBarHost")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._bar = QTabBar(self)
        self._bar.setObjectName("documentTabBar")
        self._bar.setDocumentMode(True)
        self._bar.setExpanding(False)
        self._bar.setMovable(False)
        self._bar.setUsesScrollButtons(True)
        self._bar.setElideMode(Qt.TextElideMode.ElideMiddle)
        self._bar.setTabsClosable(False)
        self._bar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._bar.customContextMenuRequested.connect(self._on_context_menu)
        self._bar.currentChanged.connect(self._on_current_changed)
        layout.addWidget(self._bar, 1)

        self._icon = QFileIconProvider().icon(QFileIconProvider.IconType.File)
        self._close_buttons: dict[int, QToolButton] = {}
        self._suppress_current_changed = False
        self._context_index = -1

        enable_file_drops(self._bar)

    def tab_count(self) -> int:
        return self._bar.count()

    def set_current_index(self, index: int) -> None:
        if index < 0 or index >= self._bar.count():
            return
        self._suppress_current_changed = True
        self._bar.setCurrentIndex(index)
        self._suppress_current_changed = False

    def sync_tabs(self, labels: list[str]) -> None:
        """Rebuild tabs to match ``labels`` while preserving selection when possible."""
        current = self._bar.currentIndex()
        self._suppress_current_changed = True
        while self._bar.count():
            self._bar.removeTab(0)
        self._close_buttons.clear()

        for index, label in enumerate(labels):
            self._bar.addTab(self._icon, label)
            self._install_close_button(index)

        if labels:
            target = current if 0 <= current < len(labels) else len(labels) - 1
            self._bar.setCurrentIndex(target)
        self._suppress_current_changed = False

    def update_tab_text(self, index: int, text: str) -> None:
        if 0 <= index < self._bar.count():
            self._bar.setTabText(index, text)
            self._bar.setTabIcon(index, self._icon)

    def _install_close_button(self, index: int) -> None:
        button = QToolButton(self)
        button.setObjectName("documentTabCloseButton")
        button.setText("✕")
        button.setAutoRaise(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(
            lambda _checked=False, tab_index=index: self.tab_close_requested.emit(
                tab_index
            )
        )
        self._bar.setTabButton(index, QTabBar.ButtonPosition.RightSide, button)
        self._close_buttons[index] = button

    def _on_current_changed(self, index: int) -> None:
        if self._suppress_current_changed or index < 0:
            return
        self.tab_selected.emit(index)

    def _on_context_menu(self, pos: QPoint) -> None:
        index = self._bar.tabAt(pos)
        if index < 0:
            return
        self._context_index = index
        menu = QMenu(self)
        close_action = QAction(tr("close_tab"), self)
        close_action.triggered.connect(
            lambda: self.tab_close_requested.emit(self._context_index)
        )
        others_action = QAction(tr("close_other_tabs"), self)
        others_action.setEnabled(self._bar.count() > 1)
        others_action.triggered.connect(
            lambda: self.close_others_requested.emit(self._context_index)
        )
        all_action = QAction(tr("close_all_tabs"), self)
        all_action.triggered.connect(self.close_all_requested.emit)
        menu.addAction(close_action)
        menu.addAction(others_action)
        menu.addAction(all_action)
        menu.exec(self._bar.mapToGlobal(pos))

    def dragEnterEvent(self, event) -> None:  # noqa: ANN001, N802
        if accept_file_drag(event):
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:  # noqa: ANN001, N802
        if accept_file_drag(event):
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:  # noqa: ANN001, N802
        path = path_from_drop(event)
        if path is None:
            super().dropEvent(event)
            return
        index = self._bar.tabAt(event.position().toPoint())
        if index < 0 and self._bar.count() > 0:
            index = self._bar.currentIndex()
        if index < 0:
            index = 0
        self.file_dropped_on_tab.emit(index, Path(path))
        event.acceptProposedAction()
