"""Pure helpers for PDF text selection by bounding box."""

from __future__ import annotations

from dataclasses import dataclass

Rect = tuple[float, float, float, float]
WordEntry = tuple[Rect, str] | tuple[Rect, str, int, int, int]
Point = tuple[float, float]

NEAREST_WORD_MAX_DIST_PT = 30.0
MIN_WORDS_PER_COLUMN = 3
MIN_COLUMN_GAP_PT = 20.0
MIN_COLUMN_GAP_PAGE_RATIO = 0.035


@dataclass(frozen=True)
class ColumnLayout:
    """Detected multi-column layout for a page."""

    divider_x: float
    page_width: float


def _word_parts(word: WordEntry) -> tuple[Rect, str, int, int, int]:
    """Normalize a word entry to rect, text, and reading-order indices."""
    rect, text = word[0], word[1]
    if len(word) >= 5:
        block, line, word_no = int(word[2]), int(word[3]), int(word[4])
    else:
        block = line = word_no = 0
    return rect, text, block, line, word_no


def normalize_rect(x0: float, y0: float, x1: float, y1: float) -> Rect:
    """Return a rectangle with non-negative width and height."""
    return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def point_in_rect(px: float, py: float, rect: Rect) -> bool:
    """Return True when a point lies inside a rectangle."""
    x0, y0, x1, y1 = rect
    return x0 <= px <= x1 and y0 <= py <= y1


def rects_intersect(first: Rect, second: Rect) -> bool:
    """Return True when two axis-aligned rectangles overlap."""
    ax0, ay0, ax1, ay1 = first
    bx0, by0, bx1, by1 = second
    return ax0 < bx1 and ax1 > bx0 and ay0 < by1 and ay1 > by0


def _word_center_x(word: WordEntry) -> float:
    rect, *_rest = _word_parts(word)
    return (rect[0] + rect[2]) / 2.0


def detect_column_layout(words: list[WordEntry], *, page_width: float | None = None) -> ColumnLayout | None:
    """Detect a two-column layout from word X positions, or return None for single-column."""
    centers: list[float] = []
    max_x = 0.0
    for word in words:
        rect, text, *_rest = _word_parts(word)
        if not text.strip():
            continue
        centers.append(_word_center_x(word))
        max_x = max(max_x, rect[2])

    if len(centers) < MIN_WORDS_PER_COLUMN * 2:
        return None

    page_w = page_width if page_width is not None else max_x
    if page_w <= 0:
        return None

    sorted_centers = sorted(centers)
    max_gap = 0.0
    split_index = -1
    for index in range(len(sorted_centers) - 1):
        gap = sorted_centers[index + 1] - sorted_centers[index]
        if gap > max_gap:
            max_gap = gap
            split_index = index

    min_gap = max(MIN_COLUMN_GAP_PT, page_w * MIN_COLUMN_GAP_PAGE_RATIO)
    if split_index < 0 or max_gap < min_gap:
        return None

    divider_x = (sorted_centers[split_index] + sorted_centers[split_index + 1]) / 2.0
    left_count = sum(1 for center in centers if center < divider_x)
    right_count = len(centers) - left_count
    if left_count < MIN_WORDS_PER_COLUMN or right_count < MIN_WORDS_PER_COLUMN:
        return None

    return ColumnLayout(divider_x=divider_x, page_width=page_w)


def _word_column(word: WordEntry, layout: ColumnLayout | None) -> str | None:
    """Return ``left``/``right`` for a word, or None when layout is unknown."""
    if layout is None:
        return None
    return "left" if _word_center_x(word) < layout.divider_x else "right"


def _reading_order_key(word: WordEntry) -> tuple[int, int, int, float, float]:
    rect, _text, block, line, word_no = _word_parts(word)
    return block, line, word_no, rect[1], rect[0]


