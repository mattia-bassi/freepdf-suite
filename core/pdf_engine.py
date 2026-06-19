"""PyMuPDF-backed PDF engine (contract §6.2).

All failures raise from the ``core.errors`` hierarchy. PyMuPDF is imported as
``fitz`` and declared in ``pyproject.toml`` as ``pymupdf (>=1.24,<2.0)``.
"""

from __future__ import annotations

import io
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
from .format_handler import FormatHandler
from .models import (
    Document,
    DocumentFormat,
    DocumentMetadata,
    PageInfo,
    RenderedPage,
    SearchHit,
)

Rect = tuple[float, float, float, float]


def _require_fitz() -> None:
    if fitz is None:  # pragma: no cover
        raise DocumentOpenError(
            "PyMuPDF (fitz) is not installed; run `poetry install`."
        )


def _draw_highlights(
    png_bytes: bytes,
    rects: list[Rect],
    dpi: int,
    active: int | None = None,
) -> bytes:
    """Overlay semi-transparent rectangles on a rendered PNG page."""
    from PIL import Image, ImageDraw

    image = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    scale = dpi / 72.0
    for index, (x0, y0, x1, y1) in enumerate(rects):
        fill = (255, 180, 0, 150) if index == active else (255, 255, 0, 90)
        outline = (255, 120, 0, 220) if index == active else (255, 200, 0, 180)
        draw.rectangle(
            [x0 * scale, y0 * scale, x1 * scale, y1 * scale],
            fill=fill,
            outline=outline,
        )
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="PNG")
    return buffer.getvalue()


def _search_flags() -> int | None:
    """Return PyMuPDF flags for case-insensitive search, if available."""
    try:
        from pymupdf import mupdf

        return int(mupdf.FZ_SEARCH_IGNORE_CASE | mupdf.FZ_SEARCH_IGNORE_DIACRITICS)
    except Exception:  # pragma: no cover
        return None


