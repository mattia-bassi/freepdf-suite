"""FreePDF Suite exception hierarchy (contract §8).

Single base ``FreePDFError`` so callers can ``except FreePDFError``. Each class
carries an ``error_code`` string in SCREAMING_SNAKE_CASE.
"""

from __future__ import annotations


class FreePDFError(Exception):
    """Base for every error raised inside FreePDF Suite."""

    error_code: str = "FREEPDF_ERROR"


# --- document layer ---------------------------------------------------------
class DocumentError(FreePDFError):
    error_code = "DOCUMENT_ERROR"


class DocumentOpenError(DocumentError):
    error_code = "DOCUMENT_OPEN_ERROR"


class DocumentSaveError(DocumentError):
    error_code = "DOCUMENT_SAVE_ERROR"


class EncryptedDocumentError(DocumentError):
    error_code = "ENCRYPTED_DOCUMENT_ERROR"


class PageIndexError(DocumentError):
    error_code = "PAGE_INDEX_ERROR"


# --- format layer -----------------------------------------------------------
class FormatError(FreePDFError):
    error_code = "FORMAT_ERROR"


class UnsupportedFormatError(FormatError):
    error_code = "UNSUPPORTED_FORMAT_ERROR"


class P7MExtractionError(FormatError):
    error_code = "P7M_EXTRACTION_ERROR"


class PDFAConversionError(FormatError):
    error_code = "PDFA_CONVERSION_ERROR"
