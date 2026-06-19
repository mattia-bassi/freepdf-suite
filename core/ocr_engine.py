"""Local OCR via Tesseract (pytesseract) — no network calls."""

from __future__ import annotations

import os
import sys
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Literal

try:
    import fitz  # type: ignore
except ImportError:  # pragma: no cover
    fitz = None  # type: ignore[assignment]

try:
    import pytesseract
    from PIL import Image
except ImportError:  # pragma: no cover
    pytesseract = None  # type: ignore[assignment]
    Image = None  # type: ignore[assignment,misc]

OutputFormat = Literal["txt", "searchable_pdf"]

DEFAULT_OCR_LANGUAGE = "ita+eng"
DEFAULT_OCR_DPI = 150
TESSERACT_NOT_AVAILABLE_MSG = (
    "Tesseract is not available (not bundled and not found on system PATH)."
)

EXCLUDED_LANGUAGE_CODES: frozenset[str] = frozenset({"osd"})

LANGUAGE_DISPLAY_NAMES: dict[str, str] = {
    "eng": "English",
    "ita": "Italiano",
    "fra": "Français",
    "deu": "Deutsch",
    "spa": "Español",
    "por": "Português",
    "nld": "Nederlands",
    "rus": "Русский",
    "pol": "Polski",
    "ces": "Čeština",
    "slk": "Slovenčina",
    "hun": "Magyar",
    "ron": "Română",
    "bul": "Български",
    "hrv": "Hrvatski",
    "srp": "Srpski",
    "slv": "Slovenščina",
    "ell": "Ελληνικά",
    "tur": "Türkçe",
    "ara": "العربية",
    "heb": "עברית",
    "hin": "हिन्दी",
    "jpn": "日本語",
    "kor": "한국어",
    "chi_sim": "中文 (简体)",
    "chi_tra": "中文 (繁體)",
}

FALLBACK_LANGUAGES: tuple[str, ...] = tuple(LANGUAGE_DISPLAY_NAMES)

_TESSERACT_READY: bool | None = None


class OcrError(RuntimeError):
    """Raised when OCR processing fails."""

    error_code: str = "OCR_ERROR"


