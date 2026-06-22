"""Tests for in-memory PDF page manipulation."""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from core.errors import PageIndexError
from core.page_manager import PageManager, parse_page_ranges, ranges_from_split_points
from core.pdf_engine import PDFEngine


def _make_pdf(path: Path, pages: int = 3) -> None:
    doc = fitz.open()
    for index in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page-{index + 1}")
    doc.save(path)
    doc.close()


def _open(engine: PDFEngine, path: Path):
    return engine.open(path)


def test_move_page_reorders_correctly(tmp_path: Path) -> None:
    pdf_path = tmp_path / "move.pdf"
    _make_pdf(pdf_path, pages=3)
    engine = PDFEngine()
    manager = PageManager(engine)
    document = _open(engine, pdf_path)
    try:
        manager.move_page(document, 0, 2)
        assert engine.extract_text(document, 0).strip() == "Page-2"
        assert engine.extract_text(document, 2).strip() == "Page-1"
        assert manager.is_dirty
    finally:
        engine.close(document)


def test_delete_page_removes_page_and_blocks_last_page(tmp_path: Path) -> None:
    pdf_path = tmp_path / "delete.pdf"
    _make_pdf(pdf_path, pages=3)
    engine = PDFEngine()
    manager = PageManager(engine)
    document = _open(engine, pdf_path)
    try:
        manager.delete_page(document, 1)
        assert document.page_count == 2
        assert engine.extract_text(document, 0).strip() == "Page-1"
        assert engine.extract_text(document, 1).strip() == "Page-3"
    finally:
        engine.close(document)

    single_path = tmp_path / "single.pdf"
    _make_pdf(single_path, pages=1)
    single = _open(engine, single_path)
    try:
        with pytest.raises(PageIndexError):
            manager.delete_page(single, 0)
    finally:
        engine.close(single)


def test_rotate_page_is_cumulative(tmp_path: Path) -> None:
    pdf_path = tmp_path / "rotate.pdf"
    _make_pdf(pdf_path, pages=1)
    engine = PDFEngine()
    manager = PageManager(engine)
    document = _open(engine, pdf_path)
    try:
        manager.rotate_page(document, 0, 90)
        assert engine.page_info(document, 0).rotation == 90
        manager.rotate_page(document, 0, 90)
        assert engine.page_info(document, 0).rotation == 180
    finally:
        engine.close(document)


def test_insert_pages_from_file_at_position(tmp_path: Path) -> None:
    target_path = tmp_path / "target.pdf"
    source_path = tmp_path / "source.pdf"
    _make_pdf(target_path, pages=2)
    _make_pdf(source_path, pages=2)

    engine = PDFEngine()
    manager = PageManager(engine)
    document = _open(engine, target_path)
    try:
        inserted = manager.insert_pages_from_file(document, 1, source_path)
        assert inserted == 2
        assert document.page_count == 4
        assert engine.extract_text(document, 0).strip() == "Page-1"
        assert engine.extract_text(document, 1).strip() == "Page-1"
        assert engine.extract_text(document, 2).strip() == "Page-2"
        assert engine.extract_text(document, 3).strip() == "Page-2"
    finally:
        engine.close(document)


def test_split_document_outputs_expected_files(tmp_path: Path) -> None:
    pdf_path = tmp_path / "split.pdf"
    _make_pdf(pdf_path, pages=6)
    output_dir = tmp_path / "parts"
    engine = PDFEngine()
    manager = PageManager(engine)
    document = _open(engine, pdf_path)
    try:
        outputs = manager.split_document(document, [(0, 2), (3, 5)], output_dir)
        assert len(outputs) == 2
        first = fitz.open(outputs[0])
        second = fitz.open(outputs[1])
        try:
            assert first.page_count == 3
            assert second.page_count == 3
        finally:
            first.close()
            second.close()
    finally:
        engine.close(document)


def test_merge_documents_combines_pages_in_order(tmp_path: Path) -> None:
    first_path = tmp_path / "a.pdf"
    second_path = tmp_path / "b.pdf"
    _make_pdf(first_path, pages=2)
    _make_pdf(second_path, pages=1)
    output_path = tmp_path / "merged.pdf"

    engine = PDFEngine()
    manager = PageManager(engine)
    manager.merge_documents([first_path, second_path], output_path)

    merged = fitz.open(output_path)
    try:
        assert merged.page_count == 3
        assert merged[0].get_text("text").strip() == "Page-1"
        assert merged[1].get_text("text").strip() == "Page-2"
        assert merged[2].get_text("text").strip() == "Page-1"
    finally:
        merged.close()


def test_parse_page_ranges_accepts_user_input() -> None:
    assert parse_page_ranges("1-3, 7", 10) == [(0, 2), (6, 6)]


def test_ranges_from_split_points_builds_expected_ranges() -> None:
    assert ranges_from_split_points(7, [2, 5]) == [(0, 2), (3, 5), (6, 6)]
    assert ranges_from_split_points(1, []) == [(0, 0)]
    assert ranges_from_split_points(3, [0]) == [(0, 0), (1, 2)]
