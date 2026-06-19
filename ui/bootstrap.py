"""Runtime wiring helpers for the UI shell."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


def app_root() -> Path:
    """Repository root in dev; directory containing the .exe when frozen."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


REPO_ROOT: Path = app_root()
CONFIG_DIR: Path = REPO_ROOT / "config"
ASSETS_DIR: Path = REPO_ROOT / "assets"
LOGO_PATH: Path = ASSETS_DIR / "logo.png"
LOGO_ICO_PATH: Path = ASSETS_DIR / "logo.ico"


def init_windows_app_id() -> None:
    """Set AppUserModelID so Windows taskbar shows our icon instead of Python's."""
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FreePDFSuite.App.1.0")


def load_backend() -> dict[str, Any]:
    """Return the PDF engine class for the reader shell."""
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    try:
        from core.pdf_engine import PDFEngine

        return {"PDFEngine": PDFEngine}
    except Exception:  # pragma: no cover
        return {"PDFEngine": None}


def init_language() -> str:
    """Load the UI language from config before widgets are created."""
    from .i18n import init_language as _init_language

    return _init_language()


def configure_application(app: Any) -> None:
    """Apply qt-material theme plus app-specific navigation/search overrides."""
    from qt_material import apply_stylesheet

    from .style import APP_STYLESHEET

    extra = {
        "density_scale": "-2",
        "font_size": "13px",
        "primaryColor": "#1565C0",
        "primaryLightColor": "#448aff",
    }

    apply_stylesheet(app, theme="dark_blue.xml", extra=extra)
    app.setStyleSheet(app.styleSheet() + "\n" + APP_STYLESHEET)

    from PySide6.QtGui import QIcon

    if LOGO_ICO_PATH.is_file():
        app.setWindowIcon(QIcon(str(LOGO_ICO_PATH)))
    elif LOGO_PATH.is_file():
        app.setWindowIcon(QIcon(str(LOGO_PATH)))
