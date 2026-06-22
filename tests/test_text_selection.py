"""Tests for PDF text selection helpers and engine word extraction."""

from __future__ import annotations

from pathlib import Path

import fitz

from core.pdf_engine import PDFEngine
from core.text_selection import (
    selected_words,
    selected_words_anchor_focus,
    words_in_selection_rect,
)


def test_get_text_words_returns_bounding_boxes(tmp_path: Path) -> None:
    pdf_path = tmp_path / "words.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), "Hello World", fontsize=12)
    doc.save(pdf_path)
    doc.close()

    engine = PDFEngine()
    document = engine.open(pdf_path)
    try:
        words = engine.get_text_words(document, 0)
    finally:
        engine.close(document)

    assert words
    texts = [entry[1] for entry in words]
    joined = " ".join(texts)
    assert "Hello" in joined
    assert "World" in joined
    for rect, text, *_rest in words:
        x0, y0, x1, y1 = rect
        assert x1 > x0
        assert y1 > y0
        assert text.strip()


def test_words_in_selection_rect_joins_in_reading_order() -> None:
    words = [
        ((10.0, 10.0, 40.0, 20.0), "Alpha"),
        ((50.0, 10.0, 80.0, 20.0), "Beta"),
        ((10.0, 30.0, 50.0, 40.0), "Gamma"),
    ]
    selection = (0.0, 0.0, 100.0, 25.0)
    assert words_in_selection_rect(words, selection) == "Alpha Beta"
    assert (
        words_in_selection_rect(words, (0.0, 0.0, 100.0, 50.0)) == "Alpha Beta\nGamma"
    )


def test_selected_words_returns_highlight_rects() -> None:
    words = [
        ((10.0, 10.0, 30.0, 20.0), "One"),
        ((200.0, 200.0, 230.0, 210.0), "Far"),
    ]
    rects, text = selected_words(words, (0.0, 0.0, 50.0, 30.0))
    assert text == "One"
    assert len(rects) == 1
    assert rects[0] == words[0][0]


def test_two_column_selection_respects_horizontal_bounds() -> None:
    """A drag confined to one column must not select words in the other column."""
    words = [
        ((72.0, 100.0, 120.0, 112.0), "LeftOne"),
        ((130.0, 100.0, 180.0, 112.0), "LeftTwo"),
        ((350.0, 100.0, 400.0, 112.0), "RightOne"),
        ((410.0, 100.0, 460.0, 112.0), "RightTwo"),
    ]

    left_rects, left_text = selected_words(words, (70.0, 98.0, 200.0, 115.0))
    assert left_text == "LeftOne LeftTwo"
    assert len(left_rects) == 2
    assert all(rect[2] <= 200.0 for rect in left_rects)

    right_rects, right_text = selected_words(words, (340.0, 98.0, 470.0, 115.0))
    assert right_text == "RightOne RightTwo"
    assert len(right_rects) == 2
    assert all(rect[0] >= 340.0 for rect in right_rects)


def test_two_column_anchor_focus_respects_reading_order() -> None:
    """Anchor/focus selection in one column must not include the other column."""
    words = [
        ((72.0, 100.0, 120.0, 112.0), "LeftOne", 0, 0, 0),
        ((130.0, 100.0, 180.0, 112.0), "LeftTwo", 0, 0, 1),
        ((350.0, 100.0, 400.0, 112.0), "RightOne", 1, 0, 0),
        ((410.0, 100.0, 460.0, 112.0), "RightTwo", 1, 0, 1),
    ]

    rects, text = selected_words_anchor_focus(words, (90.0, 106.0), (150.0, 106.0))
    assert text == "LeftOne LeftTwo"
    assert len(rects) == 2
    assert all(rect[2] <= 200.0 for rect in rects)

    rects, text = selected_words_anchor_focus(words, (370.0, 106.0), (430.0, 106.0))
    assert text == "RightOne RightTwo"
    assert len(rects) == 2
    assert all(rect[0] >= 340.0 for rect in rects)


def test_two_column_anchor_focus_filters_interleaved_ocr_blocks() -> None:
    """Interleaved OCR block indices must not pull in the other column."""
    words = [
        ((72.0, 100.0, 120.0, 112.0), "LeftA", 0, 0, 0),
        ((72.0, 120.0, 120.0, 132.0), "LeftB", 1, 0, 0),
        ((350.0, 50.0, 420.0, 62.0), "RightHeader", 2, 0, 0),
        ((72.0, 140.0, 120.0, 152.0), "LeftC", 3, 0, 0),
        ((350.0, 100.0, 420.0, 112.0), "RightBody", 4, 0, 0),
        ((350.0, 120.0, 420.0, 132.0), "RightTail", 5, 0, 0),
    ]

    rects, text = selected_words_anchor_focus(words, (90.0, 106.0), (90.0, 146.0))
    assert text == "LeftA\nLeftB\nLeftC"
    assert len(rects) == 3
    assert all(rect[2] < 300.0 for rect in rects)
    assert "RightHeader" not in text
    assert "RightBody" not in text

    cross_rects, cross_text = selected_words_anchor_focus(
        words, (90.0, 106.0), (380.0, 106.0)
    )
    assert "LeftA" in cross_text
    assert "RightBody" in cross_text
    assert len(cross_rects) == 5


