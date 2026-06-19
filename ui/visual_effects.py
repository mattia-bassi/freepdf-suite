"""Reusable drop-shadow presets for EaseOut-style dark UI depth."""

from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget


def apply_shadow(
    widget: QWidget,
    *,
    blur: float = 8,
    dx: float = 0,
    dy: float = 2,
    color: QColor | None = None,
) -> QGraphicsDropShadowEffect:
    """Attach or update a drop shadow on a widget."""
    if color is None:
        color = QColor(0, 0, 0, 128)
    effect = widget.graphicsEffect()
    if not isinstance(effect, QGraphicsDropShadowEffect):
        effect = QGraphicsDropShadowEffect(widget)
        widget.setGraphicsEffect(effect)
    effect.setBlurRadius(blur)
    effect.setOffset(dx, dy)
    effect.setColor(color)
    return effect


def clear_shadow(widget: QWidget) -> None:
    """Remove any graphics effect from a widget."""
    widget.setGraphicsEffect(None)


def card_shadow(widget: QWidget) -> QGraphicsDropShadowEffect:
    """Floating card shadow: 0 4px 16px rgba(0,0,0,0.4)."""
    return apply_shadow(widget, blur=16, dy=4, color=QColor(0, 0, 0, 102))


def navbar_bottom_shadow(widget: QWidget) -> QGraphicsDropShadowEffect:
    """Navbar strip shadow: 0 2px 8px rgba(0,0,0,0.5)."""
    return apply_shadow(widget, blur=8, dy=2, color=QColor(0, 0, 0, 128))


def accent_tab_glow(widget: QWidget) -> QGraphicsDropShadowEffect:
    """Active tab pill glow: 0 2px 6px rgba(68,138,255,0.35)."""
    return apply_shadow(widget, blur=6, dy=2, color=QColor(68, 138, 255, 89))


def popup_shadow(widget: QWidget) -> QGraphicsDropShadowEffect:
    """Dropdown/dialog popup shadow: 0 8px 24px rgba(0,0,0,0.6)."""
    return apply_shadow(widget, blur=24, dy=8, color=QColor(0, 0, 0, 153))


def primary_button_glow(widget: QWidget) -> QGraphicsDropShadowEffect:
    """Primary action button glow: 0 2px 8px rgba(68,138,255,0.3)."""
    return apply_shadow(widget, blur=8, dy=2, color=QColor(68, 138, 255, 77))


def search_rim_glow(widget: QWidget) -> QGraphicsDropShadowEffect:
    """Soft outer glow for focused search field rim light."""
    return apply_shadow(widget, blur=10, dy=0, color=QColor(68, 138, 255, 64))


def shadow_popup_window(widget: QWidget) -> None:
    """Apply popup shadow to a combo/menu popup top-level window."""
    window = widget.window()
    if window is not widget:
        popup_shadow(window)
