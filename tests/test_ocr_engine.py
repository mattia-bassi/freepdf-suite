"""Tests for local OCR engine (mocked — no Tesseract required in CI)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core import ocr_engine


def test_check_tesseract_available_returns_bool_without_crashing() -> None:
    result = ocr_engine.check_tesseract_available()
    assert isinstance(result, bool)


def test_bundled_tesseract_path_when_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tesseract_dir = tmp_path / "tesseract"
    tesseract_dir.mkdir()
    exe_name = "tesseract.exe" if sys.platform == "win32" else "tesseract"
    exe_path = tesseract_dir / exe_name
    exe_path.write_bytes(b"stub")
    monkeypatch.setattr(ocr_engine, "_app_root", lambda: tmp_path)
    assert ocr_engine.bundled_tesseract_path() == exe_path


def test_bundled_tesseract_path_missing_when_exe_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "tesseract").mkdir()
    monkeypatch.setattr(ocr_engine, "_app_root", lambda: tmp_path)
    assert ocr_engine.bundled_tesseract_path() is None


def test_configure_tesseract_uses_bundled_binary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ocr_engine._reset_tesseract_cache()
    tesseract_dir = tmp_path / "tesseract"
    tessdata_dir = tesseract_dir / "tessdata"
    tessdata_dir.mkdir(parents=True)
    exe_name = "tesseract.exe" if sys.platform == "win32" else "tesseract"
    exe_path = tesseract_dir / exe_name
    exe_path.write_bytes(b"stub")

    inner = MagicMock()
    mock_pt = MagicMock()
    mock_pt.pytesseract = inner
    mock_pt.get_tesseract_version.return_value = "5.0"
    monkeypatch.setattr(ocr_engine, "pytesseract", mock_pt)
    monkeypatch.setattr(ocr_engine, "_app_root", lambda: tmp_path)

    assert ocr_engine.check_tesseract_available() is True
    assert inner.tesseract_cmd == str(exe_path)


def test_configure_tesseract_falls_back_to_system_path(monkeypatch: pytest.MonkeyPatch) -> None:
    ocr_engine._reset_tesseract_cache()
    monkeypatch.setattr(ocr_engine, "bundled_tesseract_path", lambda: None)

    inner = MagicMock()
    mock_pt = MagicMock()
    mock_pt.pytesseract = inner
    mock_pt.get_tesseract_version.return_value = "5.0"
    monkeypatch.setattr(ocr_engine, "pytesseract", mock_pt)

    assert ocr_engine.check_tesseract_available() is True
    assert inner.tesseract_cmd == "tesseract"


def test_configure_tesseract_tries_system_when_bundled_probe_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ocr_engine._reset_tesseract_cache()
    tesseract_dir = tmp_path / "tesseract"
    tesseract_dir.mkdir()
    exe_name = "tesseract.exe" if sys.platform == "win32" else "tesseract"
    (tesseract_dir / exe_name).write_bytes(b"stub")

    inner = MagicMock()
    mock_pt = MagicMock()
    mock_pt.pytesseract = inner
    mock_pt.get_tesseract_version.side_effect = [RuntimeError("bad bundled"), "5.0"]
    monkeypatch.setattr(ocr_engine, "pytesseract", mock_pt)
    monkeypatch.setattr(ocr_engine, "_app_root", lambda: tmp_path)

    assert ocr_engine.check_tesseract_available() is True
    assert inner.tesseract_cmd == "tesseract"
    assert mock_pt.get_tesseract_version.call_count == 2


def test_get_ocr_language_choices_excludes_osd_and_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ocr_engine, "check_tesseract_available", lambda: True)
    monkeypatch.setattr(
        ocr_engine,
        "_raw_installed_language_codes",
        lambda: ["eng", "ita", "osd", "cat"],
    )
    choices = ocr_engine.get_ocr_language_choices()
    codes = [code for code, _label in choices]
    labels = dict(choices)
    assert "osd" not in codes
    assert "cat" not in codes
    assert codes == ["eng", "ita"]
    assert labels["eng"] == "English"
    assert labels["ita"] == "Italiano"


def test_default_ocr_language_is_ita_plus_eng() -> None:
    assert ocr_engine.DEFAULT_OCR_LANGUAGE == "ita+eng"


def test_default_ocr_dpi_matches_render_pipeline() -> None:
    assert ocr_engine.DEFAULT_OCR_DPI == 150


def test_create_temp_ocr_output_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ocr_engine, "ocr_temp_dir", lambda: tmp_path)
    txt_path = ocr_engine.create_temp_ocr_output_path(Path("report.pdf"), "txt")
    pdf_path = ocr_engine.create_temp_ocr_output_path(Path("report.pdf"), "searchable_pdf")
    assert txt_path.parent == tmp_path
    assert txt_path.suffix == ".txt"
    assert txt_path.name.startswith("report_ocr_")
    assert pdf_path.suffix == ".pdf"


def _mock_pixmap() -> MagicMock:
    pixmap = MagicMock()
    pixmap.width = 10
    pixmap.height = 10
    pixmap.samples = b"\xff" * 300
    return pixmap


def _mock_document(page_count: int = 2) -> MagicMock:
    page = MagicMock()
    page.get_pixmap.return_value = _mock_pixmap()
    doc = MagicMock()
    doc.page_count = page_count
    doc.load_page.return_value = page
    return doc


def _patch_tesseract_and_image(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_tesseract = MagicMock()
    mock_tesseract.image_to_string.return_value = "page text"
    mock_tesseract.image_to_data.return_value = {
        "text": ["Hello"],
        "left": [10],
        "top": [10],
        "width": [50],
        "height": [12],
        "conf": ["95"],
    }
    monkeypatch.setattr(ocr_engine, "pytesseract", mock_tesseract)

    mock_image = MagicMock()
    mock_image.width = 10
    mock_image.height = 10
    mock_image_module = MagicMock()
    mock_image_module.frombytes.return_value = mock_image
    monkeypatch.setattr(ocr_engine, "Image", mock_image_module)


def test_run_ocr_on_pdf_txt_with_mocks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 mock")
    output_path = tmp_path / "sample_ocr.txt"
    doc = _mock_document(page_count=2)

    monkeypatch.setattr(ocr_engine, "check_tesseract_available", lambda: True)
    monkeypatch.setattr(ocr_engine, "fitz", MagicMock())
    monkeypatch.setattr(ocr_engine.fitz, "open", lambda *args, **kwargs: doc)
    _patch_tesseract_and_image(monkeypatch)

    progress: list[tuple[int, int]] = []

    ocr_engine.run_ocr_on_pdf(
        pdf_path,
        output_path,
        "txt",
        progress_callback=lambda current, total: progress.append((current, total)),
    )

    assert output_path.is_file()
    text = output_path.read_text(encoding="utf-8")
    assert "page text" in text
    assert progress == [(1, 2), (2, 2)]
    doc.close.assert_called_once()
    ocr_engine.pytesseract.image_to_string.assert_called()


def test_run_ocr_on_pdf_searchable_pdf_with_mocks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 mock")
    output_path = tmp_path / "sample_ocr.pdf"

    page_rect = MagicMock()
    page_rect.width = 100.0
    page_rect.height = 120.0

    source_page = MagicMock()
    source_page.rect = page_rect
    source_page.get_pixmap.return_value = _mock_pixmap()

    source_doc = MagicMock()
    source_doc.page_count = 1
    source_doc.load_page.return_value = source_page

    new_page = MagicMock()
    new_page.rect = page_rect
    output_doc = MagicMock()
    output_doc.new_page.return_value = new_page

    def fitz_open(*args, **kwargs):
        if not args and "stream" not in kwargs:
            return output_doc
        return source_doc

    monkeypatch.setattr(ocr_engine, "check_tesseract_available", lambda: True)
    monkeypatch.setattr(ocr_engine, "fitz", MagicMock())
    monkeypatch.setattr(ocr_engine.fitz, "open", fitz_open)
    _patch_tesseract_and_image(monkeypatch)

    ocr_engine.run_ocr_on_pdf(
        pdf_path,
        output_path,
        "searchable_pdf",
        "ita",
        150,
    )

    output_doc.new_page.assert_called_once()
    new_page.insert_image.assert_called_once()
    new_page.insert_text.assert_called()
    output_doc.save.assert_called_once_with(str(output_path))
    output_doc.close.assert_called_once()
    source_doc.close.assert_called_once()
    source_page.get_pixmap.assert_called_once_with(dpi=150, alpha=False)
    ocr_engine.pytesseract.image_to_data.assert_called()
