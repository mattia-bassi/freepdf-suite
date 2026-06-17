"""PyMuPDF-backed PDF engine (contract §6.2).

All failures raise from the ``core.errors`` hierarchy. PyMuPDF is imported as
``fitz`` and declared in ``pyproject.toml`` as ``pymupdf (>=1.24,<2.0)``.
"""

from __future__ import annotations

import uuid
from pathlib import Path

try:  # PyMuPDF is a runtime dependency; tolerate absence at import time.
    import fitz  # type: ignore
except ImportError:  # pragma: no cover - exercised only without the dep installed
    fitz = None  # type: ignore[assignment]

from .errors import (
    DocumentOpenError,
    DocumentSaveError,
    EncryptedDocumentError,
    PageIndexError,
)
from .models import (
    Document,
    DocumentFormat,
    DocumentMetadata,
    PageInfo,
    RenderedPage,
)


def _require_fitz() -> None:
    if fitz is None:  # pragma: no cover
        raise DocumentOpenError(
            "PyMuPDF (fitz) is not installed; run `poetry install`."
        )


class PDFEngine:
    """Thin, typed facade over PyMuPDF returning core dataclasses."""

    DEFAULT_DPI: int = 150

    def open(self, path: str | Path, password: str | None = None) -> Document:
        _require_fitz()
        path = Path(path)
        if not path.exists():
            raise DocumentOpenError(f"File not found: {path}")
        try:
            handle = fitz.open(path)  # type: ignore[union-attr]
        except Exception as exc:  # noqa: BLE001 - normalize to our hierarchy
            raise DocumentOpenError(f"Could not open {path}: {exc}") from exc

        is_encrypted = bool(getattr(handle, "needs_pass", False))
        if is_encrypted:
            if password is None or not handle.authenticate(password):
                handle.close()
                raise EncryptedDocumentError(f"Password required/incorrect: {path}")

        metadata = self._read_metadata(handle)
        return Document(
            doc_id=uuid.uuid4().hex,
            path=path,
            page_count=handle.page_count,
            metadata=metadata,
            is_encrypted=is_encrypted,
            format=DocumentFormat.PDF,
            _handle=handle,
        )

    def close(self, doc: Document) -> None:
        handle = doc._handle
        if handle is not None:
            try:
                handle.close()
            except Exception:  # noqa: BLE001 - close is best-effort
                pass
            doc._handle = None

    def save(
        self,
        doc: Document,
        path: str | Path,
        *,
        incremental: bool = False,
        garbage: int = 1,
    ) -> None:
        handle = self._handle(doc)
        path = Path(path)
        try:
            handle.save(
                str(path), incremental=incremental, garbage=garbage, deflate=True
            )
        except Exception as exc:  # noqa: BLE001
            raise DocumentSaveError(f"Could not save {path}: {exc}") from exc

    def page_count(self, doc: Document) -> int:
        return self._handle(doc).page_count

    def page_info(self, doc: Document, page_index: int) -> PageInfo:
        page = self._page(doc, page_index)
        rect = page.rect
        return PageInfo(
            index=page_index,
            width=float(rect.width),
            height=float(rect.height),
            rotation=int(page.rotation),
        )

    def render_page(
        self, doc: Document, page_index: int, *, dpi: int = DEFAULT_DPI
    ) -> RenderedPage:
        page = self._page(doc, page_index)
        pix = page.get_pixmap(dpi=dpi)
        return RenderedPage(
            page_index=page_index,
            image_bytes=pix.tobytes("png"),
            width_px=pix.width,
            height_px=pix.height,
            image_format="png",
        )

    def extract_text(self, doc: Document, page_index: int) -> str:
        return self._page(doc, page_index).get_text("text")

    def extract_metadata(self, doc: Document) -> DocumentMetadata:
        return self._read_metadata(self._handle(doc))

    # --- internals ----------------------------------------------------------
    @staticmethod
    def _handle(doc: Document):
        handle = doc._handle
        if handle is None:
            raise DocumentOpenError("Document is closed or was never opened.")
        return handle

    def _page(self, doc: Document, page_index: int):
        handle = self._handle(doc)
        if page_index < 0 or page_index >= handle.page_count:
            raise PageIndexError(
                f"Page {page_index} out of range [0, {handle.page_count})."
            )
        return handle.load_page(page_index)

    @staticmethod
    def _read_metadata(handle) -> DocumentMetadata:
        meta = dict(getattr(handle, "metadata", None) or {})
        return DocumentMetadata(
            title=meta.get("title") or None,
            author=meta.get("author") or None,
            subject=meta.get("subject") or None,
            keywords=meta.get("keywords") or None,
            creator=meta.get("creator") or None,
            producer=meta.get("producer") or None,
            created=meta.get("creationDate") or None,
            modified=meta.get("modDate") or None,
        )