def test_detect_column_layout_single_column_returns_none() -> None:
    from core.text_selection import detect_column_layout

    words = [
        ((72.0, 100.0, 120.0, 112.0), "One", 0, 0, 0),
        ((130.0, 100.0, 180.0, 112.0), "Two", 0, 0, 1),
        ((72.0, 120.0, 120.0, 132.0), "Three", 1, 0, 0),
    ]
    assert detect_column_layout(words) is None


def test_detect_column_layout_finds_two_columns() -> None:
    from core.text_selection import detect_column_layout

    words = [
        ((72.0, 100.0, 120.0, 112.0), "Left", 0, 0, 0),
        ((350.0, 100.0, 400.0, 112.0), "Right", 1, 0, 0),
        ((72.0, 120.0, 120.0, 132.0), "Left2", 2, 0, 0),
        ((350.0, 120.0, 400.0, 132.0), "Right2", 3, 0, 0),
        ((80.0, 140.0, 130.0, 152.0), "Left3", 4, 0, 0),
        ((360.0, 140.0, 410.0, 152.0), "Right3", 5, 0, 0),
    ]
    layout = detect_column_layout(words, page_width=595.0)
    assert layout is not None
    assert 150.0 < layout.divider_x < 300.0


def test_ocr_cv_anchor_focus_stays_in_left_column() -> None:
    """Regression test for the two-column OCR CV layout."""
    import pytest

    pdf_path = (
        Path(__file__).resolve().parents[1]
        / "temp"
        / "CV Bassi Mattia 2026_ocr_2c631891.pdf"
    )
    if not pdf_path.is_file():
        pytest.skip("OCR CV fixture not available")

    engine = PDFEngine()
    document = engine.open(pdf_path)
    try:
        words = engine.get_text_words(document, 0)
        assert words
        assert len(words[0]) == 5

        anchor = (50.0, 150.0)
        focus = (100.0, 160.0)
        rects, text = selected_words_anchor_focus(words, anchor, focus)
        assert text
        assert all(rect[2] < 220.0 for rect in rects)
    finally:
        engine.close(document)


def test_widget_drag_rect_clamped_to_pixmap_avoids_full_page_span() -> None:
    from ui.page_geometry import PageDisplayMetrics, widget_drag_rect_to_pdf

    page_w, page_h = 595.0, 842.0
    pix_w, pix_h = 595, 842
    metrics = PageDisplayMetrics(page_w, page_h, pix_w, pix_h)
    origin_x, origin_y = 100.0, 0.0

    words = [
        ((72.0, 98.0, 120.0, 115.0), "Left"),
        ((350.0, 98.0, 400.0, 115.0), "Right"),
    ]

    selection = widget_drag_rect_to_pdf(
        origin_x + 72,
        100,
        origin_x + 200,
        120,
        metrics,
        origin_x,
        origin_y,
        pix_w,
        pix_h,
    )
    _rects, text = selected_words(words, selection)
    assert text == "Left"

    # Drag starting in label margin must clamp to pixmap edge, not widen into both columns.
    clamped = widget_drag_rect_to_pdf(
        10,
        100,
        origin_x + 200,
        120,
        metrics,
        origin_x,
        origin_y,
        pix_w,
        pix_h,
    )
    assert clamped[0] >= 0.0
    _rects, text = selected_words(words, clamped)
    assert "Right" not in text


def test_page_geometry_roundtrip_at_multiple_zoom_dpi() -> None:
    from ui.page_geometry import (
        PageDisplayMetrics,
        pdf_rect_to_widget,
        widget_point_to_pdf,
    )

    for dpi in (150, 225, 300):
        page_w = 595.0
        page_h = 842.0
        pix_w = int(round(page_w * dpi / 72.0))
        pix_h = int(round(page_h * dpi / 72.0))
        metrics = PageDisplayMetrics(page_w, page_h, pix_w, pix_h)

        for px, py in ((10.0, 20.0), (pix_w / 2, pix_h / 2), (pix_w - 5, pix_h - 5)):
            pdf_x, pdf_y = widget_point_to_pdf(px, py, metrics, 0.0, 0.0)
            back_x, back_y, _, _ = pdf_rect_to_widget(
                (pdf_x, pdf_y, pdf_x, pdf_y), metrics, 0.0, 0.0
            )
            assert abs(back_x - px) < 0.01
            assert abs(back_y - py) < 0.01

        word = (72.0, 100.0, 120.0, 112.0)
        wx0, wy0, wx1, wy1 = pdf_rect_to_widget(word, metrics, 4.0, 8.0)
        assert wx0 >= 4.0
        assert wy0 >= 8.0
        assert wx1 > wx0
        assert wy1 > wy0
        roundtrip = widget_point_to_pdf(wx0, wy0, metrics, 4.0, 8.0)
        assert abs(roundtrip[0] - word[0]) < 0.05
        assert abs(roundtrip[1] - word[1]) < 0.05
