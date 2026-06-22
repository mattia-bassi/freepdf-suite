"""Tests for multi-document tab management."""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest
from PySide6.QtWidgets import QApplication

from core.pdf_engine import PDFEngine
from ui.document_manager import DocumentManager
from ui.pdf_reader import PdfReaderWidget


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    return application


def _make_pdf(path: Path, pages: int = 2) -> None:
    document = fitz.open()
    for index in range(pages):
        page = document.new_page()
        page.insert_text((72, 72), f"Page-{index + 1}")
    document.save(path)
    document.close()


def _open_manager(
    tmp_path: Path,
    engine: PDFEngine | None = None,
) -> tuple[DocumentManager, PDFEngine]:
    pdf_engine = engine or PDFEngine()
    manager = DocumentManager(pdf_engine, {"zoom_default": 1.0, "render_dpi": 96})
    manager.set_reader_factory(lambda: PdfReaderWidget({"zoom_default": 1.0}))
    return manager, pdf_engine


def test_open_document_creates_new_tab(tmp_path: Path, qapp: QApplication) -> None:
    pdf_path = tmp_path / "one.pdf"
    _make_pdf(pdf_path)
    manager, engine = _open_manager(tmp_path)

    document = engine.open(pdf_path)
    index = manager.open_document(document, pdf_path)

    assert index == 0
    assert manager.tab_count() == 1
    assert manager.get_active() is not None
    assert manager.get_active().file_path == pdf_path
    engine.close(document)


def test_open_document_same_path_switches_without_duplicate(
    tmp_path: Path, qapp: QApplication
) -> None:
    first = tmp_path / "a.pdf"
    second = tmp_path / "b.pdf"
    _make_pdf(first)
    _make_pdf(second)
    manager, engine = _open_manager(tmp_path)

    doc_a = engine.open(first)
    manager.open_document(doc_a, first)
    doc_b = engine.open(second)
    manager.open_document(doc_b, second)
    assert manager.tab_count() == 2

    doc_a_again = engine.open(first)
    index = manager.open_document(doc_a_again, first)

    assert index == 0
    assert manager.tab_count() == 2
    assert manager.active_index == 0


def test_close_document_removes_tab(tmp_path: Path, qapp: QApplication) -> None:
    pdf_path = tmp_path / "close.pdf"
    _make_pdf(pdf_path)
    manager, engine = _open_manager(tmp_path)
    manager.set_confirm_close_handler(lambda _state: "discard")

    document = engine.open(pdf_path)
    manager.open_document(document, pdf_path)
    assert manager.close_document(0)

    assert manager.tab_count() == 0
    assert manager.get_active() is None


def test_switch_to_restores_page_and_zoom(tmp_path: Path, qapp: QApplication) -> None:
    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    _make_pdf(first)
    _make_pdf(second)
    manager, engine = _open_manager(tmp_path)

    doc_first = engine.open(first)
    manager.open_document(doc_first, first)
    first_state = manager.get_active()
    assert first_state is not None
    first_state.reader.go_to_page(1)
    first_state.reader.set_zoom(1.5)
    first_state.capture_viewer_state()

    doc_second = engine.open(second)
    manager.open_document(doc_second, second)
    second_state = manager.get_active()
    assert second_state is not None
    second_state.reader.set_zoom(0.75)

    manager.switch_to(0)
    restored = manager.get_active()
    assert restored is first_state
    assert restored.reader.current_page == 1
    assert restored.reader.zoom == pytest.approx(1.5)

    engine.close(doc_first)
    engine.close(doc_second)


def test_replace_current_updates_active_tab_in_place(
    tmp_path: Path, qapp: QApplication
) -> None:
    original = tmp_path / "source.pdf"
    replacement = tmp_path / "CV_ocr_abcd12.pdf"
    _make_pdf(original)
    _make_pdf(replacement, pages=2)
    manager, engine = _open_manager(tmp_path)
    manager.set_confirm_close_handler(lambda _state: "discard")

    doc = engine.open(original)
    manager.open_document(doc, original)
    assert manager.tab_count() == 1

    replacement_doc = engine.open(replacement)
    index = manager.replace_current(replacement_doc, replacement, is_temp=True)

    assert index == 0
    assert manager.tab_count() == 1
    active = manager.get_active()
    assert active is not None
    assert active.file_path == replacement
    assert active.is_temp is True
    assert manager.tab_label(0).endswith("CV_ocr_abcd12.pdf")
    engine.close(replacement_doc)


def test_dirty_state_propagates_to_tab_label(
    tmp_path: Path, qapp: QApplication
) -> None:
    pdf_path = tmp_path / "dirty.pdf"
    _make_pdf(pdf_path, pages=3)
    manager, engine = _open_manager(tmp_path)

    document = engine.open(pdf_path)
    manager.open_document(document, pdf_path)
    state = manager.get_active()
    assert state is not None
    assert manager.tab_label(0) == "dirty.pdf"

    state.page_manager.move_page(state.document, 0, 2)
    manager.mark_dirty(0)

    assert state.page_manager.is_dirty
    assert manager.tab_label(0).startswith("● ")
    engine.close(document)
