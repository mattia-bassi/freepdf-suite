"""FreePDF Suite core engine: PDF backend, format handling, shared models."""

from __future__ import annotations

from . import errors
from .errors import FreePDFError
from .format_handler import FormatHandler
from .models import (
    Document,
    DocumentFormat,
    DocumentMetadata,
    PageInfo,
    RenderedPage,
    SearchHit,
)
from .pdf_engine import PDFEngine

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "errors",
    "FreePDFError",
    "PDFEngine",
    "FormatHandler",
    "Document",
    "DocumentFormat",
    "DocumentMetadata",
    "PageInfo",
    "RenderedPage",
    "SearchHit",
]