def _app_root() -> Path:
    """Same resolution as ``ui.bootstrap.app_root()`` (dev repo root / frozen exe dir)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _tesseract_binary_name() -> str:
    return "tesseract.exe" if sys.platform == "win32" else "tesseract"


def bundled_tesseract_path() -> Path | None:
    """Return the bundled Tesseract executable when present beside the app."""
    candidate = _app_root() / "tesseract" / _tesseract_binary_name()
    return candidate if candidate.is_file() else None


def ocr_temp_dir() -> Path:
    """Return the app temp folder used for OCR outputs."""
    path = _app_root() / "temp"
    path.mkdir(parents=True, exist_ok=True)
    return path


def create_temp_ocr_output_path(source_pdf: Path, output_format: OutputFormat) -> Path:
    """Build a unique temp output path for OCR results."""
    suffix = ".pdf" if output_format == "searchable_pdf" else ".txt"
    stem = source_pdf.stem or "document"
    return ocr_temp_dir() / f"{stem}_ocr_{uuid.uuid4().hex[:8]}{suffix}"


def cleanup_ocr_temp_files() -> None:
    """Remove OCR temp files (called on application shutdown)."""
    temp_dir = _app_root() / "temp"
    if not temp_dir.is_dir():
        return
    for path in temp_dir.iterdir():
        if not path.is_file():
            continue
        try:
            path.unlink()
        except OSError:
            continue


def _apply_tesseract_cmd(binary: Path | None) -> None:
    """Point pytesseract at a bundled binary or revert to the system PATH default."""
    if pytesseract is None:
        return
    if binary is not None:
        pytesseract.pytesseract.tesseract_cmd = str(binary)
        tessdata_dir = binary.parent / "tessdata"
        if tessdata_dir.is_dir():
            os.environ["TESSDATA_PREFIX"] = str(tessdata_dir)
    else:
        pytesseract.pytesseract.tesseract_cmd = "tesseract"
        os.environ.pop("TESSDATA_PREFIX", None)


def _probe_tesseract(binary: Path | None) -> bool:
    """Configure pytesseract and verify the binary responds."""
    if pytesseract is None:
        return False
    _apply_tesseract_cmd(binary)
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _reset_tesseract_cache() -> None:
    """Clear cached availability (used by tests)."""
    global _TESSERACT_READY
    _TESSERACT_READY = None


def _ensure_tesseract_configured() -> bool:
    """Detect bundled Tesseract first, then fall back to system PATH."""
    global _TESSERACT_READY
    if _TESSERACT_READY is not None:
        return _TESSERACT_READY

    if pytesseract is None:
        _TESSERACT_READY = False
        return False

    bundled = bundled_tesseract_path()
    if bundled is not None and _probe_tesseract(bundled):
        _TESSERACT_READY = True
        return True

    if _probe_tesseract(None):
        _TESSERACT_READY = True
        return True

    _TESSERACT_READY = False
    return False


def check_tesseract_available() -> bool:
    """Return True when a bundled or system Tesseract binary is reachable."""
    return _ensure_tesseract_configured()


def _raw_installed_language_codes() -> list[str]:
    """Return raw language codes reported by Tesseract."""
    if not check_tesseract_available() or pytesseract is None:
        return list(FALLBACK_LANGUAGES)
    try:
        langs = pytesseract.get_languages(config="")
        cleaned = sorted({code.strip() for code in langs if code and code.strip()})
        return cleaned if cleaned else list(FALLBACK_LANGUAGES)
    except Exception:
        return list(FALLBACK_LANGUAGES)


def get_ocr_language_choices() -> list[tuple[str, str]]:
    """Return (code, friendly name) pairs for known installed OCR languages."""
    installed = set(_raw_installed_language_codes())
    choices: list[tuple[str, str]] = []
    for code, label in LANGUAGE_DISPLAY_NAMES.items():
        if code in EXCLUDED_LANGUAGE_CODES:
            continue
        if code in installed:
            choices.append((code, label))
    return choices


def get_ocr_languages() -> list[str]:
    """Return installed OCR language codes limited to the known language map."""
    return [code for code, _label in get_ocr_language_choices()]


def _require_ocr_deps() -> None:
    if fitz is None:
        raise OcrError("PyMuPDF is not installed.")
    if pytesseract is None or Image is None:
        raise OcrError("pytesseract or Pillow is not installed.")


def _open_pdf_document(pdf_path: Path, pdf_bytes: bytes | None) -> fitz.Document:
    _require_ocr_deps()
    if pdf_bytes is not None:
        return fitz.open(stream=pdf_bytes, filetype="pdf")  # type: ignore[union-attr]
    if not pdf_path.exists():
        raise OcrError(f"File not found: {pdf_path}")
    return fitz.open(pdf_path)  # type: ignore[union-attr]


def _page_to_image(page: fitz.Page, dpi: int) -> Image.Image:
    pixmap = page.get_pixmap(dpi=dpi, alpha=False)
    return Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)


def _tesseract_word_data(image: Image.Image, language: str) -> dict[str, list]:
    """Return Tesseract word-level OCR data as a dict."""
    output_type = getattr(pytesseract, "Output", None)
    dict_type = output_type.DICT if output_type is not None else "dict"
    return pytesseract.image_to_data(  # type: ignore[union-attr,no-any-return]
        image,
        lang=language,
        output_type=dict_type,
    )


def _add_invisible_text_layer(
    page: fitz.Page,
    image: Image.Image,
    language: str,
    page_width: float,
    page_height: float,
) -> None:
    """Overlay invisible selectable text on a page image at full render quality."""
    data = _tesseract_word_data(image, language)
    texts = data.get("text", [])
    if not texts:
        return

    scale_x = page_width / max(1, image.width)
    scale_y = page_height / max(1, image.height)

    for index, raw_text in enumerate(texts):
        text = str(raw_text).strip()
        if not text:
            continue
        try:
            confidence = int(data.get("conf", ["-1"])[index])
        except (TypeError, ValueError, IndexError):
            confidence = -1
        if confidence < 1:
            continue

        left = float(data["left"][index])
        top = float(data["top"][index])
        width = float(data["width"][index])
        height = float(data["height"][index])
        x0 = left * scale_x
        y0 = top * scale_y
        y1 = (top + height) * scale_y
        fontsize = max(4.0, height * scale_y * 0.85)
        page.insert_text(  # type: ignore[union-attr]
            (x0, y1),
            f"{text} ",
            fontsize=fontsize,
            render_mode=3,
        )


def _write_txt_output(
    doc: fitz.Document,
    output_path: Path,
    *,
    language: str,
    dpi: int,
    progress_callback: Callable[[int, int], None] | None,
) -> None:
    total = doc.page_count
    chunks: list[str] = []
    for index in range(total):
        page = doc.load_page(index)
        image = _page_to_image(page, dpi)
        text = pytesseract.image_to_string(image, lang=language)  # type: ignore[union-attr]
        chunks.append(text.rstrip())
        if progress_callback is not None:
            progress_callback(index + 1, total)
    output_path.write_text("\n\n".join(chunks).strip() + "\n", encoding="utf-8")


def _write_searchable_pdf_output(
    doc: fitz.Document,
    output_path: Path,
    *,
    language: str,
    dpi: int,
    progress_callback: Callable[[int, int], None] | None,
) -> None:
    """Build a searchable PDF using full-quality page images plus invisible OCR text."""
    total = doc.page_count
    output_doc = fitz.open()  # type: ignore[union-attr]
    try:
        for index in range(total):
            source_page = doc.load_page(index)
            page_rect = source_page.rect
            pixmap = source_page.get_pixmap(dpi=dpi, alpha=False)
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)

            new_page = output_doc.new_page(width=page_rect.width, height=page_rect.height)
            new_page.insert_image(new_page.rect, pixmap=pixmap)
            _add_invisible_text_layer(
                new_page,
                image,
                language,
                float(page_rect.width),
                float(page_rect.height),
            )

            if progress_callback is not None:
                progress_callback(index + 1, total)
        output_doc.save(str(output_path))
    finally:
        output_doc.close()


def run_ocr_on_pdf(
    pdf_path: str | Path,
    output_path: str | Path,
    output_format: OutputFormat,
    language: str = DEFAULT_OCR_LANGUAGE,
    dpi: int = DEFAULT_OCR_DPI,
    progress_callback: Callable[[int, int], None] | None = None,
    *,
    pdf_bytes: bytes | None = None,
) -> None:
    """Run local OCR on every page of a PDF and write txt or searchable PDF output."""
    if not check_tesseract_available():
        raise OcrError(TESSERACT_NOT_AVAILABLE_MSG)
    if output_format not in ("txt", "searchable_pdf"):
        raise OcrError(f"Unsupported output format: {output_format}")

    pdf_path = Path(pdf_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = _open_pdf_document(pdf_path, pdf_bytes)
    try:
        if doc.page_count == 0:
            raise OcrError("The document has no pages to process.")
        if output_format == "txt":
            _write_txt_output(
                doc,
                output_path,
                language=language,
                dpi=dpi,
                progress_callback=progress_callback,
            )
        else:
            _write_searchable_pdf_output(
                doc,
                output_path,
                language=language,
                dpi=dpi,
                progress_callback=progress_callback,
            )
    except OcrError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise OcrError(f"OCR failed: {exc}") from exc
    finally:
        doc.close()
