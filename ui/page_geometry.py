"""Coordinate transforms between PDF points and on-screen page pixels."""

from __future__ import annotations

from dataclasses import dataclass

Rect = tuple[float, float, float, float]


@dataclass(frozen=True)
class PageDisplayMetrics:
    """Link PDF page size (points) to the rendered pixmap size (pixels)."""

    page_width_pt: float
    page_height_pt: float
    pixmap_width_px: int
    pixmap_height_px: int

    @property
    def scale_x(self) -> float:
        """PDF points per horizontal pixel."""
        return self.page_width_pt / max(1, self.pixmap_width_px)

    @property
    def scale_y(self) -> float:
        """PDF points per vertical pixel."""
        return self.page_height_pt / max(1, self.pixmap_height_px)


def widget_point_to_pdf(
    x: float,
    y: float,
    metrics: PageDisplayMetrics,
    origin_x: float,
    origin_y: float,
) -> tuple[float, float]:
    """Convert widget coordinates to PDF page points."""
    return (x - origin_x) * metrics.scale_x, (y - origin_y) * metrics.scale_y


def pdf_rect_to_widget(
    rect: Rect,
    metrics: PageDisplayMetrics,
    origin_x: float,
    origin_y: float,
) -> Rect:
    """Convert a PDF rectangle to widget/pixel coordinates."""
    x0, y0, x1, y1 = rect
    inv_x = 1.0 / metrics.scale_x
    inv_y = 1.0 / metrics.scale_y
    return (
        x0 * inv_x + origin_x,
        y0 * inv_y + origin_y,
        x1 * inv_x + origin_x,
        y1 * inv_y + origin_y,
    )


def metrics_from_render(page_width_pt: float, page_height_pt: float, pixmap_width_px: int, pixmap_height_px: int) -> PageDisplayMetrics:
    """Build display metrics from page and pixmap dimensions."""
    return PageDisplayMetrics(
        page_width_pt=page_width_pt,
        page_height_pt=page_height_pt,
        pixmap_width_px=pixmap_width_px,
        pixmap_height_px=pixmap_height_px,
    )


def pixmap_widget_bounds(
    origin_x: float,
    origin_y: float,
    pixmap_width_px: int,
    pixmap_height_px: int,
) -> Rect:
    """Return the pixmap area in widget coordinates."""
    return (
        origin_x,
        origin_y,
        origin_x + float(pixmap_width_px),
        origin_y + float(pixmap_height_px),
    )


def clamp_point_to_bounds(x: float, y: float, bounds: Rect) -> tuple[float, float]:
    """Clamp a widget point to an axis-aligned bounds rectangle."""
    bx0, by0, bx1, by1 = bounds
    return min(max(x, bx0), bx1), min(max(y, by0), by1)


def widget_point_to_pdf_clamped(
    x: float,
    y: float,
    metrics: PageDisplayMetrics,
    origin_x: float,
    origin_y: float,
    pixmap_width_px: int,
    pixmap_height_px: int,
) -> tuple[float, float]:
    """Convert a widget point to PDF points, clamped to the rendered pixmap."""
    bounds = pixmap_widget_bounds(origin_x, origin_y, pixmap_width_px, pixmap_height_px)
    cx, cy = clamp_point_to_bounds(x, y, bounds)
    return widget_point_to_pdf(cx, cy, metrics, origin_x, origin_y)


def widget_drag_rect_to_pdf(
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    metrics: PageDisplayMetrics,
    origin_x: float,
    origin_y: float,
    pixmap_width_px: int,
    pixmap_height_px: int,
) -> Rect:
    """Convert a widget drag rectangle to PDF points, clamped to the pixmap."""
    bounds = pixmap_widget_bounds(origin_x, origin_y, pixmap_width_px, pixmap_height_px)
    cx0, cy0 = clamp_point_to_bounds(x0, y0, bounds)
    cx1, cy1 = clamp_point_to_bounds(x1, y1, bounds)
    px0, py0 = widget_point_to_pdf(cx0, cy0, metrics, origin_x, origin_y)
    px1, py1 = widget_point_to_pdf(cx1, cy1, metrics, origin_x, origin_y)
    left = min(px0, px1)
    right = max(px0, px1)
    top = min(py0, py1)
    bottom = max(py0, py1)
    return left, top, right, bottom
