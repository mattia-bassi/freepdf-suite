"""Tests for format detection and P7M extraction."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.errors import P7MExtractionError, PDFAConversionError
from core.format_handler import FormatHandler
from core.models import DocumentFormat


def test_detect_format_pdf(tmp_path: Path) -> None:
    pdf = tmp_path / "sample.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")
    handler = FormatHandler()
    assert handler.detect_format(pdf) == DocumentFormat.PDF


def test_detect_format_p7m_by_extension(tmp_path: Path) -> None:
    p7m = tmp_path / "signed.p7m"
    p7m.write_bytes(b"not a real envelope")
    handler = FormatHandler()
    assert handler.detect_format(p7m) == DocumentFormat.P7M


def test_extract_p7m_embedded_pdf_bytes(tmp_path: Path) -> None:
    payload = b"prefix %PDF-1.4\nhello\n%%EOF\n suffix"
    p7m = tmp_path / "wrapped.p7m"
    p7m.write_bytes(payload)
    extracted = FormatHandler().extract_p7m(p7m)
    assert extracted.startswith(b"%PDF-")
    assert extracted.endswith(b"%%EOF")


def test_extract_p7m_missing_pdf_raises(tmp_path: Path) -> None:
    p7m = tmp_path / "empty.p7m"
    p7m.write_bytes(b"no pdf here")
    with pytest.raises(P7MExtractionError):
        FormatHandler().extract_p7m(p7m)


def test_to_pdfa_not_implemented(tmp_path: Path) -> None:
    src = tmp_path / "in.pdf"
    dst = tmp_path / "out.pdf"
    src.write_bytes(b"%PDF-1.4\n")
    with pytest.raises(PDFAConversionError):
        FormatHandler().to_pdfa(src, dst)


def test_detect_unknown_extension(tmp_path: Path) -> None:
    txt = tmp_path / "notes.txt"
    txt.write_text("hello", encoding="utf-8")
    assert FormatHandler().detect_format(txt) == DocumentFormat.UNKNOWN
