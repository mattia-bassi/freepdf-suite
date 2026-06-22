# FreePDF Suite — AI Coding Context

## Project Overview
FreePDF Suite is a free, open-source PDF reader and editor
for Windows, built as an alternative to Adobe Acrobat Pro.
Built with Python 3.12, PySide6 (Qt6), PyMuPDF.

## Architecture
- core/ — PDF engine, OCR, page manager, text selection, format handler
- ui/ — PySide6 interface (MainWindow, NavTabBar, PdfReaderWidget,
  ThumbnailPanel, OCR dialog, Page Manager dialogs)
- config/ — defaults.json (app settings)
- assets/ — logo.png, logo.ico
- tests/ — pytest test suite (55 tests)
- scripts/ — PyInstaller build script

## Coding Conventions
- Python 3.12+, PySide6 (Qt6), PyMuPDF (fitz)
- Black formatter, PEP8, max 100 chars per line
- Type hints required on all public functions in core/
- Google Style docstrings on all public functions in core/
- snake_case for functions/variables, PascalCase for classes
- UPPER_SNAKE_CASE for constants
- No print() in production code — use Python logging module
- All user-facing strings use tr() from ui/i18n.py
- Tests: pytest, 55 tests currently passing

## Key Files
- ui/bootstrap.py — app entry point, applies qt-material theme
- ui/main_window.py — MainWindow, menu wiring
- ui/toolbar_widgets.py — TopNavBar, ReaderStrip
- ui/style.py — QSS styles and color constants
- ui/i18n.py — all user-facing strings, 6 languages
- core/pdf_engine.py — PDF rendering and manipulation
- core/ocr_engine.py — Tesseract OCR integration
- core/page_manager.py — page reorder/delete/rotate/split/merge
- core/text_selection.py — mouse text selection logic
- config/defaults.json — default app configuration

## Current Status
Version: v0.4.0
Features: PDF/P7M reader, OCR, Page Manager, text selection/copy
