"""In-memory PDF page manipulation with dirty-state tracking."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import fitz

from .errors import DocumentOpenError, DocumentSaveError, PageIndexError
from .models import Document

if TYPE_CHECKING:
    from .pdf_engine import PDFEngine


class PageManager:
    """Coordinate page-level edits on an open ``Document``."""

    def __init__(self, engine: PDFEngine) -> None:
        self._engine = engine
        self._dirty = False

    @property
    def is_dirty(self) -> bool:
        """Return True when page operations changed the open document."""
        return self._dirty

    def reset_dirty(self) -> None:
        """Clear the modified flag after save or fresh open."""
        self._dirty = False

    def move_page(self, doc: Document, from_index: int, to_index: int) -> None:
        """Reorder a page from ``from_index`` to ``to_index`` (0-based)."""
        count = self._engine.page_count(doc)
        if from_index < 0 or from_index >= count or to_index < 0 or to_index >= count:
            raise PageIndexError(f"Invalid page move ({from_index} -> {to_index}) for {count} pages.")
        if from_index == to_index:
            return
        order = list(range(count))
        page = order.pop(from_index)
        order.insert(to_index, page)
        self._engine.reorder_pages(doc, order)
        self._sync_page_count(doc)
        self._mark_dirty()

    def delete_page(self, doc: Document, index: int) -> None:
        """Remove one page; refuses to delete the last remaining page."""
        count = self._engine.page_count(doc)
        if index < 0 or index >= count:
            raise PageIndexError(f"Page index out of range: {index}")
        if count <= 1:
            raise PageIndexError("Cannot delete the only remaining page.")
        self._engine.delete_pages(doc, [index])
        self._sync_page_count(doc)
        self._mark_dirty()

    def rotate_page(self, doc: Document, index: int, degrees: int) -> None:
        """Rotate a page cumulatively by 90, 180, or 270 degrees."""
        if degrees not in (90, 180, 270, -90, -180, -270):
            raise PageIndexError("Rotation step must be ±90, 180, or 270 degrees.")
        current = self._engine.page_info(doc, index).rotation
        new_rotation = (current + degrees) % 360
        self._engine.rotate_page(doc, index, new_rotation)
        self._mark_dirty()

    def insert_pages_from_file(
        self,
        doc: Document,
        at_index: int,
        source_path: str | Path,
        page_range: tuple[int, int] | None = None,
    ) -> int:
        """Insert pages from another PDF at ``at_index``; returns inserted page count."""
        path = Path(source_path)
        if not path.is_file():
            raise DocumentOpenError(f"File not found: {path}")

        count = self._engine.page_count(doc)
        if at_index < 0 or at_index > count:
            raise PageIndexError(f"Insert index out of range: {at_index}")

        src = fitz.open(path)  # type: ignore[union-attr]
        try:
            if src.page_count == 0:
                raise DocumentOpenError(f"No pages in source file: {path}")
            if page_range is None:
                from_page, to_page = 0, src.page_count - 1
            else:
                from_page, to_page = page_range
                if from_page < 0 or to_page >= src.page_count or from_page > to_page:
                    raise PageIndexError(
                        f"Invalid source page range ({from_page}, {to_page}) for {src.page_count} pages."
                    )
            handle = self._engine._handle(doc)
            handle.insert_pdf(src, from_page=from_page, to_page=to_page, start_at=at_index)
            inserted = to_page - from_page + 1
        finally:
            src.close()

        self._sync_page_count(doc)
        self._mark_dirty()
        return inserted

    def split_document(
        self,
        doc: Document,
        ranges: list[tuple[int, int]],
        output_dir: str | Path,
        *,
        stem: str | None = None,
    ) -> list[Path]:
        """Export page ranges as separate PDF files (0-based inclusive ranges)."""
        return self._engine.split_document(doc, ranges, output_dir, stem=stem)

    def merge_documents(self, file_paths: list[str | Path], output_path: str | Path) -> Path:
        """Combine multiple PDFs into one file in the given order."""
        return self._engine.merge_documents(file_paths, output_path)

    def _mark_dirty(self) -> None:
        self._dirty = True

    def _sync_page_count(self, doc: Document) -> None:
        doc.page_count = self._engine.page_count(doc)


def parse_page_ranges(text: str, page_count: int) -> list[tuple[int, int]]:
    """Parse user ranges like ``1-3, 4-6, 7`` into 0-based inclusive tuples."""
    cleaned = text.strip()
    if not cleaned:
        raise PageIndexError("Page ranges cannot be empty.")

    ranges: list[tuple[int, int]] = []
    for part in cleaned.split(","):
        token = part.strip()
        if not token:
            continue
        if "-" in token:
            left, right = token.split("-", 1)
            start = int(left.strip())
            end = int(right.strip())
        else:
            start = end = int(token)
        if start < 1 or end < 1 or start > end or end > page_count:
            raise PageIndexError(f"Invalid page range: {token}")
        ranges.append((start - 1, end - 1))

    if not ranges:
        raise PageIndexError("Page ranges cannot be empty.")
    return ranges


def ranges_from_split_points(page_count: int, split_after: list[int]) -> list[tuple[int, int]]:
    """Build 0-based inclusive ranges from split points after page indices."""
    if page_count <= 0:
        raise PageIndexError("Document has no pages.")
    if page_count == 1:
        return [(0, 0)]

    valid = sorted({index for index in split_after if 0 <= index < page_count - 1})
    ranges: list[tuple[int, int]] = []
    start = 0
    for split_index in valid:
        ranges.append((start, split_index))
        start = split_index + 1
    ranges.append((start, page_count - 1))
    return ranges
