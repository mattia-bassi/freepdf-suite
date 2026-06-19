#!/usr/bin/env python3
"""Build a portable Windows distribution with PyInstaller.

Output layout (onedir)::

    dist/FreePDFSuite/
        FreePDFSuite.exe
        _internal/     # bundled dependencies (do not edit)
        config/        # defaults + recent_files.json
        assets/        # logo and static resources
        tesseract/     # bundled OCR binary + tessdata (optional at build time)

Run from the repository root::

    poetry run python scripts/build.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENTRY = ROOT / "scripts" / "freepdf_entry.py"
DIST_DIR = ROOT / "dist"
APP_DIR = DIST_DIR / "FreePDFSuite"
WORK_DIR = ROOT / "build" / "pyinstaller"


def _require_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "PyInstaller is not installed. Run: poetry add --group dev pyinstaller"
        ) from exc


def _pyinstaller_cmd() -> list[str]:
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        "FreePDFSuite",
        f"--distpath={DIST_DIR}",
        f"--workpath={WORK_DIR}",
        f"--specpath={WORK_DIR}",
        f"--paths={ROOT}",
        "--hidden-import",
        "core",
        "--hidden-import",
        "core.pdf_engine",
        "--hidden-import",
        "core.format_handler",
        "--hidden-import",
        "core.errors",
        "--hidden-import",
        "core.models",
        "--hidden-import",
        "ui",
        "--hidden-import",
        "ui.app",
        "--hidden-import",
        "ui.main_window",
        "--hidden-import",
        "ui.pdf_reader",
        "--hidden-import",
        "core.ocr_engine",
        "--hidden-import",
        "pytesseract",
        "--collect-all",
        "PySide6",
        "--collect-all",
        "pymupdf",
    ]
    icon_path = ROOT / "assets" / "logo.ico"
    if icon_path.is_file():
        cmd.extend(["--icon", str(icon_path)])
    cmd.append(str(ENTRY))
    return cmd


def _copy_external_tree(name: str, *, required: bool = True) -> None:
    """Copy ``config/``, ``assets/``, or optional ``tesseract/`` next to the exe."""
    source = ROOT / name
    if not source.is_dir():
        if required:
            raise SystemExit(f"Missing required folder: {source}")
        print(f"Skipping {name}/ (not found — optional)")
        return
    target = APP_DIR / name
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    print(f"Copied {name}/ -> {target}")


def main() -> int:
    _require_pyinstaller()
    print("Building FreePDF Suite with PyInstaller…")
    subprocess.run(_pyinstaller_cmd(), cwd=ROOT, check=True)

    if not APP_DIR.is_dir():
        raise SystemExit(f"Expected output folder not found: {APP_DIR}")

    _copy_external_tree("config")
    _copy_external_tree("assets")
    _copy_external_tree("tesseract", required=False)

    print(f"\nBuild complete: {APP_DIR / 'FreePDFSuite.exe'}")
    print("Edit config/ beside the exe without rebuilding.")
    if not (APP_DIR / "tesseract").is_dir():
        print("Note: tesseract/ was not bundled — OCR will only work if Tesseract is on PATH.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
