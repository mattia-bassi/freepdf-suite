"""Rounded floating card containers for the dashboard-style shell layout."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget

from .visual_effects import card_shadow


class FloatingCard(QFrame):
    """Elevated panel with internal padding, rounded corners, and drop shadow."""

    def __init__(
        self,
        object_name: str,
        parent: QWidget | None = None,
        *,
        padding: int = 16,
    ) -> None:
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(padding, padding, padding, padding)
        self._layout.setSpacing(0)
        card_shadow(self)

    @property
    def content_layout(self) -> QVBoxLayout:
        return self._layout

    def set_content(self, widget: QWidget, *, stretch: int = 0) -> None:
        """Place a single child widget inside the card."""
        while self._layout.count():
            item = self._layout.takeAt(0)
            child = item.widget()
            if child is not None:
                child.setParent(None)
        if stretch:
            self._layout.addWidget(widget, stretch)
        else:
            self._layout.addWidget(widget)