class PDFEngine:
    """Thin, typed facade over PyMuPDF returning core dataclasses."""

    DEFAULT_DPI: int = 150

    def __init__(self) -> None:
        self._formats = FormatHandler()

    def open(self, path: str | Path, password: str | None = None) -> Document:
        _require_fitz()
        path = Path(path)
        if not path.exists():
            raise DocumentOpenError(f"File not found: {path}")

        fmt = self._formats.detect_format(path)
        if fmt == DocumentFormat.P7M:
            try:
                pdf_bytes = self._formats.extract_p7m(path)
            except Exception as exc:  # noqa: BLE001
                raise DocumentOpenError(f"Could not extract P7M payload: {exc}") from exc
            return self._open_stream(pdf_bytes, path, password)

        try:
            handle = fitz.open(path)  # type: ignore[union-attr]
        except Exception as exc:  # noqa: BLE001 - normalize to our hierarchy
            raise DocumentOpenError(f"Could not open {path}: {exc}") from exc

        return self._document_from_handle(handle, path, password, fmt)

    def open_bytes(
        self, data: bytes, *, label: str = "<memory>", password: str | None = None
    ) -> Document:
        """Open a PDF from an in-memory byte buffer."""
        _require_fitz()
        return self._open_stream(data, Path(label), password)

    def close(self, doc: Document) -> None:
        handle = doc._handle
        if handle is not None:
            try:
                getattr(handle, "close", lambda: None)()
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
        self,
        doc: Document,
        page_index: int,
        *,
        dpi: int = DEFAULT_DPI,
        highlight_rects: list[Rect] | None = None,
        active_highlight: int | None = None,
    ) -> RenderedPage:
        page = self._page(doc, page_index)
        pix = page.get_pixmap(dpi=dpi)
        image_bytes = pix.tobytes("png")
        if highlight_rects:
            image_bytes = _draw_highlights(
                image_bytes, highlight_rects, dpi, active_highlight
            )
        return RenderedPage(
            page_index=page_index,
            image_bytes=image_bytes,
            width_px=pix.width,
            height_px=pix.height,
            image_format="png",
        )

    def search_text(self, doc: Document, query: str) -> list[SearchHit]:
        """Find every occurrence of ``query`` across all pages (case-insensitive)."""
        _require_fitz()
        text = query.strip()
        if not text:
            return []
        flags = _search_flags()
        hits: list[SearchHit] = []
        for index in range(self.page_count(doc)):
            page = self._page(doc, index)
            kwargs: dict[str, int] = {}
            if flags is not None:
                kwargs["flags"] = flags
            for rect in page.search_for(text, **kwargs):  # type: ignore[union-attr]
                hits.append(
                    SearchHit(
                        page_index=index,
                        x0=float(rect.x0),
                        y0=float(rect.y0),
                        x1=float(rect.x1),
                        y1=float(rect.y1),
                    )
                )
        return hits

    def export_pages_as_png(
        self,
        doc: Document,
        output_dir: str | Path,
        *,
        dpi: int = DEFAULT_DPI,
        stem: str | None = None,
    ) -> list[Path]:
        """Render every page to a PNG file inside ``output_dir``."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        base = stem or doc.path.stem
        outputs: list[Path] = []
        for index in range(self.page_count(doc)):
            rendered = self.render_page(doc, index, dpi=dpi)
            out_path = output_dir / f"{base}_page{index + 1:03d}.png"
            out_path.write_bytes(rendered.image_bytes)
            outputs.append(out_path)
        return outputs

    def extract_text(self, doc: Document, page_index: int) -> str:
        return self._page(doc, page_index).get_text("text")

    def extract_all_text(self, doc: Document) -> str:
        """Concatenate plain text from every page."""
        parts: list[str] = []
        for index in range(self.page_count(doc)):
            parts.append(self.extract_text(doc, index))
        return "\n".join(parts)

    def merge_documents(self, paths: list[str | Path], output: str | Path) -> Path:
        """Combine multiple PDFs into a single file."""
        _require_fitz()
        if len(paths) < 2:
            raise DocumentSaveError("merge_documents requires at least two input files.")
        output = Path(output)
        merged = fitz.open()  # type: ignore[union-attr]
        try:
            for raw in paths:
                src_path = Path(raw)
                if not src_path.is_file():
                    raise DocumentOpenError(f"File not found: {src_path}")
                src = fitz.open(src_path)  # type: ignore[union-attr]
                try:
                    merged.insert_pdf(src)
                finally:
                    src.close()
            merged.save(str(output), garbage=4, deflate=True)
        except DocumentOpenError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise DocumentSaveError(f"Could not merge into {output}: {exc}") from exc
        finally:
            merged.close()
        return output

    def split_document(
        self,
        doc: Document,
        ranges: list[tuple[int, int]],
        output_dir: str | Path,
        *,
        stem: str | None = None,
    ) -> list[Path]:
        """Split ``doc`` into parts; each range is ``(start_page, end_page)`` inclusive, 0-based."""
        _require_fitz()
        handle = self._handle(doc)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        base = stem or doc.path.stem
        outputs: list[Path] = []
        for part_index, (start, end) in enumerate(ranges, start=1):
            if start < 0 or end >= handle.page_count or start > end:
                raise PageIndexError(
                    f"Invalid split range ({start}, {end}) for {handle.page_count} pages."
                )
            part = fitz.open()  # type: ignore[union-attr]
            try:
                part.insert_pdf(handle, from_page=start, to_page=end)
                out_path = output_dir / f"{base}_part{part_index}.pdf"
                part.save(str(out_path), garbage=4, deflate=True)
                outputs.append(out_path)
            finally:
                part.close()
        return outputs

    def compress_document(
        self,
        doc: Document,
        output: str | Path,
        *,
        garbage: int = 4,
        deflate: bool = True,
    ) -> Path:
        """Rewrite ``doc`` with stronger cleanup/deflate settings."""
        output = Path(output)
        handle = self._handle(doc)
        try:
            handle.save(str(output), garbage=garbage, deflate=deflate, clean=True)
        except Exception as exc:  # noqa: BLE001
            raise DocumentSaveError(f"Could not compress to {output}: {exc}") from exc
        return output

    def encrypt_document(
        self,
        doc: Document,
        output: str | Path,
        *,
        user_password: str,
        owner_password: str | None = None,
    ) -> Path:
        """Save a password-protected copy of ``doc``."""
        output = Path(output)
        handle = self._handle(doc)
        owner = owner_password or user_password
        try:
            handle.save(
                str(output),
                encryption=fitz.PDF_ENCRYPT_AES_256,  # type: ignore[union-attr]
                user_pw=user_password,
                owner_pw=owner,
            )
        except Exception as exc:  # noqa: BLE001
            raise DocumentSaveError(f"Could not encrypt to {output}: {exc}") from exc
        return output

    def reorder_pages(self, doc: Document, order: list[int]) -> None:
        """Reorder pages in-place; ``order`` lists 0-based source indices."""
        handle = self._handle(doc)
        if sorted(order) != list(range(handle.page_count)):
            raise PageIndexError("`order` must be a permutation of all page indices.")
        handle.select(order)

    def rotate_page(self, doc: Document, page_index: int, degrees: int) -> None:
        page = self._page(doc, page_index)
        if degrees not in (0, 90, 180, 270):
            raise PageIndexError("Rotation must be 0, 90, 180, or 270 degrees.")
        page.set_rotation(degrees)

    def add_text_annotation(
        self,
        doc: Document,
        page_index: int,
        text: str,
        *,
        x: float = 36,
        y: float = 48,
        fontsize: float = 12,
    ) -> None:
        """Insert a simple text stamp on the given page."""
        page = self._page(doc, page_index)
        rect = page.rect
        page.insert_text((rect.x0 + x, rect.y0 + y), text, fontsize=fontsize)

    def delete_pages(self, doc: Document, page_indices: list[int]) -> None:
        handle = self._handle(doc)
        to_drop = set(page_indices)
        keep = [i for i in range(handle.page_count) if i not in to_drop]
        if not keep:
            raise PageIndexError("Cannot delete every page.")
        handle.select(keep)

    def extract_metadata(self, doc: Document) -> DocumentMetadata:
        return self._read_metadata(self._handle(doc))

    # --- internals ----------------------------------------------------------
    def _open_stream(
        self, data: bytes, label: Path, password: str | None
    ) -> Document:
        try:
            handle = fitz.open(stream=data, filetype="pdf")  # type: ignore[union-attr]
        except Exception as exc:  # noqa: BLE001
            raise DocumentOpenError(f"Could not open {label}: {exc}") from exc
        return self._document_from_handle(handle, label, password, DocumentFormat.PDF)

    def _document_from_handle(
        self,
        handle,
        path: Path,
        password: str | None,
        fmt: DocumentFormat | None,
    ) -> Document:
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
            format=fmt or DocumentFormat.PDF,
            _handle=handle,
        )

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
