"""Main application window: PDF reader shell."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QIcon,
    QKeySequence,
    QShortcut,
)
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QMainWindow,
    QMenu,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .bootstrap import LOGO_PATH, load_backend
from .config_loader import (
    load_app_config,
    load_session_paths,
    recent_files_path,
    save_session_paths,
)
from .document_manager import DocumentManager, DocumentState
from .file_drop import accept_file_drag, enable_file_drops, path_from_drop
from .floating_card import FloatingCard
from .i18n import register_retranslate, tr
from .message_boxes import (
    ask_save_discard_cancel,
    ask_yes_no,
    show_critical,
    show_warning,
)
from .page_manager_dialogs import show_merge_pdf_dialog, show_split_pdf_dialog
from .pdf_reader import PdfReaderWidget
from .recent_files import RecentFilesStore
from .status_bar import show_status_message
from .tools_dialogs import (
    confirm_reset_defaults,
    show_about,
    show_general_settings,
    show_options,
    show_view_settings,
)
from .tab_bar import DocumentTabBar
from .thumbnail_panel import ThumbnailPanel
from .toolbar_widgets import ReaderToolStrip, TopNavBar
from .visual_effects import popup_shadow

from core.ocr_engine import (
    DEFAULT_OCR_DPI,
    DEFAULT_OCR_LANGUAGE,
    check_tesseract_available,
    create_temp_ocr_output_path,
    run_ocr_on_pdf,
)
from core.errors import DocumentOpenError, DocumentSaveError, PageIndexError
from core.page_manager import PageManager

ZOOM_PRESETS: list[tuple[str, float]] = [
    ("10%", 0.1),
    ("25%", 0.25),
    ("50%", 0.5),
    ("75%", 0.75),
    ("100%", 1.0),
    ("125%", 1.25),
    ("150%", 1.5),
    ("200%", 2.0),
    ("400%", 4.0),
]


class _OcrWorker(QThread):
    """Run searchable-PDF OCR off the UI thread."""

    progress = Signal(int, int)
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, *, pdf_path: Path, pdf_bytes: bytes | None, dpi: int) -> None:
        super().__init__()
        self._pdf_path = pdf_path
        self._pdf_bytes = pdf_bytes
        self._dpi = dpi
        self._output_path = create_temp_ocr_output_path(pdf_path, "searchable_pdf")

    def run(self) -> None:
        try:
            run_ocr_on_pdf(
                self._pdf_path,
                self._output_path,
                "searchable_pdf",
                DEFAULT_OCR_LANGUAGE,
                self._dpi,
                progress_callback=self.progress.emit,
                pdf_bytes=self._pdf_bytes,
            )
            self.succeeded.emit(self._output_path)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self, *, initial_path: Path | None = None) -> None:
        super().__init__()
        self.resize(1200, 850)
        if LOGO_PATH.is_file():
            self.setWindowIcon(QIcon(str(LOGO_PATH)))
        enable_file_drops(self)

        self._config = load_app_config()
        self._backend = load_backend()
        self._engine = self._make_engine()
        self._recent = RecentFilesStore(
            recent_files_path(),
            limit=int(self._config.get("recent_files_limit", 10)),
        )
        self._recent_menu: QMenu | None = None
        self._action_open: QAction | None = None
        self._action_save: QAction | None = None
        self._action_save_as: QAction | None = None
        self._action_exit: QAction | None = None
        self._action_zoom_in: QAction | None = None
        self._action_zoom_out: QAction | None = None
        self._action_ocr: QAction | None = None
        self._action_split_pdf: QAction | None = None
        self._action_merge_pdf: QAction | None = None
        self._action_general_settings: QAction | None = None
        self._action_view_settings: QAction | None = None
        self._action_advanced_options: QAction | None = None
        self._action_reset_defaults: QAction | None = None
        self._action_encrypted_pdf: QAction | None = None
        self._action_p7m_files: QAction | None = None
        self._action_missing_fonts: QAction | None = None
        self._action_fit_width: QAction | None = None
        self._action_fit_page: QAction | None = None
        self._action_next_page: QAction | None = None
        self._action_previous_page: QAction | None = None
        self._action_about: QAction | None = None
        self._action_documentation: QAction | None = None
        self._pdf_menu: QMenu | None = None
        self._options_menu: QMenu | None = None
        self._help_menu: QMenu | None = None
        self._doc_open = False
        self._ocr_worker: _OcrWorker | None = None
        self._unregister_i18n = register_retranslate(self.retranslate_ui)

        self._documents = DocumentManager(self._engine, self._config, self)
        self._documents.set_confirm_close_handler(self._confirm_close_tab)
        self._documents.set_reader_factory(self._create_reader)
        self._documents.active_changed.connect(self._on_active_tab_changed)
        self._documents.tabs_changed.connect(self._refresh_tab_bar)
        self._documents.dirty_changed.connect(self._on_tab_dirty_changed)

        empty_reader = self._documents.empty_reader
        empty_reader.open_file_requested.connect(self._on_open)
        empty_reader.file_dropped.connect(self._open_path)

        self._tab_bar = DocumentTabBar(self)
        self._tab_bar.tab_selected.connect(self._documents.switch_to)
        self._tab_bar.tab_close_requested.connect(self._on_close_tab)
        self._tab_bar.close_others_requested.connect(self._on_close_other_tabs)
        self._tab_bar.close_all_requested.connect(self._on_close_all_tabs)
        self._tab_bar.file_dropped_on_tab.connect(self._on_file_dropped_on_tab)

        self._thumb_panel = ThumbnailPanel(self)
        self._wire_thumbnail_panel()

        self._reader_strip = ReaderToolStrip(ZOOM_PRESETS, self)
        self._wire_reader_strip()

        self._build_menus()
        self._build_floating_layout()
        self._setup_nav_bar()
        self._build_shortcuts()
        self._update_page_controls()
        status = self.statusBar()
        status.setObjectName("appStatusBar")
        self._ocr_status_progress = QProgressBar(self)
        self._ocr_status_progress.setObjectName("ocrStatusProgress")
        self._ocr_status_progress.setFixedWidth(180)
        self._ocr_status_progress.setMaximumHeight(14)
        self._ocr_status_progress.setTextVisible(True)
        self._ocr_status_progress.hide()
        status.addPermanentWidget(self._ocr_status_progress)
        self._show_status(self._ready_message(), flash=False)

        if initial_path is not None:
            self._open_path(initial_path)
        else:
            self._restore_last_session()
        self._refresh_tab_bar()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if not accept_file_drag(event):
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:  # noqa: N802
        if not accept_file_drag(event):
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        path = path_from_drop(event)
        if path is not None:
            self._open_path(path)
        else:
            super().dropEvent(event)

    def _make_engine(self) -> Any:
        cls = self._backend.get("PDFEngine")
        if cls is None:
            return None
        try:
            return cls()
        except Exception:
            return None

    def _ready_message(self) -> str:
        if self._engine is None:
            return tr("msg_engine_unavailable")
        return tr("ready_open_pdf")

    def _update_window_title(self) -> None:
        state = self._active_state()
        if state is not None:
            prefix = "● " if state.page_manager.is_dirty else ""
            self.setWindowTitle(f"{prefix}{state.display_name} — {tr('app_title')}")
        else:
            self.setWindowTitle(tr("app_title"))

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if not self._confirm_close_all():
            event.ignore()
            return
        save_session_paths(self._documents.paths_for_session())
        super().closeEvent(event)

    def _active_state(self) -> DocumentState | None:
        return self._documents.get_active()

    def _active_reader(self) -> PdfReaderWidget | None:
        state = self._active_state()
        return state.reader if state is not None else None

    def _active_doc(self) -> Any:
        state = self._active_state()
        return state.document if state is not None else None

    def _active_page_manager(self) -> PageManager | None:
        state = self._active_state()
        return state.page_manager if state is not None else None

    def _create_reader(self) -> PdfReaderWidget:
        reader = PdfReaderWidget(self._config, self)
        reader.attach_engine(self._engine)
        reader.page_changed.connect(self._on_page_changed)
        reader.open_file_requested.connect(self._on_open)
        reader.file_dropped.connect(self._open_path)
        reader.fit_mode_changed.connect(self._reader_strip.set_fit_mode)
        return reader

    def _wire_thumbnail_panel(self) -> None:
        """Connect the single shared sidebar thumbnail panel once."""
        self._thumb_panel.page_selected.connect(self._on_thumbnail_page_selected)
        self._thumb_panel.pages_reordered.connect(self._on_pages_reordered)
        self._thumb_panel.page_rotate_left.connect(
            lambda index: self._on_rotate_page(index, -90)
        )
        self._thumb_panel.page_rotate_right.connect(
            lambda index: self._on_rotate_page(index, 90)
        )
        self._thumb_panel.page_delete_requested.connect(self._on_delete_page)
        self._thumb_panel.page_insert_requested.connect(self._on_insert_pages)

    def _on_thumbnail_page_selected(self, page_index: int) -> None:
        reader = self._active_reader()
        if reader is not None:
            reader.go_to_page(page_index)

    def _sync_thumbnail_panel(self) -> None:
        """Reload the shared thumbnail sidebar for the active document."""
        state = self._active_state()
        if state is None or self._engine is None:
            self._thumb_panel.clear_thumbnails()
            return
        reader = state.reader
        self._thumb_panel.load_document(
            self._engine,
            state.document,
            current_page=reader.current_page,
        )

    def _restore_last_session(self) -> None:
        if not bool(self._config.get("open_last_session", False)):
            return
        for path in load_session_paths():
            self._open_path(path)

    def _refresh_tab_bar(self) -> None:
        labels = [
            self._documents.tab_label(index)
            for index in range(self._documents.tab_count())
        ]
        current = self._documents.active_index
        self._tab_bar.sync_tabs(labels)
        if current >= 0:
            self._tab_bar.set_current_index(current)
        self._tab_bar.setVisible(bool(labels))

    def _on_tab_dirty_changed(self, index: int, _dirty: bool) -> None:
        self._tab_bar.update_tab_text(index, self._documents.tab_label(index))
        self._update_window_title()
        self._update_doc_dependent_actions()

    def _on_active_tab_changed(self, index: int) -> None:
        state = self._documents.get_active()
        if state is None:
            self._doc_open = False
            self._sync_thumbnail_panel()
        else:
            self._doc_open = True
            self._tab_bar.set_current_index(index)
            self._sync_thumbnail_panel()
        self._sync_toolbar_to_active()
        self._update_window_title()
        self._update_page_controls()
        self._update_doc_dependent_actions()
        if not self._doc_open:
            self._show_status(self._ready_message(), flash=False)

    def _sync_toolbar_to_active(self) -> None:
        reader = self._active_reader()
        if reader is None:
            return
        nav = self._reader_strip.page_navigator
        nav.set_value(reader.current_page + 1)
        self._set_zoom_combo(reader.zoom)
        self._reader_strip.set_fit_mode(reader.fit_mode)

    def _on_close_tab(self, index: int) -> None:
        if self._documents.close_document(index):
            self._refresh_tab_bar()

    def _on_close_other_tabs(self, index: int) -> None:
        if self._documents.close_others(index):
            self._refresh_tab_bar()

    def _on_close_all_tabs(self) -> None:
        if self._documents.close_all():
            self._refresh_tab_bar()

    def _on_file_dropped_on_tab(self, index: int, path: object) -> None:
        self._open_path(Path(path), replace_index=index)

    def _confirm_close_tab(self, state: DocumentState) -> str | None:
        if not state.page_manager.is_dirty:
            return None
        choice = ask_save_discard_cancel(
            self,
            tr("save_changes_before_closing"),
        )
        if choice == "cancel":
            return "cancel"
        if choice == "save":
            if not self._save_document_state(state):
                return "cancel"
        return "discard"

    def _confirm_close_all(self) -> bool:
        while self._documents.tab_count():
            index = self._documents.tab_count() - 1
            state = self._documents.tab_at(index)
            if state is not None and state.page_manager.is_dirty:
                choice = self._confirm_close_tab(state)
                if choice == "cancel":
                    return False
            if not self._documents.close_document(index, confirm=False):
                return False
        return True

    def _save_document_state(
        self, state: DocumentState, *, path: Path | None = None
    ) -> bool:
        if self._engine is None:
            return False
        target = path or state.file_path
        try:
            self._engine.save(state.document, target, garbage=4)
        except DocumentSaveError as exc:
            show_critical(self, tr("msg_save_failed").replace("{detail}", str(exc)))
            return False
        if path is not None:
            state.file_path = path
            state.document.path = path
        state.page_manager.reset_dirty()
        index = self._documents.find_index_by_path(target)
        if index is not None:
            self._tab_bar.update_tab_text(index, self._documents.tab_label(index))
        self._update_window_title()
        self._update_doc_dependent_actions()
        self._show_status(tr("status_saved").replace("{filename}", target.name))
        return True

    def retranslate_ui(self) -> None:
        """Refresh menus, toolbar, and status text for the active language."""
        if hasattr(self, "_file_menu"):
            self._file_menu.setTitle("&" + tr("file"))
        if hasattr(self, "_view_menu"):
            self._view_menu.setTitle("&" + tr("view"))
        if hasattr(self, "_tools_menu"):
            self._tools_menu.setTitle("&" + tr("tools"))
        if hasattr(self, "_pdf_menu"):
            self._pdf_menu.setTitle("&" + tr("pdf"))
        if hasattr(self, "_options_menu"):
            self._options_menu.setTitle("&" + tr("options"))
        if hasattr(self, "_help_menu"):
            self._help_menu.setTitle("&" + tr("help"))
        if self._action_open is not None:
            self._action_open.setText("&" + tr("open_ellipsis"))
        if self._action_save is not None:
            self._action_save.setText("&" + tr("save"))
        if self._action_save_as is not None:
            self._action_save_as.setText(tr("save_as"))
        if self._recent_menu is not None:
            self._recent_menu.setTitle("&" + tr("recent_files"))
        if self._action_exit is not None:
            self._action_exit.setText("&" + tr("exit"))
        if self._action_zoom_in is not None:
            self._action_zoom_in.setText("&" + tr("zoom_in"))
        if self._action_zoom_out is not None:
            self._action_zoom_out.setText("&" + tr("zoom_out"))
        if self._action_fit_width is not None:
            self._action_fit_width.setText(tr("fit_width"))
        if self._action_fit_page is not None:
            self._action_fit_page.setText(tr("fit_page"))
        if self._action_next_page is not None:
            self._action_next_page.setText("&" + tr("next_page"))
        if self._action_previous_page is not None:
            self._action_previous_page.setText("&" + tr("previous_page"))
        if self._action_ocr is not None:
            self._action_ocr.setText(tr("ocr_title"))
            if not self._action_ocr.isEnabled():
                self._action_ocr.setToolTip(tr("ocr_requires_open_document"))
        if self._action_split_pdf is not None:
            self._action_split_pdf.setText(tr("split_pdf_title"))
        if self._action_merge_pdf is not None:
            self._action_merge_pdf.setText(tr("merge_pdf_title"))
        if self._action_general_settings is not None:
            self._action_general_settings.setText(tr("general_settings"))
        if self._action_view_settings is not None:
            self._action_view_settings.setText(tr("view_settings"))
        if self._action_advanced_options is not None:
            self._action_advanced_options.setText(tr("advanced"))
        if self._action_reset_defaults is not None:
            self._action_reset_defaults.setText(tr("reset_defaults"))
        if self._action_encrypted_pdf is not None:
            self._action_encrypted_pdf.setText(tr("encrypted_pdf"))
        if self._action_p7m_files is not None:
            self._action_p7m_files.setText(tr("p7m_files"))
        if self._action_missing_fonts is not None:
            self._action_missing_fonts.setText(tr("missing_fonts"))
        if self._action_about is not None:
            self._action_about.setText(tr("about_freepdf_suite"))
        if self._action_documentation is not None:
            self._action_documentation.setText(tr("documentation"))
        if hasattr(self, "_nav"):
            self._nav.retranslate_ui()
        if hasattr(self, "_reader_strip"):
            self._reader_strip.retranslate_ui()
        reader = self._active_reader()
        if reader is not None:
            reader.retranslate_ui()
        elif hasattr(self, "_documents"):
            self._documents.empty_reader.retranslate_ui()
        if hasattr(self, "_thumb_panel"):
            self._thumb_panel.retranslate_ui()
        self._update_window_title()
        if not self._doc_open:
            self._show_status(self._ready_message(), flash=False)

    def _build_floating_layout(self) -> None:
        """Compose the dashboard-style floating card shell."""
        central = QWidget(self)
        central.setObjectName("appCanvas")
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        nav_row = QHBoxLayout()
        nav_row.setContentsMargins(12, 12, 12, 0)
        self._nav_card = FloatingCard("navCard", padding=16)
        nav_row.addWidget(self._nav_card)
        root.addLayout(nav_row)

        tab_row = QHBoxLayout()
        tab_row.setContentsMargins(8, 0, 8, 0)
        self._tab_card = FloatingCard("documentTabCard", padding=8)
        self._tab_card.set_content(self._tab_bar)
        tab_row.addWidget(self._tab_card)
        root.addLayout(tab_row)

        strip_row = QHBoxLayout()
        strip_row.setContentsMargins(8, 0, 8, 0)
        self._strip_card = FloatingCard("readerStripCard", padding=16)
        strip_row.addWidget(self._strip_card)
        root.addLayout(strip_row)

        content_row = QHBoxLayout()
        content_row.setContentsMargins(12, 0, 12, 12)
        content_row.setSpacing(10)

        self._thumb_card = FloatingCard("thumbnailCard", padding=16)
        self._thumb_panel.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Expanding,
        )
        self._thumb_card.set_content(self._thumb_panel, stretch=1)

        self._viewer_card = FloatingCard("viewerCard", padding=16)
        self._viewer_card.set_content(self._documents.stack, stretch=1)

        content_row.addWidget(self._thumb_card)
        content_row.addWidget(self._viewer_card, 1)
        root.addLayout(content_row, 1)

        self.setCentralWidget(central)

        self._strip_card.set_content(self._reader_strip)

    def _setup_nav_bar(self) -> None:
        """Create the top navigation bar inside its floating card."""
        self._nav = TopNavBar(
            self, logo_path=LOGO_PATH if LOGO_PATH.is_file() else None
        )
        self._nav_card.set_content(self._nav)

        self._nav.file_clicked.connect(
            lambda: self._popup_menu(self._file_menu, self._nav.file_tab)
        )
        self._nav.view_clicked.connect(
            lambda: self._popup_menu(self._view_menu, self._nav.view_tab)
        )
        self._nav.tools_clicked.connect(
            lambda: self._popup_menu(self._tools_menu, self._nav.tools_tab)
        )
        self._nav.pdf_clicked.connect(
            lambda: self._popup_menu(self._pdf_menu, self._nav.pdf_tab)
        )
        self._nav.options_clicked.connect(
            lambda: self._popup_menu(self._options_menu, self._nav.options_tab)
        )
        self._nav.help_clicked.connect(
            lambda: self._popup_menu(self._help_menu, self._nav.help_tab)
        )

        self._search_bar = self._nav.search_bar
        self._search_bar.returnPressed.connect(self._on_search)

    def _wire_reader_strip(self) -> None:
        self._reader_strip.open_clicked.connect(self._on_open)
        self._reader_strip.page_changed.connect(self._on_page_indicator_changed)
        self._reader_strip.zoom_changed.connect(self._on_strip_zoom_changed)
        self._reader_strip.fit_width_clicked.connect(self._on_strip_fit_width)
        self._reader_strip.fit_page_clicked.connect(self._on_strip_fit_page)
        default_zoom = float(self._config.get("zoom_default", 1.0))
        self._set_zoom_combo(default_zoom)

    def _on_strip_zoom_changed(self, zoom: float) -> None:
        reader = self._active_reader()
        if reader is not None:
            reader.set_zoom(zoom)

    def _on_strip_fit_width(self) -> None:
        reader = self._active_reader()
        if reader is not None:
            reader.fit_width()
            self._reader_strip.set_fit_mode(reader.fit_mode)

    def _on_strip_fit_page(self) -> None:
        reader = self._active_reader()
        if reader is not None:
            reader.fit_page()
            self._reader_strip.set_fit_mode(reader.fit_mode)

    def _popup_menu(self, menu: QMenu, tab) -> None:  # noqa: ANN001
        self._nav.show_menu_tab(tab)
        anchor = tab.mapToGlobal(tab.rect().bottomLeft())
        menu.exec(anchor)
        self._nav.hide_menu_tab()

    def _build_menus(self) -> None:
        self._file_menu = QMenu("&" + tr("file"), self)
        self._action_open = self._file_menu.addAction(
            "&" + tr("open_ellipsis"),
            self._on_open,
            QKeySequence.StandardKey.Open,
        )
        self._recent_menu = self._file_menu.addMenu("&" + tr("recent_files"))
        self._refresh_recent_menu()
        self._action_save = self._file_menu.addAction(
            "&" + tr("save"),
            self._on_save,
            QKeySequence.StandardKey.Save,
        )
        self._action_save_as = self._file_menu.addAction(
            tr("save_as"),
            self._on_save_as,
            QKeySequence("Ctrl+Shift+S"),
        )
        self._file_menu.addSeparator()
        self._action_exit = self._file_menu.addAction(
            "&" + tr("exit"),
            self.close,
            QKeySequence("Ctrl+Q"),
        )

        self._view_menu = QMenu("&" + tr("view"), self)
        self._action_zoom_in = self._view_menu.addAction(
            "&" + tr("zoom_in"),
            self._zoom_in_active,
            QKeySequence.StandardKey.ZoomIn,
        )
        self._action_zoom_out = self._view_menu.addAction(
            "&" + tr("zoom_out"),
            self._zoom_out_active,
            QKeySequence.StandardKey.ZoomOut,
        )
        self._action_fit_width = self._view_menu.addAction(
            tr("fit_width"),
            self._on_strip_fit_width,
        )
        self._action_fit_page = self._view_menu.addAction(
            tr("fit_page"),
            self._on_strip_fit_page,
        )
        self._view_menu.addSeparator()
        self._action_next_page = self._view_menu.addAction(
            "&" + tr("next_page"),
            self._next_page_active,
            QKeySequence("PgDown"),
        )
        self._action_previous_page = self._view_menu.addAction(
            "&" + tr("previous_page"),
            self._previous_page_active,
            QKeySequence("PgUp"),
        )

        self._tools_menu = QMenu("&" + tr("tools"), self)
        self._action_ocr = QAction(tr("ocr_title"), self)
        self._action_ocr.setEnabled(False)
        self._action_ocr.setToolTip(tr("ocr_requires_open_document"))
        self._action_ocr.triggered.connect(self._on_ocr)
        self._tools_menu.addAction(self._action_ocr)
        self._tools_menu.addSeparator()
        self._action_split_pdf = QAction(tr("split_pdf_title"), self)
        self._action_split_pdf.setEnabled(False)
        self._action_split_pdf.triggered.connect(self._on_split_pdf)
        self._tools_menu.addAction(self._action_split_pdf)
        self._action_merge_pdf = QAction(tr("merge_pdf_title"), self)
        self._action_merge_pdf.triggered.connect(self._on_merge_pdf)
        self._tools_menu.addAction(self._action_merge_pdf)

        self._pdf_menu = QMenu("&" + tr("pdf"), self)
        self._action_encrypted_pdf = self._pdf_menu.addAction(
            tr("encrypted_pdf"),
            lambda: show_options(self, initial_tab=2),
        )
        self._action_p7m_files = self._pdf_menu.addAction(
            tr("p7m_files"),
            lambda: show_options(self, initial_tab=2),
        )
        self._action_missing_fonts = self._pdf_menu.addAction(
            tr("missing_fonts"),
            lambda: show_options(self, initial_tab=2),
        )

        self._options_menu = QMenu("&" + tr("options"), self)
        self._action_general_settings = self._options_menu.addAction(
            tr("general_settings"),
            lambda: show_general_settings(self),
        )
        self._action_view_settings = self._options_menu.addAction(
            tr("view_settings"),
            lambda: show_view_settings(self),
        )
        self._action_advanced_options = self._options_menu.addAction(
            tr("advanced"),
            lambda: show_options(self, initial_tab=3),
        )
        self._options_menu.addSeparator()
        self._action_reset_defaults = self._options_menu.addAction(
            tr("reset_defaults"),
            lambda: confirm_reset_defaults(self),
        )

        self._help_menu = QMenu("&" + tr("help"), self)
        self._action_about = self._help_menu.addAction(
            tr("about_freepdf_suite"),
            lambda: show_about(self),
        )
        self._action_documentation = QAction(tr("documentation"), self)
        self._action_documentation.setEnabled(False)
        self._help_menu.addAction(self._action_documentation)

        menu_bar = self.menuBar()
        menu_bar.addMenu(self._file_menu)
        menu_bar.addMenu(self._view_menu)
        menu_bar.addMenu(self._tools_menu)
        menu_bar.addMenu(self._pdf_menu)
        menu_bar.addMenu(self._options_menu)
        menu_bar.addMenu(self._help_menu)
        menu_bar.setVisible(False)
        self._attach_menu_popup_shadows()

    def _attach_menu_popup_shadows(self) -> None:
        """Deep shadow on nav dropdown menus when they open."""
        for menu in (
            self._file_menu,
            self._view_menu,
            self._tools_menu,
            self._pdf_menu,
            self._options_menu,
            self._help_menu,
        ):
            menu.aboutToShow.connect(
                lambda _checked=False, bound=menu: QTimer.singleShot(
                    0, lambda: popup_shadow(bound)
                )
            )

    def _build_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+F"), self, self._search_bar.setFocus)
        QShortcut(QKeySequence("F3"), self, self._on_find_next)
        QShortcut(QKeySequence("Shift+F3"), self, self._on_find_previous)
        QShortcut(QKeySequence("Ctrl+W"), self, self._close_active_tab)
        QShortcut(QKeySequence("Ctrl+Tab"), self, self._next_tab)
        QShortcut(QKeySequence("Ctrl+Shift+Tab"), self, self._previous_tab)
        for number in range(1, 10):
            QShortcut(
                QKeySequence(f"Ctrl+{number}"),
                self,
                lambda index=number - 1: self._switch_to_tab_index(index),
            )

    def _zoom_in_active(self) -> None:
        reader = self._active_reader()
        if reader is not None:
            reader.zoom_in()

    def _zoom_out_active(self) -> None:
        reader = self._active_reader()
        if reader is not None:
            reader.zoom_out()

    def _next_page_active(self) -> None:
        reader = self._active_reader()
        if reader is not None:
            reader.next_page()

    def _previous_page_active(self) -> None:
        reader = self._active_reader()
        if reader is not None:
            reader.previous_page()

    def _close_active_tab(self) -> None:
        index = self._documents.active_index
        if index >= 0:
            self._on_close_tab(index)

    def _next_tab(self) -> None:
        count = self._documents.tab_count()
        if count <= 1:
            return
        index = (self._documents.active_index + 1) % count
        self._documents.switch_to(index)

    def _previous_tab(self) -> None:
        count = self._documents.tab_count()
        if count <= 1:
            return
        index = (self._documents.active_index - 1) % count
        self._documents.switch_to(index)

    def _switch_to_tab_index(self, index: int) -> None:
        if 0 <= index < self._documents.tab_count():
            self._documents.switch_to(index)

    def _save_document(self, *, path: Path | None = None) -> bool:
        state = self._active_state()
        if state is None:
            return False
        return self._save_document_state(state, path=path)

    def _on_save(self) -> None:
        state = self._active_state()
        if state is None or not state.page_manager.is_dirty:
            return
        self._save_document()

    def _on_save_as(self) -> None:
        state = self._active_state()
        if state is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("save_as"),
            str(state.file_path),
            "PDF (*.pdf)",
        )
        if path:
            self._save_document(path=Path(path))

    def _after_page_structure_change(self, current_page: int | None = None) -> None:
        reader = self._active_reader()
        if reader is None:
            return
        reader.reload_document(current_page=current_page)
        self._sync_thumbnail_panel()
        self._update_page_controls()
        self._documents.mark_dirty()
        self._refresh_tab_bar()
        self._update_window_title()
        self._update_doc_dependent_actions()

    def _on_pages_reordered(self, from_row: int, to_row: int) -> None:
        state = self._active_state()
        reader = self._active_reader()
        if state is None or reader is None:
            return
        current = reader.current_page
        try:
            state.page_manager.move_page(state.document, from_row, to_row)
        except PageIndexError as exc:
            show_critical(self, str(exc))
            self._sync_thumbnail_panel()
            return
        if current == from_row:
            new_current = to_row
        elif from_row < current <= to_row:
            new_current = current - 1
        elif to_row <= current < from_row:
            new_current = current + 1
        else:
            new_current = current
        self._after_page_structure_change(new_current)

    def _on_rotate_page(self, page_index: int, degrees: int) -> None:
        state = self._active_state()
        reader = self._active_reader()
        if state is None or reader is None:
            return
        try:
            state.page_manager.rotate_page(state.document, page_index, degrees)
        except PageIndexError as exc:
            show_critical(self, str(exc))
            return
        reader.refresh_page_view(page_index=page_index)
        self._sync_thumbnail_panel()
        self._documents.mark_dirty()
        self._refresh_tab_bar()
        self._update_window_title()

    def _on_delete_page(self, page_index: int) -> None:
        state = self._active_state()
        reader = self._active_reader()
        if state is None or reader is None:
            return
        if reader.page_count <= 1:
            show_warning(self, tr("page_delete_last_blocked"))
            return
        if not ask_yes_no(
            self,
            tr("page_delete_confirm").replace("{page}", str(page_index + 1)),
        ):
            return
        current = reader.current_page
        try:
            state.page_manager.delete_page(state.document, page_index)
        except PageIndexError as exc:
            show_critical(self, str(exc))
            return
        new_current = (
            min(current, reader.page_count - 1) if current >= page_index else current
        )
        self._after_page_structure_change(new_current)

    def _on_insert_pages(self, at_index: int) -> None:
        state = self._active_state()
        reader = self._active_reader()
        if state is None or reader is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("page_insert_here"),
            "",
            "PDF (*.pdf);;All files (*)",
        )
        if not path:
            return
        current = reader.current_page
        try:
            state.page_manager.insert_pages_from_file(
                state.document, at_index, Path(path)
            )
        except (DocumentOpenError, PageIndexError) as exc:
            show_critical(self, str(exc))
            return
        if current >= at_index:
            current += 1
        self._after_page_structure_change(current)

    def _on_split_pdf(self) -> None:
        state = self._active_state()
        if state is None:
            return
        show_split_pdf_dialog(
            self,
            page_manager=state.page_manager,
            engine=self._engine,
            doc=state.document,
        )

    def _on_merge_pdf(self) -> None:
        state = self._active_state()
        if state is None:
            show_merge_pdf_dialog(
                self,
                page_manager=PageManager(self._engine),
                on_open_result=lambda path: self._open_path(path),
            )
            return
        show_merge_pdf_dialog(
            self,
            page_manager=state.page_manager,
            on_open_result=lambda path: self._open_path(path),
        )

    def _on_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("open_pdf_dialog_title"),
            "",
            "PDF & signed (*.pdf *.p7m *.pdf.p7m);;All files (*)",
        )
        if path:
            self._open_path(Path(path))

    def _friendly_open_error(
        self, exc: Exception, path: Path, *, had_password: bool
    ) -> str:
        code = getattr(exc, "error_code", "")
        if code == "ENCRYPTED_DOCUMENT_ERROR" and had_password:
            return tr("msg_wrong_password")
        if code == "P7M_EXTRACTION_ERROR":
            return tr("msg_p7m_failed")
        if code in ("DOCUMENT_OPEN_ERROR", "UNSUPPORTED_FORMAT_ERROR", "FORMAT_ERROR"):
            return tr("msg_cannot_open_file").replace("{filename}", path.name)
        return tr("msg_open_failed_generic")

    def _open_path(
        self,
        path: Path,
        password: str | None = None,
        *,
        is_temp: bool = False,
        replace_index: int | None = None,
    ) -> None:
        if self._engine is None:
            show_warning(self, tr("msg_engine_unavailable"))
            return

        existing = self._documents.find_index_by_path(path)
        if existing is not None and replace_index is None:
            self._documents.switch_to(existing)
            return

        try:
            document = self._engine.open(path, password=password)
        except Exception as exc:
            if self._is_encrypted_error(exc) and password is None:
                pwd, ok = QInputDialog.getText(
                    self,
                    tr("app_title"),
                    tr("password_prompt").replace("{filename}", path.name),
                    QLineEdit.EchoMode.Password,
                )
                if ok and pwd:
                    self._open_path(
                        path,
                        password=pwd,
                        is_temp=is_temp,
                        replace_index=replace_index,
                    )
                return
            show_critical(
                self,
                self._friendly_open_error(exc, path, had_password=password is not None),
            )
            return

        if replace_index is not None:
            self._documents.replace_document_at(
                replace_index,
                document,
                path,
                is_temp=is_temp,
            )
        else:
            self._documents.open_document(document, path, is_temp=is_temp)

        self._doc_open = self._documents.tab_count() > 0
        self._refresh_tab_bar()
        self._sync_toolbar_to_active()
        self._update_page_controls()
        self._update_window_title()
        title = path.name
        if getattr(document, "format", None) is not None:
            fmt = getattr(document.format, "value", str(document.format))
            if fmt == "p7m":
                title += " (P7M extracted)"
        self._show_status(tr("status_opened").replace("{filename}", title))
        if not is_temp:
            self._recent.add(path)
            self._refresh_recent_menu()
        self._update_doc_dependent_actions()

    def _pdf_bytes_for_ocr(self) -> bytes | None:
        """Return in-memory PDF bytes for OCR when the open document is not a plain file."""
        state = self._active_state()
        if state is None:
            return None
        handle = getattr(state.document, "_handle", None)
        if handle is None:
            return None
        try:
            return handle.tobytes()
        except Exception:
            return None

    def _on_ocr(self) -> None:
        state = self._active_state()
        if not self._doc_open or state is None:
            show_warning(self, tr("ocr_requires_open_document"))
            return
        if self._ocr_worker is not None and self._ocr_worker.isRunning():
            return
        if not check_tesseract_available():
            show_critical(self, tr("ocr_not_bundled"))
            return

        self._action_ocr.setEnabled(False)
        self._begin_ocr_progress(0, 1)

        render_dpi = int(self._config.get("render_dpi", DEFAULT_OCR_DPI))
        self._ocr_worker = _OcrWorker(
            pdf_path=state.file_path,
            pdf_bytes=self._pdf_bytes_for_ocr(),
            dpi=render_dpi,
        )
        self._ocr_worker.progress.connect(self._on_ocr_progress)
        self._ocr_worker.succeeded.connect(self._on_ocr_succeeded)
        self._ocr_worker.failed.connect(self._on_ocr_failed)
        self._ocr_worker.finished.connect(self._on_ocr_finished)
        self._ocr_worker.start()

    def _on_ocr_progress(self, current: int, total: int) -> None:
        self._begin_ocr_progress(current, total)

    def _begin_ocr_progress(self, current: int, total: int) -> None:
        maximum = max(1, total)
        value = min(current, maximum)
        percent = int(round(100 * value / maximum))
        message = (
            tr("ocr_status_running")
            .replace("{current}", str(current))
            .replace("{total}", str(total))
        )
        self._show_status(message, flash=False)
        self._ocr_status_progress.setMaximum(maximum)
        self._ocr_status_progress.setValue(value)
        self._ocr_status_progress.setFormat(f"{percent}%")
        self._ocr_status_progress.show()
        reader = self._active_reader()
        if reader is not None:
            reader.show_ocr_progress(current, total)

    def _end_ocr_progress(self) -> None:
        self._ocr_status_progress.hide()
        reader = self._active_reader()
        if reader is not None:
            reader.hide_ocr_progress()

    def _on_ocr_succeeded(self, output_path: object) -> None:
        self._end_ocr_progress()
        path = Path(output_path)
        if self._engine is None:
            return
        try:
            document = self._engine.open(path)
        except Exception as exc:
            show_critical(
                self,
                self._friendly_open_error(exc, path, had_password=False),
            )
            return
        self._documents.replace_current(document, path, is_temp=True)
        self._doc_open = self._documents.tab_count() > 0
        self._refresh_tab_bar()
        self._sync_thumbnail_panel()
        self._sync_toolbar_to_active()
        self._update_page_controls()
        self._update_window_title()
        self._update_doc_dependent_actions()
        self._show_status(tr("ocr_status_completed"), flash=True)

    def _on_ocr_failed(self, _message: str) -> None:
        self._end_ocr_progress()
        show_critical(self, tr("ocr_error_generic"))

    def _on_ocr_finished(self) -> None:
        self._end_ocr_progress()
        self._update_doc_dependent_actions()

    def _update_doc_dependent_actions(self) -> None:
        state = self._active_state()
        enabled = self._doc_open and state is not None
        dirty = state is not None and state.page_manager.is_dirty
        if self._action_ocr is not None:
            self._action_ocr.setEnabled(enabled)
            self._action_ocr.setToolTip(
                "" if enabled else tr("ocr_requires_open_document")
            )
        if self._action_split_pdf is not None:
            self._action_split_pdf.setEnabled(enabled)
        if self._action_save is not None:
            self._action_save.setEnabled(enabled and dirty)
        if self._action_save_as is not None:
            self._action_save_as.setEnabled(enabled)

    def _refresh_recent_menu(self) -> None:
        if self._recent_menu is None:
            return
        self._recent_menu.clear()
        paths = self._recent.paths()
        if not paths:
            empty = self._recent_menu.addAction(tr("recent_files_none"))
            empty.setEnabled(False)
            return
        for path in paths:
            action = self._recent_menu.addAction(path.name)
            action.setToolTip(str(path))
            action.triggered.connect(
                lambda _checked=False, chosen=path: self._open_path(chosen)
            )

    def _on_page_changed(self, page_index: int) -> None:
        if self.sender() is not self._active_reader():
            return
        self._reader_strip.page_navigator.set_value(page_index + 1)
        self._thumb_panel.set_current_page(page_index)

    def _on_page_indicator_changed(self, one_based: int) -> None:
        reader = self._active_reader()
        if reader is not None:
            reader.go_to_page(one_based - 1)

    def _update_page_controls(self) -> None:
        reader = self._active_reader()
        count = reader.page_count if reader is not None else 0
        nav = self._reader_strip.page_navigator
        nav.set_range(max(1, count))
        if count > 0 and reader is not None:
            nav.set_value(min(nav.value(), count))
        nav.set_nav_enabled(count > 1)

    def _set_zoom_combo(self, zoom: float) -> None:
        combo = self._reader_strip.zoom_combo
        combo.blockSignals(True)
        closest = min(range(combo.count()), key=lambda i: abs(combo.itemData(i) - zoom))
        combo.setCurrentIndex(closest)
        combo.blockSignals(False)

    def _on_search(self) -> None:
        reader = self._active_reader()
        if reader is None:
            return
        query = self._search_bar.text()
        count = reader.find_text(query)
        if not query.strip():
            self._show_status(tr("status_search_cleared"))
        elif count == 0:
            self._show_status(tr("status_no_matches").replace("{query}", query))
        else:
            self._show_status(
                tr("status_matches")
                .replace("{count}", str(count))
                .replace("{query}", query)
            )
        self._update_page_controls()

    def _on_find_next(self) -> None:
        reader = self._active_reader()
        if reader is not None and reader.find_next():
            self._show_status(tr("status_next_match"))
            self._update_page_controls()

    def _on_find_previous(self) -> None:
        reader = self._active_reader()
        if reader is not None and reader.find_previous():
            self._show_status(tr("status_prev_match"))
            self._update_page_controls()

    def _show_status(self, message: str, *, flash: bool = True) -> None:
        show_status_message(self.statusBar(), message, flash=flash)

    @staticmethod
    def _is_encrypted_error(exc: Exception) -> bool:
        code = getattr(exc, "error_code", "")
        if code == "ENCRYPTED_DOCUMENT_ERROR":
            return True
        return "password" in str(exc).lower()
