"""Application entry point for the FreePDF Suite Qt6 shell."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from .bootstrap import configure_application, init_language, init_windows_app_id
from .main_window import MainWindow
from .splash_screen import BrandedSplashScreen


def run(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv)
    init_windows_app_id()
    app = QApplication(args)
    app.setApplicationName("FreePDF Suite")
    init_language()
    configure_application(app)

    splash = BrandedSplashScreen.show_while_loading(app)

    initial: Path | None = None
    if len(args) > 1:
        candidate = Path(args[1])
        if candidate.is_file():
            initial = candidate

    window = MainWindow(initial_path=initial)
    window.show()
    splash.finish(window)
    return app.exec()


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
