"""Full-featured PDF reader with lazy page rendering on scroll."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QDragEnterEvent, QDragMoveEvent, QDropEvent, QImage, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .file_drop import accept_file_drag, enable_file_drops, path_from_drop
from .i18n import tr
from .ocr_overlay import OcrProcessingOverlay
from .page_geometry import (
    PageDisplayMetrics,
    metrics_from_render,
    pdf_rect_to_widget,
    widget_drag_rect_to_pdf,
    widget_point_to_pdf,
    widget_point_to_pdf_clamped,
)
from .page_render_queue import PageRenderQueue
from .page_view_label import PageViewLabel
from .style import INTERACTION_BORDER, TEXT_SECONDARY
from .thumbnail_panel import ThumbnailPanel
from .visual_effects import search_rim_glow

ZOOM_MIN = 0.1
ZOOM_MAX = 4.0
ZOOM_STEP = 0.1
PAGE_BUFFER = 2


class ViewerEmptyState(QWidget):
    """Centered empty-state panel; double-click opens the file dialog."""

    open_requested = Signal()

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: ANN001, N802
        self.open_requested.emit()
        super().mouseDoubleClickEvent(event)


class PdfReaderWidget(QWidget):
    """Continuous-scroll PDF viewer; renders visible pages via a background queue."""

    page_changed = Signal(int)
    open_file_requested = Signal()
    file_dropped = Signal(object)
    fit_mode_changed = Signal(object)

    def __init__(self, config: dict[str, Any] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        enable_file_drops(self)

        self._config = dict(config or {})
        self._engine: Any = None
        self._doc: Any = None
        self._base_dpi = int(self._config.get("render_dpi", 150))
        self._zoom = float(self._config.get("zoom_default", 1.0))
        self._fit_mode: str | None = None
        self._current_page = 0
        self._search_query = ""
        self._search_hits: list[Any] = []
        self._active_hit = -1
        self._page_labels: dict[int, PageViewLabel] = {}
        self._page_pixmaps: dict[int, QPixmap] = {}
        self._page_display_metrics: dict[int, PageDisplayMetrics] = {}
        self._updating_page = False
        self._queue = PageRenderQueue()
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.timeout.connect(self._process_render_queue)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self._thumbs = ThumbnailPanel()
        self._thumbs.page_selected.connect(self.go_to_page)
        enable_file_drops(self._thumbs)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("pdfViewerScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._scroll.viewport().installEventFilter(self)

        self._container = QWidget()
        self._container.setObjectName("pdfViewerCanvas")
        self._layout = QVBoxLayout(self._container)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self._layout.setSpacing(16)
        self._scroll.setWidget(self._container)
        root.addWidget(self._scroll, 1)

        enable_file_drops(self._scroll)
        enable_file_drops(self._scroll.viewport())
        enable_file_drops(self._container)

        self._placeholder = ViewerEmptyState()
        self._placeholder.setObjectName("viewerEmptyState")
        placeholder_layout = QVBoxLayout(self._placeholder)
        placeholder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.setSpacing(8)

        self._empty_title = QLabel(self._placeholder)
        self._empty_title.setObjectName("viewerEmptyTitle")
        self._empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._empty_hints = QLabel(self._placeholder)
        self._empty_hints.setObjectName("viewerEmptyHints")
        self._empty_hints.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_hints.setTextFormat(Qt.TextFormat.RichText)

        self._placeholder_message = QLabel(self._placeholder)
        self._placeholder_message.setObjectName("viewerPlaceholder")
        self._placeholder_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder_message.setWordWrap(True)
        self._placeholder_message.hide()

        placeholder_layout.addWidget(self._empty_title)
        placeholder_layout.addWidget(self._empty_hints)
        placeholder_layout.addWidget(self._placeholder_message)
        self._placeholder.open_requested.connect(self.open_file_requested.emit)
        self._layout.addWidget(self._placeholder)
        self._refresh_empty_state()
        search_rim_glow(self._empty_hints)

        self._scroll.verticalScrollBar().valueChanged.connect(self._on_scroll)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        copy_shortcut = QShortcut(QKeySequence.StandardKey.Copy, self)
        copy_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        copy_shortcut.activated.connect(self.copy_selection)
        esc_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        esc_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        esc_shortcut.activated.connect(self.clear_selection)

        self._ocr_overlay = OcrProcessingOverlay(self)
        self._ocr_overlay.hide()

    def _emit_dropped_file(self, path: Path) -> None:
        self.file_dropped.emit(path)

    # -- public API ----------------------------------------------------------

    @property
    def thumbnail_panel(self) -> ThumbnailPanel:
        """Sidebar thumbnail list (hosted in a floating card by MainWindow)."""
        return self._thumbs

    def attach_engine(self, engine: Any) -> None:
        self._engine = engine

    def retranslate_ui(self) -> None:
        """Refresh reader child widgets for the active language."""
        self._thumbs.retranslate_ui()
        if self._placeholder_message.isHidden():
            self._refresh_empty_state()
        elif self._placeholder_message.text():
            key = self._placeholder_message.property("message_key")
            if key:
                self._placeholder_message.setText(tr(str(key)))

    @property
    def current_page(self) -> int:
        return self._current_page

    @property
    def zoom(self) -> float:
        return self._zoom

    @property
    def page_count(self) -> int:
        if self._doc is None:
            return 0
        return int(getattr(self._doc, "page_count", 0))

    @property
    def document(self) -> Any:
        return self._doc

    @property
    def fit_mode(self) -> str | None:
        return self._fit_mode

    def show_document(self, doc: Any) -> None:
        """Prepare page placeholders and queue visible pages for rendering."""
        self._render_timer.stop()
        self._queue.clear()
        self._doc = doc
        self._search_query = ""
        self._search_hits = []
        self._active_hit = -1
        self.clear_selection()
        self._current_page = 0
        self._fit_mode = None
        self.fit_mode_changed.emit(None)
        self._zoom = float(self._config.get("zoom_default", 1.0))
        self._clear_pages()

        if self._engine is None or doc is None:
            self._show_placeholder("viewer_engine_unavailable")
            return

        self._placeholder.hide()
        page_count = self.page_count
        if page_count == 0:
            self._show_placeholder("viewer_no_pages")
            return

        self._thumbs.prepare(page_count)
        self._thumbs.start_lazy_load(self._engine, doc)

        dpi = self._effective_dpi()
        for index in range(page_count):
            label = PageViewLabel(index, reader=self)
            label.setMargin(0)
            label.setContentsMargins(0, 0, 0, 0)
            try:
                info = self._engine.page_info(doc, index)
                height_px = max(80, int(info.height * dpi / 72.0))
                width_px = max(60, int(info.width * dpi / 72.0))
                label.setMinimumSize(width_px, height_px)
            except Exception:
                label.setMinimumHeight(400)
            self._layout.addWidget(label)
            self._page_labels[index] = label

        self._thumbs.set_current_page(0)
        self.page_changed.emit(0)
        self._schedule_visible_render()

    def reload_document(self, *, current_page: int | None = None) -> None:
        """Refresh viewer and thumbnails after in-place page structure changes."""
        if self._doc is None:
            return
        page = self._current_page if current_page is None else current_page
        self.show_document(self._doc)
        if self.page_count > 0:
            self.go_to_page(min(max(0, page), self.page_count - 1))

    def refresh_page_view(self, *, page_index: int | None = None) -> None:
        """Refresh thumbnails and rendered pages without rebuilding the full layout."""
        if self._doc is None or self._engine is None:
            return
        self._thumbs.refresh(self._engine, self._doc)
        self._invalidate_render_cache()
        self._schedule_visible_render(front=page_index if page_index is not None else self._current_page)

    def go_to_page(self, page_index: int) -> None:
        if page_index < 0 or page_index >= self.page_count:
            return
        self._current_page = page_index
        label = self._page_labels.get(page_index)
        if label is not None:
            self._updating_page = True
            self._scroll.ensureWidgetVisible(label, 0, 80)
            self._updating_page = False
        self._thumbs.set_current_page(page_index)
        self.page_changed.emit(page_index)
        self._schedule_visible_render(front=page_index)

    def next_page(self) -> None:
        if self._current_page + 1 < self.page_count:
            self.go_to_page(self._current_page + 1)

    def previous_page(self) -> None:
        if self._current_page > 0:
            self.go_to_page(self._current_page - 1)

    def set_zoom(self, zoom: float) -> None:
        self._fit_mode = None
        self._zoom = max(ZOOM_MIN, min(ZOOM_MAX, zoom))
        self._invalidate_render_cache()
        self.fit_mode_changed.emit(None)

    def zoom_in(self) -> None:
        self.set_zoom(self._zoom + ZOOM_STEP)

    def zoom_out(self) -> None:
        self.set_zoom(self._zoom - ZOOM_STEP)

    def fit_width(self) -> None:
        self._fit_mode = "width"
        self._apply_fit()
        self.fit_mode_changed.emit("width")

    def fit_page(self) -> None:
        self._fit_mode = "page"
        self._apply_fit()
        self.fit_mode_changed.emit("page")

    def find_text(self, query: str) -> int:
        self._search_query = query.strip()
        self._search_hits = []
        self._active_hit = -1
        if not self._search_query or self._engine is None or self._doc is None:
            self._invalidate_render_cache()
            return 0
        self._search_hits = self._engine.search_text(self._doc, self._search_query)
        if self._search_hits:
            self._active_hit = 0
            self._go_to_hit(0)
        else:
            self._invalidate_render_cache()
        return len(self._search_hits)

    def find_next(self) -> bool:
        if not self._search_hits:
            return False
        self._active_hit = (self._active_hit + 1) % len(self._search_hits)
        self._go_to_hit(self._active_hit)
        return True

    def find_previous(self) -> bool:
        if not self._search_hits:
            return False
        self._active_hit = (self._active_hit - 1) % len(self._search_hits)
        self._go_to_hit(self._active_hit)
        return True

    def words_for_page(self, page_index: int) -> list[tuple[tuple[float, float, float, float], str]]:
        if self._engine is None or self._doc is None:
            return []
        try:
            return self._engine.get_text_words(self._doc, page_index)
        except Exception:
            return []

    def widget_point_to_pdf(self, page_index: int, x: float, y: float) -> tuple[float, float]:
        metrics, origin_x, origin_y, pix_w, pix_h = self._page_display_state(page_index)
        return widget_point_to_pdf_clamped(x, y, metrics, origin_x, origin_y, pix_w, pix_h)

    def widget_drag_rect_to_pdf(
        self, page_index: int, x0: float, y0: float, x1: float, y1: float
    ) -> tuple[float, float, float, float]:
        metrics, origin_x, origin_y, pix_w, pix_h = self._page_display_state(page_index)
        return widget_drag_rect_to_pdf(x0, y0, x1, y1, metrics, origin_x, origin_y, pix_w, pix_h)

    def pdf_rect_to_widget(
        self, page_index: int, rect: tuple[float, float, float, float]
    ) -> tuple[float, float, float, float] | None:
        metrics, origin_x, origin_y, _pw, _ph = self._page_display_state(page_index)
        return pdf_rect_to_widget(rect, metrics, origin_x, origin_y)

    def _page_display_state(self, page_index: int) -> tuple[PageDisplayMetrics, float, float, int, int]:
        label = self._page_labels.get(page_index)
        if label is None:
            dpi = self._effective_dpi()
            pix_w = max(1, int(612 * dpi / 72))
            pix_h = max(1, int(792 * dpi / 72))
            return PageDisplayMetrics(612.0, 792.0, pix_w, pix_h), 0.0, 0.0, pix_w, pix_h

        pixmap = label.pixmap()
        if pixmap is None or pixmap.isNull():
            pixmap = self._page_pixmaps.get(page_index)

        if pixmap is not None and not pixmap.isNull() and self._engine is not None and self._doc is not None:
            info = self._engine.page_info(self._doc, page_index)
            metrics = metrics_from_render(
                info.width,
                info.height,
                pixmap.width(),
                pixmap.height(),
            )
            pix_w = pixmap.width()
            pix_h = pixmap.height()
        else:
            metrics = self._page_display_metrics.get(page_index)
            if metrics is None:
                metrics = self._fallback_page_metrics(page_index)
            pix_w = metrics.pixmap_width_px
            pix_h = metrics.pixmap_height_px

        origin_x, origin_y = self._pixmap_origin(label, pixmap)
        return metrics, origin_x, origin_y, pix_w, pix_h

    def _fallback_page_metrics(self, page_index: int) -> PageDisplayMetrics:
        dpi = self._effective_dpi()
        if self._engine is None or self._doc is None:
            return PageDisplayMetrics(612.0, 792.0, max(1, int(612 * dpi / 72)), max(1, int(792 * dpi / 72)))
        info = self._engine.page_info(self._doc, page_index)
        return metrics_from_render(
            info.width,
            info.height,
            max(1, int(info.width * dpi / 72.0)),
            max(1, int(info.height * dpi / 72.0)),
        )

    def _pixmap_origin(self, label: PageViewLabel, pixmap: QPixmap | None) -> tuple[float, float]:
        if pixmap is None or pixmap.isNull():
            return 0.0, 0.0
        contents = label.contentsRect()
        origin_x = float(contents.x()) + (float(contents.width()) - float(pixmap.width())) / 2.0
        origin_y = float(contents.y()) + (float(contents.height()) - float(pixmap.height())) / 2.0
        return origin_x, origin_y

    def clear_selection(self, *, except_page: int | None = None) -> None:
        for index, label in self._page_labels.items():
            if except_page is not None and index == except_page:
                continue
            label.clear_selection()

    def copy_selection(self) -> None:
        for label in self._page_labels.values():
            if label.has_selection() and label.copy_selection():
                return

    def _widget_to_pdf_scale(self, page_index: int) -> float:
        """Backward-compatible helper returning horizontal PDF points per pixel."""
        metrics, _, _, _, _ = self._page_display_state(page_index)
        return metrics.scale_x

    def _pixmap_offset(self, page_index: int) -> tuple[float, float]:
        label = self._page_labels.get(page_index)
        if label is None:
            return 0.0, 0.0
        return self._pixmap_origin(label, self._page_pixmaps.get(page_index))

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._ocr_overlay.resize_with_parent()
        if self._fit_mode is not None:
            self._apply_fit()

    def show_ocr_progress(self, current: int, total: int) -> None:
        self._ocr_overlay.set_progress(current, total)
        if not self._ocr_overlay.isVisible():
            self._ocr_overlay.show_overlay()

    def hide_ocr_progress(self) -> None:
        self._ocr_overlay.hide_overlay()

    # -- drag & drop ---------------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if not accept_file_drag(event):
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:  # noqa: N802
        if not accept_file_drag(event):
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        path = path_from_drop(event)
        if path is not None:
            self._emit_dropped_file(path)
        else:
            super().dropEvent(event)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if obj is self._scroll.viewport():
            if event.type() == QEvent.Type.DragEnter:
                if accept_file_drag(event):
                    return True
            elif event.type() == QEvent.Type.DragMove:
                if accept_file_drag(event):
                    return True
            elif event.type() == QEvent.Type.Drop:
                path = path_from_drop(event)
                if path is not None:
                    self._emit_dropped_file(path)
                    return True
            elif event.type() == QEvent.Type.Wheel:
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    if event.angleDelta().y() > 0:
                        self.zoom_in()
                    elif event.angleDelta().y() < 0:
                        self.zoom_out()
                    return True
        return super().eventFilter(obj, event)

    # -- internals -----------------------------------------------------------

    def _clear_pages(self) -> None:
        self._render_timer.stop()
        self._queue.clear()
        self._thumbs.stop_lazy_load()
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None and widget is not self._placeholder:
                widget.deleteLater()
        self._page_labels.clear()
        self._page_pixmaps.clear()
        self._page_display_metrics.clear()
        self._layout.addWidget(self._placeholder)
        self._refresh_empty_state()
        self._placeholder.show()
        self._thumbs.clear_thumbnails()

    def _empty_hints_html(self) -> str:
        open_hint = tr("viewer_hint_open")
        drag = tr("viewer_hint_drag")
        dclick = tr("viewer_hint_dclick")
        return (
            f'<span style="color:{TEXT_SECONDARY}">'
            f'<span style="color:{INTERACTION_BORDER}">{open_hint}</span>'
            f"  ·  {drag}  ·  {dclick}</span>"
        )

    def _refresh_empty_state(self) -> None:
        self._empty_title.setText(tr("viewer_empty_title"))
        self._empty_hints.setText(self._empty_hints_html())
        self._empty_title.show()
        self._empty_hints.show()
        self._placeholder_message.hide()

    def _show_placeholder(self, message_key: str) -> None:
        self._clear_pages()
        self._empty_title.hide()
        self._empty_hints.hide()
        self._placeholder_message.setProperty("message_key", message_key)
        self._placeholder_message.setText(tr(message_key))
        self._placeholder_message.show()
        self._placeholder.show()

    def _effective_dpi(self) -> int:
        return max(36, int(self._base_dpi * self._zoom))

    def _on_scroll(self, _value: int) -> None:
        if not self._updating_page:
            self._sync_page_from_scroll()
        self._schedule_visible_render()

    def _visible_page_indices(self) -> list[int]:
        if not self._page_labels:
            return []
        scroll_top = self._scroll.verticalScrollBar().value()
        viewport_h = self._scroll.viewport().height()
        margin = 200
        top = scroll_top - margin
        bottom = scroll_top + viewport_h + margin
        visible: list[int] = []
        for index, label in self._page_labels.items():
            y = label.y()
            height = label.height()
            if y + height >= top and y <= bottom:
                visible.append(index)
        if not visible and self._page_labels:
            visible.append(self._current_page)
        return visible

    def _schedule_visible_render(self, *, front: int | None = None) -> None:
        if not self._page_labels:
            return
        visible = set(self._visible_page_indices())
        buffered: list[int] = []
        for index in visible:
            buffered.append(index)
            for offset in range(1, PAGE_BUFFER + 1):
                if index - offset >= 0:
                    buffered.append(index - offset)
                if index + offset < self.page_count:
                    buffered.append(index + offset)
        self._queue.enqueue(buffered, front=front)
        if self._queue.has_work() and not self._render_timer.isActive():
            self._render_timer.start(0)

    def _process_render_queue(self) -> None:
        prefer = set(self._visible_page_indices())
        page_index = self._queue.pop(prefer)
        if page_index is None:
            return
        self._render_page(page_index)
        self._queue.mark_done(page_index)
        if self._queue.has_work():
            self._render_timer.start(0)

    def _render_page(self, page_index: int) -> None:
        label = self._page_labels.get(page_index)
        if label is None or self._engine is None or self._doc is None:
            return
        dpi = self._effective_dpi()
        rects = self._highlights_for_page(page_index)
        active = self._active_rect_index_on_page(page_index)
        try:
            rendered = self._engine.render_page(
                self._doc,
                page_index,
                dpi=dpi,
                highlight_rects=rects or None,
                active_highlight=active,
            )
            image = QImage.fromData(rendered.image_bytes, "PNG")
            pixmap = QPixmap.fromImage(image)
            pixmap.setDevicePixelRatio(1.0)
            info = self._engine.page_info(self._doc, page_index)
            self._page_display_metrics[page_index] = metrics_from_render(
                info.width,
                info.height,
                pixmap.width(),
                pixmap.height(),
            )
            self._page_pixmaps[page_index] = pixmap
            label.setPixmap(pixmap)
            label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            label.setFixedSize(pixmap.size())
            label.update()
        except Exception as exc:
            label.setText(f"[page {page_index + 1} failed: {exc}]")

    def _invalidate_render_cache(self) -> None:
        self._render_timer.stop()
        self._queue.invalidate_all()
        self._page_pixmaps.clear()
        self._page_display_metrics.clear()
        for label in self._page_labels.values():
            label.invalidate_word_cache()
        dpi = self._effective_dpi()
        for index, label in self._page_labels.items():
            label.clear()
            label.setMaximumSize(16777215, 16777215)
            if self._engine is not None and self._doc is not None:
                try:
                    info = self._engine.page_info(self._doc, index)
                    label.setMinimumSize(
                        max(60, int(info.width * dpi / 72.0)),
                        max(80, int(info.height * dpi / 72.0)),
                    )
                except Exception:
                    label.setMinimumHeight(400)
        self._schedule_visible_render(front=self._current_page)

    def _highlights_for_page(self, page_index: int) -> list[tuple[float, float, float, float]]:
        if not self._search_query:
            return []
        return [hit.rect for hit in self._search_hits if hit.page_index == page_index]

    def _active_rect_index_on_page(self, page_index: int) -> int | None:
        if self._active_hit < 0 or self._active_hit >= len(self._search_hits):
            return None
        active = self._search_hits[self._active_hit]
        if active.page_index != page_index:
            return None
        page_hits = [h for h in self._search_hits if h.page_index == page_index]
        for index, page_hit in enumerate(page_hits):
            if page_hit == active:
                return index
        return None

    def _go_to_hit(self, hit_index: int) -> None:
        if hit_index < 0 or hit_index >= len(self._search_hits):
            return
        hit = self._search_hits[hit_index]
        self._queue.invalidate_all()
        self._page_pixmaps.clear()
        self.go_to_page(hit.page_index)
        self._schedule_visible_render(front=hit.page_index)

    def _apply_fit(self) -> None:
        if self._fit_mode is None or not self._page_labels or self._engine is None:
            return
        page_index = min(self._current_page, self.page_count - 1)
        info = self._engine.page_info(self._doc, page_index)
        viewport = self._scroll.viewport().size()
        if viewport.width() <= 0 or viewport.height() <= 0:
            return
        if info.width <= 0 or info.height <= 0:
            return
        width_zoom = (viewport.width() - 32) / info.width
        height_zoom = (viewport.height() - 32) / info.height
        if self._fit_mode == "width":
            target = width_zoom * 72.0 / self._base_dpi
        else:
            target = min(width_zoom, height_zoom) * 72.0 / self._base_dpi
        self._zoom = max(ZOOM_MIN, min(ZOOM_MAX, target))
        self._invalidate_render_cache()

    def _sync_page_from_scroll(self) -> None:
        if not self._page_labels:
            return
        scroll_top = self._scroll.verticalScrollBar().value()
        viewport_h = self._scroll.viewport().height()
        midpoint = scroll_top + viewport_h // 3
        best_index = self._current_page
        best_dist = float("inf")
        for index, label in self._page_labels.items():
            dist = abs(label.y() - midpoint)
            if dist < best_dist:
                best_dist = dist
                best_index = index
        if best_index != self._current_page:
            self._current_page = best_index
            self._thumbs.set_current_page(best_index)
            self.page_changed.emit(best_index)
