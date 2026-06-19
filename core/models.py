"""Shared in-process dataclasses and enums (contract §6.1 / §6.4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class DocumentFormat(str, Enum):
    """On-disk document format detected by ``FormatHandler``."""

    PDF = "pdf"
    PDF_A = "pdf_a"
    P7M = "p7m"  # CAdES-signed (.pdf.p7m)
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DocumentMetadata:
    title: str | None = None
    author: str | None = None
    subject: str | None = None
    keywords: str | None = None
    creator: str | None = None
    producer: str | None = None
    created: str | None = None  # ISO-8601 string
    modified: str | None = None  # ISO-8601 string


@dataclass
class Document:
    doc_id: str  # opaque uuid4 hex assigned on open
    path: Path
    page_count: int
    metadata: DocumentMetadata
    is_encrypted: bool = False
    format: DocumentFormat | None = None  # set on open
    _handle: object = field(default=None, repr=False)  # backend (fitz.Document)


@dataclass(frozen=True)
class PageInfo:
    index: int  # 0-based
    width: float  # points (1/72 in)
    height: float  # points
    rotation: int  # degrees: 0|90|180|270


@dataclass(frozen=True)
class RenderedPage:
    page_index: int
    image_bytes: bytes
    width_px: int
    height_px: int
    image_format: str = "png"  # "png" | "ppm"


@dataclass(frozen=True)
class SearchHit:
    """A text-search match on a single page (rect in PDF points)."""

    page_index: int
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def rect(self) -> tuple[float, float, float, float]:
        return (self.x0, self.y0, self.x1, self.y1)
