"""Main application window: PDF reader shell."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QDragEnterEvent, QDragMoveEvent, QDropEvent, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QMainWindow,
    QMenu,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .bootstrap import LOGO_PATH, load_backend
from .config_loader import load_app_config, recent_files_path
from .file_drop import accept_file_drag, enable_file_drops, path_from_drop
from .floating_card import FloatingCard
from .i18n import register_retranslate, tr
from .message_boxes import show_critical, show_warning
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
from .toolbar_widgets import ReaderToolStrip, TopNavBar
from .visual_effects import popup_shadow

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


class MainWindow(QMainWindow):
    def __init__(self, *, initial_path: Path | None = None) -> None:
        super().__init__()
        self._open_filename: str | None = None
        self._update_window_title()
        self.resize(1200, 850)
        if LOGO_PATH.is_file():
            self.setWindowIcon(QIcon(str(LOGO_PATH)))
        enable_file_drops(self)

        self._config = load_app_config()
        self._backend = load_backend()
        self._engine = self._make_engine()
        self._doc: Any = None
        self._recent = RecentFilesStore(
            recent_files_path(),
            limit=int(self._config.get("recent_files_limit", 10)),
        )
        self._recent_menu: QMenu | None = None
        self._action_open: QAction | None = None
        self._action_exit: QAction | None = None
        self._action_zoom_in: QAction | None = None
        self._action_zoom_out: QAction | None = None
        self._modules_placeholder: QAction | None = None
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
        self._unregister_i18n = register_retranslate(self.retranslate_ui)

        self._reader = PdfReaderWidget(self._config, self)
        self._reader.attach_engine(self._engine)
        self._reader.page_changed.connect(self._on_page_changed)
        self._reader.open_file_requested.connect(self._on_open)
        self._reader.file_dropped.connect(self._open_path)

        self._reader_strip = ReaderToolStrip(ZOOM_PRESETS, self)
        self._wire_reader_strip()

        self._build_menus()
        self._build_floating_layout()
        self._setup_nav_bar()
        self._build_shortcuts()
        self._update_page_controls()
        status = self.statusBar()
        status.setObjectName("appStatusBar")
        self._show_status(self._ready_message(), flash=False)

        if initial_path is not None:
            self._open_path(initial_path)

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
        if self._open_filename:
            self.setWindowTitle(f"{self._open_filename} — {tr('app_title')}")
        else:
            self.setWindowTitle(tr("app_title"))

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
        if self._modules_placeholder is not None:
            self._modules_placeholder.setText(tr("no_modules_installed"))
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
        if hasattr(self, "_reader"):
            self._reader.retranslate_ui()
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

        strip_row = QHBoxLayout()
        strip_row.setContentsMargins(8, 0, 8, 0)
        self._strip_card = FloatingCard("readerStripCard", padding=16)
        strip_row.addWidget(self._strip_card)
        root.addLayout(strip_row)

        content_row = QHBoxLayout()
        content_row.setContentsMargins(12, 0, 12, 12)
        content_row.setSpacing(10)

        self._thumb_card = FloatingCard("thumbnailCard", padding=16)
        self._thumb_panel = self._reader.thumbnail_panel
        self._thumb_panel.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Expanding,
        )
        self._thumb_card.set_content(self._thumb_panel, stretch=1)

        self._viewer_card = FloatingCard("viewerCard", padding=16)
        self._viewer_card.set_content(self._reader, stretch=1)

        content_row.addWidget(self._thumb_card)
        content_row.addWidget(self._viewer_card, 1)
        root.addLayout(content_row, 1)

        self.setCentralWidget(central)

        self._strip_card.set_content(self._reader_strip)

    def _setup_nav_bar(self) -> None:
        """Create the top navigation bar inside its floating card."""
        self._nav = TopNavBar(self, logo_path=LOGO_PATH if LOGO_PATH.is_file() else None)
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
        self._reader_strip.zoom_changed.connect(self._reader.set_zoom)
        self._reader_strip.fit_width_clicked.connect(self._reader.fit_width)
        self._reader_strip.fit_page_clicked.connect(self._reader.fit_page)
        self._reader.fit_mode_changed.connect(self._reader_strip.set_fit_mode)
        default_zoom = float(self._config.get("zoom_default", 1.0))
        self._set_zoom_combo(default_zoom)

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
        self._file_menu.addSeparator()
        self._action_exit = self._file_menu.addAction(
            "&" + tr("exit"),
            self.close,
            QKeySequence("Ctrl+Q"),
        )

        self._view_menu = QMenu("&" + tr("view"), self)
        self._action_zoom_in = self._view_menu.addAction(
            "&" + tr("zoom_in"),
            self._reader.zoom_in,
            QKeySequence.StandardKey.ZoomIn,
        )
        self._action_zoom_out = self._view_menu.addAction(
            "&" + tr("zoom_out"),
            self._reader.zoom_out,
            QKeySequence.StandardKey.ZoomOut,
        )
        self._action_fit_width = self._view_menu.addAction(
            tr("fit_width"),
            self._reader.fit_width,
        )
        self._action_fit_page = self._view_menu.addAction(
            tr("fit_page"),
            self._reader.fit_page,
        )
        self._view_menu.addSeparator()
        self._action_next_page = self._view_menu.addAction(
            "&" + tr("next_page"),
            self._reader.next_page,
            QKeySequence("PgDown"),
        )
        self._action_previous_page = self._view_menu.addAction(
            "&" + tr("previous_page"),
            self._reader.previous_page,
            QKeySequence("PgUp"),
        )

        self._tools_menu = QMenu("&" + tr("tools"), self)
        self._modules_placeholder = QAction(tr("no_modules_installed"), self)
        self._modules_placeholder.setEnabled(False)
        self._tools_menu.addAction(self._modules_placeholder)

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
                lambda _checked=False, bound=menu: QTimer.singleShot(0, lambda: popup_shadow(bound))
            )

    def _build_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+F"), self, self._search_bar.setFocus)
        QShortcut(QKeySequence("F3"), self, self._on_find_next)
        QShortcut(QKeySequence("Shift+F3"), self, self._on_find_previous)

    def _on_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("open_pdf_dialog_title"),
            "",
            "PDF & signed (*.pdf *.p7m *.pdf.p7m);;All files (*)",
        )
        if path:
            self._open_path(Path(path))

    def _friendly_open_error(self, exc: Exception, path: Path, *, had_password: bool) -> str:
        code = getattr(exc, "error_code", "")
        if code == "ENCRYPTED_DOCUMENT_ERROR" and had_password:
            return tr("msg_wrong_password")
        if code == "P7M_EXTRACTION_ERROR":
            return tr("msg_p7m_failed")
        if code in ("DOCUMENT_OPEN_ERROR", "UNSUPPORTED_FORMAT_ERROR", "FORMAT_ERROR"):
            return tr("msg_cannot_open_file").replace("{filename}", path.name)
        return tr("msg_open_failed_generic")

    def _open_path(self, path: Path, password: str | None = None) -> None:
        if self._engine is None:
            show_warning(self, tr("msg_engine_unavailable"))
            return
        if self._doc is not None:
            try:
                self._engine.close(self._doc)
            except Exception:
                pass
            self._doc = None

        try:
            self._doc = self._engine.open(path, password=password)
        except Exception as exc:
            if self._is_encrypted_error(exc) and password is None:
                pwd, ok = QInputDialog.getText(
                    self,
                    tr("app_title"),
                    tr("password_prompt").replace("{filename}", path.name),
                    QLineEdit.EchoMode.Password,
                )
                if ok and pwd:
                    self._open_path(path, password=pwd)
                return
            show_critical(self, self._friendly_open_error(exc, path, had_password=password is not None))
            return

        self._reader.show_document(self._doc)
        self._doc_open = True
        self._open_filename = path.name
        self._update_window_title()
        self._update_page_controls()
        self._set_zoom_combo(self._reader.zoom)
        title = path.name
        if getattr(self._doc, "format", None) is not None:
            fmt = getattr(self._doc.format, "value", str(self._doc.format))
            if fmt == "p7m":
                title += " (P7M extracted)"
        self._show_status(tr("status_opened").replace("{filename}", title))
        self._recent.add(path)
        self._refresh_recent_menu()

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
        self._reader_strip.page_navigator.set_value(page_index + 1)

    def _on_page_indicator_changed(self, one_based: int) -> None:
        self._reader.go_to_page(one_based - 1)

    def _update_page_controls(self) -> None:
        count = self._reader.page_count
        nav = self._reader_strip.page_navigator
        nav.set_range(max(1, count))
        if count > 0:
            nav.set_value(min(nav.value(), count))
        nav.set_nav_enabled(count > 1)

    def _set_zoom_combo(self, zoom: float) -> None:
        combo = self._reader_strip.zoom_combo
        combo.blockSignals(True)
        closest = min(range(combo.count()), key=lambda i: abs(combo.itemData(i) - zoom))
        combo.setCurrentIndex(closest)
        combo.blockSignals(False)

    def _on_search(self) -> None:
        query = self._search_bar.text()
        count = self._reader.find_text(query)
        if not query.strip():
            self._show_status(tr("status_search_cleared"))
        elif count == 0:
            self._show_status(tr("status_no_matches").replace("{query}", query))
        else:
            self._show_status(
                tr("status_matches").replace("{count}", str(count)).replace("{query}", query)
            )
        self._update_page_controls()

    def _on_find_next(self) -> None:
        if self._reader.find_next():
            self._show_status(tr("status_next_match"))
            self._update_page_controls()

    def _on_find_previous(self) -> None:
        if self._reader.find_previous():
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