def word_at_point(words: list[WordEntry], px: float, py: float) -> int | None:
    """Return the index of the word under ``(px, py)`` in PDF points."""
    containing: list[tuple[float, int]] = []
    for index, word in enumerate(words):
        rect, text, *_rest = _word_parts(word)
        if not text.strip():
            continue
        if point_in_rect(px, py, rect):
            area = max(1.0, (rect[2] - rect[0]) * (rect[3] - rect[1]))
            containing.append((area, index))

    if containing:
        containing.sort(key=lambda item: item[0])
        return containing[0][1]

    best_index: int | None = None
    best_distance = float("inf")
    max_distance_sq = NEAREST_WORD_MAX_DIST_PT * NEAREST_WORD_MAX_DIST_PT
    for index, word in enumerate(words):
        rect, text, *_rest = _word_parts(word)
        if not text.strip():
            continue
        center_x = (rect[0] + rect[2]) / 2.0
        center_y = (rect[1] + rect[3]) / 2.0
        distance_sq = (center_x - px) ** 2 + (center_y - py) ** 2
        if distance_sq < best_distance:
            best_distance = distance_sq
            best_index = index

    if best_index is None or best_distance > max_distance_sq:
        return None
    return best_index


def _join_selected_words(selected: list[WordEntry]) -> tuple[list[Rect], str]:
    if not selected:
        return [], ""

    lines: list[list[str]] = []
    rects_out: list[Rect] = []
    line_y: float | None = None
    line_words: list[str] = []
    y_tolerance = 5.0

    for word in selected:
        rect, text, *_rest = _word_parts(word)
        cleaned = text.strip()
        if not cleaned:
            continue
        rects_out.append(rect)
        y0 = rect[1]
        if line_y is None or abs(y0 - line_y) > y_tolerance:
            if line_words:
                lines.append(line_words)
            line_words = [cleaned]
            line_y = y0
        else:
            line_words.append(cleaned)

    if line_words:
        lines.append(line_words)

    return rects_out, "\n".join(" ".join(parts) for parts in lines)


def selected_words_anchor_focus(
    words: list[WordEntry],
    anchor: Point,
    focus: Point,
) -> tuple[list[Rect], str]:
    """Select words from anchor to focus in PDF reading order."""
    anchor_index = word_at_point(words, anchor[0], anchor[1])
    focus_index = word_at_point(words, focus[0], focus[1])
    if anchor_index is None and focus_index is None:
        return [], ""
    if anchor_index is None:
        anchor_index = focus_index
    if focus_index is None:
        focus_index = anchor_index

    ordered = sorted(range(len(words)), key=lambda index: _reading_order_key(words[index]))
    position = {index: pos for pos, index in enumerate(ordered)}
    start = min(position[anchor_index], position[focus_index])
    end = max(position[anchor_index], position[focus_index])
    selected = [words[ordered[pos]] for pos in range(start, end + 1)]

    layout = detect_column_layout(words)
    anchor_column = _word_column(words[anchor_index], layout)
    focus_column = _word_column(words[focus_index], layout)
    if layout is not None and anchor_column is not None and anchor_column == focus_column:
        selected = [word for word in selected if _word_column(word, layout) == anchor_column]

    return _join_selected_words(selected)


def words_in_selection_rect(words: list[WordEntry], selection: Rect) -> str:
    """Join words whose boxes intersect ``selection``, in reading order."""
    _rects, text = selected_words(words, selection)
    return text


def selected_words(words: list[WordEntry], selection: Rect) -> tuple[list[Rect], str]:
    """Return word rectangles and joined text for a selection rectangle."""
    sel = normalize_rect(*selection)
    hits: list[WordEntry] = []
    for word in words:
        rect, text, *_rest = _word_parts(word)
        if not text.strip():
            continue
        if rects_intersect(rect, sel):
            hits.append(word)

    if not hits:
        return [], ""

    hits.sort(key=_reading_order_key)
    return _join_selected_words(hits)
