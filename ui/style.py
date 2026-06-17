"""Centralized Qt style sheet so states stay consistent across the shell."""

from __future__ import annotations

# Category -> accent color, keyed by the closed enum from contract Section 6.5.
CATEGORY_COLORS: dict[str, str] = {
    "view": "#2d7ff9",
    "organize": "#7c5cff",
    "optimize": "#16a34a",
    "convert": "#f59e0b",
    "enhance": "#06b6d4",
    "edit": "#ec4899",
    "security": "#ef4444",
    "extract": "#0ea5e9",
}

APP_STYLESHEET = """
QMainWindow { background: #1e1e1e; }
QMenuBar { background: #252526; color: #d4d4d4; }
QMenuBar::item:selected { background: #094771; }
QMenu { background: #252526; color: #d4d4d4; border: 1px solid #3c3c3c; }
QMenu::item:selected { background: #094771; }
QStatusBar { background: #007acc; color: #ffffff; }
QLabel#viewerPlaceholder { color: #808080; font-size: 14px; }
QScrollArea { background: #2d2d2d; border: none; }
"""
