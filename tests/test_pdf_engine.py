"""Tests for the PDF engine."""

from __future__ import annotations

from pathlib import Path

import core
from core import errors
from core.pdf_engine import PDFEngine


def test_core_exports_and_version() -> None:
    assert core.__version__ == "0.1.0"
    assert PDFEngine.DEFAULT_DPI == 150
    assert core.FormatHandler is not None


def test_error_hierarchy_codes() -> None:
    assert issubclass(errors.DocumentOpenError, errors.FreePDFError)
    assert errors.EncryptedDocumentError.error_code == "ENCRYPTED_DOCUMENT_ERROR"
    assert errors.P7MExtractionError.error_code == "P7M_EXTRACTION_ERROR"


def test_engine_open_missing_file(tmp_path: Path) -> None:
    engine = PDFEngine()
    missing = tmp_path / "missing.pdf"
    try:
        engine.open(missing)
        raised = False
    except errors.DocumentOpenError:
        raised = True
    assert raised
