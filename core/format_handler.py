"""Format detection + P7M / PDF-A handling (contract §6.3).

P7M is assumed to be a CAdES ``.p7m`` envelope wrapping a PDF (Italian "firma
digitale" context, contract §10.5). PDF/A conversion is stubbed in Wave-2 and
raises ``PDFAConversionError`` until Wave-3.
"""

from __future__ import annotations

from pathlib import Path

from .errors import P7MExtractionError, PDFAConversionError, UnsupportedFormatError
from .models import DocumentFormat

_PDF_MAGIC = b"%PDF-"


class FormatHandler:
    def detect_format(self, path: str | Path) -> DocumentFormat:
        path = Path(path)
        name = path.name.lower()
        if name.endswith(".p7m"):
            return DocumentFormat.P7M
        try:
            head = path.read_bytes()[:1024]
        except OSError as exc:
            raise UnsupportedFormatError(f"Cannot read {path}: {exc}") from exc
        if head.startswith(_PDF_MAGIC):
            return DocumentFormat.PDF_A if self._looks_pdfa(head) else DocumentFormat.PDF
        if b"%PDF-" in head:  # signed/wrapped PDF whose header is offset
            return DocumentFormat.PDF
        return DocumentFormat.UNKNOWN

    def is_pdfa(self, path: str | Path) -> bool:
        path = Path(path)
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise UnsupportedFormatError(f"Cannot read {path}: {exc}") from exc
        return self._looks_pdfa(data)

    def extract_p7m(self, path: str | Path) -> bytes:
        """Return the inner PDF bytes from a CAdES ``.p7m`` envelope.

        Uses ``asn1crypto`` when available; otherwise falls back to scanning for
        the embedded ``%PDF`` payload. Raises ``P7MExtractionError`` on failure.
        """
        path = Path(path)
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise P7MExtractionError(f"Cannot read {path}: {exc}") from exc

        try:  # preferred: proper PKCS#7 / CMS parse
            from asn1crypto import cms  # type: ignore

            content = cms.ContentInfo.load(raw)["content"]
            data = content["encap_content_info"]["content"].native
            if data:
                return bytes(data)
        except ImportError:
            pass  # fall through to byte-scan heuristic
        except Exception:
            pass  # malformed CMS — try embedded PDF scan below

        start = raw.find(_PDF_MAGIC)
        if start == -1:
            raise P7MExtractionError(f"No embedded PDF found in {path}.")
        end = raw.rfind(b"%%EOF")
        end = end + 5 if end != -1 else len(raw)
        return raw[start:end]

    def to_pdfa(
        self, src: str | Path, dst: str | Path, *, conformance: str = "pdfa-2b"
    ) -> None:
        # CONTRACT-DEVIATION: real PDF/A conversion is Wave-3 (contract §10.6).
        raise PDFAConversionError(
            f"PDF/A conversion ({conformance}) not implemented until Wave-3."
        )

    # --- internals ----------------------------------------------------------
    @staticmethod
    def _looks_pdfa(data: bytes) -> bool:
        return b"pdfaid:part" in data or b"http://www.aiim.org/pdfa/ns/id/" in data
