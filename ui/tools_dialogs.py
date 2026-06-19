"""Settings dialogs opened from the Tools menu."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .bootstrap import LOGO_PATH
from .branding import APP_VERSION
from .config_loader import load_app_config, reset_app_config, save_app_config
from .i18n import apply_language, register_retranslate, tr
from .message_boxes import ask_yes_no, show_information
from .visual_effects import popup_shadow

FORM_LABEL_WIDTH = 140
FIELD_MAX_WIDTH = 180
FIELD_ROW_HEIGHT = 28
FORM_ROW_SPACING = 16

LANGUAGE_OPTIONS: tuple[tuple[str, str], ...] = (
    ("English", "en"),
    ("Italiano", "it"),
    ("Français", "fr"),
    ("Deutsch", "de"),
    ("Español", "es"),
    ("Português", "pt"),
)

THEME_OPTIONS: tuple[tuple[str, str], ...] = (
    ("Dark", "dark"),
    ("Light", "light"),
    ("System", "system"),
)

DEFAULT_ZOOM_OPTIONS: tuple[tuple[str, str], ...] = (
    ("Fit Page", "fit_page"),
    ("Fit Width", "fit_width"),
    ("50%", "0.5"),
    ("75%", "0.75"),
    ("100%", "1.0"),
    ("125%", "1.25"),
    ("150%", "1.5"),
    ("200%", "2.0"),
)

VIEW_MODE_OPTIONS: tuple[tuple[str, str], ...] = (
    ("Single Page", "single_page"),
    ("Continuous Scroll", "continuous_scroll"),
)

RENDER_DPI_OPTIONS: tuple[tuple[str, int], ...] = (
    ("72", 72),
    ("96", 96),
    ("144", 144),
    ("300", 300),
)

ENCRYPTED_PDF_VALUES: tuple[str, ...] = ("always_ask", "remember_password")
P7M_VALUES: tuple[str, ...] = ("always_extract", "ask_confirmation")
MISSING_FONTS_VALUES: tuple[str, ...] = ("use_substitutes", "show_warning")

RENDERING_QUALITY_OPTIONS: tuple[tuple[str, str], ...] = (
    ("Normal", "normal"),
    ("High", "high"),
)


def _create_options_form(tab: QWidget) -> QFormLayout:
    """Build a consistent two-column form layout for options tabs."""
    form = QFormLayout(tab)
    form.setContentsMargins(12, 12, 12, 12)
    form.setSpacing(FORM_ROW_SPACING)
    form.setHorizontalSpacing(12)
    form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)
    form.setFormAlignment(Qt.AlignmentFlag.AlignVCenter)
    return form


def _form_label(text: str, parent: QWidget) -> QLabel:
    """Right-aligned label with a fixed width for the form label column."""
    label = QLabel(text, parent)
    label.setObjectName("settingsFormLabel")
    label.setFixedWidth(FORM_LABEL_WIDTH)
    label.setFixedHeight(FIELD_ROW_HEIGHT)
    label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    return label


def _constrain_field(widget: QWidget, *, max_width: int = FIELD_MAX_WIDTH) -> QWidget:
    """Limit field width so dropdowns do not stretch across the dialog."""
    widget.setMaximumWidth(max_width)
    return widget


def _make_combo(parent: QWidget, *, pdf: bool = False) -> QComboBox:
    """Create a settings combo box with standard width constraints."""
    combo = QComboBox(parent)
    combo.setObjectName("settingsPdfCombo" if pdf else "settingsCombo")
    combo.setFixedHeight(FIELD_ROW_HEIGHT)
    return _constrain_field(combo)  # type: ignore[return-value]


def _make_spinbox(parent: QWidget) -> QSpinBox:
    """Create a settings spin box with standard width constraints."""
    spin = QSpinBox(parent)
    spin.setObjectName("settingsSpinBox")
    spin.setFixedHeight(FIELD_ROW_HEIGHT)
    return _constrain_field(spin)  # type: ignore[return-value]


def _populate_combo(combo: QComboBox, options: tuple[tuple[str, Any], ...]) -> None:
    combo.clear()
    for label, value in options:
        combo.addItem(label, value)


def _populate_translated_combo(combo: QComboBox, keys: tuple[str, ...]) -> None:
    """Fill a combo with translated labels while preserving the selected value."""
    current = combo.currentData()
    combo.clear()
    for key in keys:
        combo.addItem(tr(key), key)
    if current is not None:
        _set_combo_value(combo, current)


def _set_combo_value(combo: QComboBox, value: Any) -> None:
    index = combo.findData(value)
    if index < 0:
        index = combo.findData(str(value))
    combo.setCurrentIndex(max(0, index))


def _combo_value(combo: QComboBox) -> Any:
    return combo.currentData()


class OptionsDialog(QDialog):
    """Tabbed application options editor."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        initial_tab: int = 0,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("optionsDialog")
        self.setFixedSize(520, 420)

        self._previous_language = str(load_app_config().get("language", "en"))

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        self._tabs = QTabWidget(self)
        self._tabs.setObjectName("optionsTabWidget")
        self._tabs.addTab(self._build_general_tab(), tr("general"))
        self._tabs.addTab(self._build_view_tab(), tr("view"))
        self._tabs.addTab(self._build_pdf_tab(), tr("pdf"))
        self._tabs.addTab(self._build_advanced_tab(), tr("advanced"))
        root.addWidget(self._tabs, 1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self._save_button = QPushButton(self)
        self._save_button.setObjectName("settingsSaveButton")
        self._save_button.clicked.connect(self._on_save)
        actions.addWidget(self._save_button)
        root.addLayout(actions)

        self._unregister_i18n = register_retranslate(self.retranslate_ui)
        self.finished.connect(lambda _result: self._unregister_i18n())
        popup_shadow(self)

        self._tabs.setCurrentIndex(max(0, min(initial_tab, self._tabs.count() - 1)))
        self._load_from_config()
        self.retranslate_ui()

    def _build_general_tab(self) -> QWidget:
        tab = QWidget(self)
        form = _create_options_form(tab)

        self._language_combo = _make_combo(tab)
        _populate_combo(self._language_combo, LANGUAGE_OPTIONS)

        self._theme_combo = _make_combo(tab)
        _populate_combo(self._theme_combo, THEME_OPTIONS)

        folder_row = QWidget(tab)
        folder_layout = QHBoxLayout(folder_row)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        folder_layout.setSpacing(8)
        self._default_folder = QLineEdit(folder_row)
        self._default_folder.setObjectName("settingsLineEdit")
        self._browse_folder = QPushButton("Browse", folder_row)
        self._browse_folder.setObjectName("settingsBrowseButton")
        self._browse_folder.clicked.connect(self._browse_default_folder)
        folder_layout.addWidget(self._default_folder, 1)
        folder_layout.addWidget(self._browse_folder)

        self._recent_limit = _make_spinbox(tab)
        self._recent_limit.setRange(5, 50)

        self._open_last_file = QCheckBox("Open last file on startup", tab)
        self._open_last_file.setObjectName("settingsCheckBox")

        form.addRow(_form_label("Application Language", tab), self._language_combo)
        form.addRow(_form_label("Theme", tab), self._theme_combo)
        form.addRow(_form_label("Default folder", tab), folder_row)
        form.addRow(_form_label("Recent files limit", tab), self._recent_limit)
        form.addRow("", self._open_last_file)
        return tab

    def _build_view_tab(self) -> QWidget:
        tab = QWidget(self)
        form = _create_options_form(tab)

        self._default_zoom_combo = _make_combo(tab)
        _populate_combo(self._default_zoom_combo, DEFAULT_ZOOM_OPTIONS)

        self._view_mode_combo = _make_combo(tab)
        _populate_combo(self._view_mode_combo, VIEW_MODE_OPTIONS)

        self._show_thumbnails = QCheckBox("Show thumbnails on startup", tab)
        self._show_thumbnails.setObjectName("settingsCheckBox")

        self._render_dpi_combo = _make_combo(tab)
        _populate_combo(self._render_dpi_combo, RENDER_DPI_OPTIONS)

        form.addRow(_form_label("Default zoom", tab), self._default_zoom_combo)
        form.addRow(_form_label("Default view mode", tab), self._view_mode_combo)
        form.addRow("", self._show_thumbnails)
        form.addRow(_form_label("Render DPI", tab), self._render_dpi_combo)
        return tab

    def _build_pdf_tab(self) -> QWidget:
        tab = QWidget(self)
        form = _create_options_form(tab)

        self._encrypted_pdf_combo = _make_combo(tab, pdf=True)
        _populate_translated_combo(self._encrypted_pdf_combo, ENCRYPTED_PDF_VALUES)

        self._p7m_combo = _make_combo(tab, pdf=True)
        _populate_translated_combo(self._p7m_combo, P7M_VALUES)

        self._missing_fonts_combo = _make_combo(tab, pdf=True)
        _populate_translated_combo(self._missing_fonts_combo, MISSING_FONTS_VALUES)

        self._encrypted_pdf_label = _form_label(tr("encrypted_pdf"), tab)
        self._p7m_label = _form_label(tr("p7m_files"), tab)
        self._missing_fonts_label = _form_label(tr("missing_fonts"), tab)

        form.addRow(self._encrypted_pdf_label, self._encrypted_pdf_combo)
        form.addRow(self._p7m_label, self._p7m_combo)
        form.addRow(self._missing_fonts_label, self._missing_fonts_combo)
        return tab

    def _build_advanced_tab(self) -> QWidget:
        tab = QWidget(self)
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(FORM_ROW_SPACING)

        form_host = QWidget(tab)
        form = _create_options_form(form_host)

        self._prerender_buffer = _make_spinbox(form_host)
        self._prerender_buffer.setRange(1, 10)

        self._rendering_quality_combo = _make_combo(form_host)
        _populate_combo(self._rendering_quality_combo, RENDERING_QUALITY_OPTIONS)

        self._enable_error_log = QCheckBox("Enable error log", form_host)
        self._enable_error_log.setObjectName("settingsCheckBox")

        form.addRow(_form_label("Pre-render buffer pages", form_host), self._prerender_buffer)
        form.addRow(_form_label("Rendering quality", form_host), self._rendering_quality_combo)
        form.addRow("", self._enable_error_log)

        layout.addWidget(form_host)
        layout.addStretch(1)

        self._reset_button = QPushButton(tr("reset_defaults"), tab)
        self._reset_button.setObjectName("settingsResetButton")
        self._reset_button.clicked.connect(self._on_reset_defaults)
        layout.addWidget(self._reset_button, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        return tab

    def retranslate_ui(self) -> None:
        """Refresh dialog labels for the active language."""
        self.setWindowTitle(tr("general_settings"))
        self._save_button.setText(tr("save"))
        self._tabs.setTabText(0, tr("general"))
        self._tabs.setTabText(1, tr("view"))
        self._tabs.setTabText(2, tr("pdf"))
        self._tabs.setTabText(3, tr("advanced"))
        self._reset_button.setText(tr("reset_defaults"))
        self._encrypted_pdf_label.setText(tr("encrypted_pdf"))
        self._p7m_label.setText(tr("p7m_files"))
        self._missing_fonts_label.setText(tr("missing_fonts"))
        _populate_translated_combo(self._encrypted_pdf_combo, ENCRYPTED_PDF_VALUES)
        _populate_translated_combo(self._p7m_combo, P7M_VALUES)
        _populate_translated_combo(self._missing_fonts_combo, MISSING_FONTS_VALUES)

    def _load_from_config(self) -> None:
        config = load_app_config()
        self._previous_language = str(config.get("language", "en"))

        _set_combo_value(self._language_combo, config.get("language", "en"))
        _set_combo_value(self._theme_combo, config.get("theme", "dark"))
        self._default_folder.setText(str(config.get("default_folder", "")))
        self._recent_limit.setValue(int(config.get("recent_files_limit", 10)))
        self._open_last_file.setChecked(bool(config.get("open_last_file_on_startup", False)))

        _set_combo_value(self._default_zoom_combo, str(config.get("default_zoom", "1.0")))
        _set_combo_value(self._view_mode_combo, config.get("default_view_mode", "continuous_scroll"))
        self._show_thumbnails.setChecked(bool(config.get("show_thumbnails_on_startup", True)))
        _set_combo_value(self._render_dpi_combo, int(config.get("render_dpi", 96)))

        _set_combo_value(self._encrypted_pdf_combo, config.get("encrypted_pdf", "always_ask"))
        _set_combo_value(self._p7m_combo, config.get("p7m_files", "always_extract"))
        _set_combo_value(self._missing_fonts_combo, config.get("missing_fonts", "use_substitutes"))

        self._prerender_buffer.setValue(int(config.get("prerender_buffer_pages", 2)))
        _set_combo_value(self._rendering_quality_combo, config.get("rendering_quality", "normal"))
        self._enable_error_log.setChecked(bool(config.get("enable_error_log", False)))

    def _collect_config(self) -> dict[str, Any]:
        default_zoom = str(_combo_value(self._default_zoom_combo))
        updates: dict[str, Any] = {
            "language": str(_combo_value(self._language_combo)),
            "theme": str(_combo_value(self._theme_combo)),
            "default_folder": self._default_folder.text().strip(),
            "recent_files_limit": self._recent_limit.value(),
            "open_last_file_on_startup": self._open_last_file.isChecked(),
            "default_zoom": default_zoom,
            "default_view_mode": str(_combo_value(self._view_mode_combo)),
            "show_thumbnails_on_startup": self._show_thumbnails.isChecked(),
            "render_dpi": int(_combo_value(self._render_dpi_combo)),
            "encrypted_pdf": str(_combo_value(self._encrypted_pdf_combo)),
            "p7m_files": str(_combo_value(self._p7m_combo)),
            "missing_fonts": str(_combo_value(self._missing_fonts_combo)),
            "prerender_buffer_pages": self._prerender_buffer.value(),
            "rendering_quality": str(_combo_value(self._rendering_quality_combo)),
            "enable_error_log": self._enable_error_log.isChecked(),
        }
        if default_zoom not in {"fit_page", "fit_width"}:
            updates["zoom_default"] = float(default_zoom)
        return updates

    def _browse_default_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select default folder")
        if folder:
            self._default_folder.setText(folder)

    def _on_reset_defaults(self) -> None:
        if not confirm_reset_defaults(self):
            return
        self._load_from_config()

    def _on_save(self) -> None:
        updates = self._collect_config()
        save_app_config(updates)
        language = str(updates.get("language", "en"))
        if language != self._previous_language:
            apply_language(language)
            self._previous_language = language
            show_information(self, tr("language_updated"))
        else:
            show_information(self, tr("settings_saved"))


class AboutDialog(QDialog):
    """Branded about box with logo, version, and license details."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("aboutDialog")
        self.setFixedSize(380, 420)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 20)
        root.setSpacing(10)
        root.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self._logo = QLabel(self)
        self._logo.setObjectName("aboutLogo")
        self._logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._logo.setFixedSize(64, 64)
        if LOGO_PATH.is_file():
            pixmap = QPixmap(str(LOGO_PATH)).scaled(
                64,
                64,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._logo.setPixmap(pixmap)
        root.addWidget(self._logo, 0, Qt.AlignmentFlag.AlignHCenter)

        self._title = QLabel(self)
        self._title.setObjectName("aboutTitle")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont(self._title.font())
        title_font.setPixelSize(20)
        title_font.setWeight(QFont.Weight.Bold)
        self._title.setFont(title_font)
        root.addWidget(self._title)

        self._version = QLabel(self)
        self._version.setObjectName("aboutVersion")
        self._version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._version)

        self._tagline = QLabel(self)
        self._tagline.setObjectName("aboutTagline")
        self._tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._tagline.setWordWrap(True)
        root.addWidget(self._tagline)

        self._built_with = QLabel(self)
        self._built_with.setObjectName("aboutBuiltWith")
        self._built_with.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._built_with.setWordWrap(True)
        root.addWidget(self._built_with)

        self._license = QLabel(self)
        self._license.setObjectName("aboutLicense")
        self._license.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._license)

        self._github = QLabel(self)
        self._github.setObjectName("aboutGithub")
        self._github.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._github)

        root.addStretch(1)

        self._close = QPushButton(self)
        self._close.setObjectName("aboutCloseBtn")
        self._close.clicked.connect(self.accept)
        root.addWidget(self._close, 0, Qt.AlignmentFlag.AlignHCenter)

        self._unregister_i18n = register_retranslate(self.retranslate_ui)
        self.finished.connect(lambda _result: self._unregister_i18n())
        popup_shadow(self)
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        """Refresh about dialog copy for the active language."""
        self.setWindowTitle(tr("about_freepdf_suite"))
        self._title.setText(tr("app_title"))
        self._version.setText(f"v{APP_VERSION}")
        self._tagline.setText(tr("about_tagline"))
        self._built_with.setText(tr("about_built_with"))
        self._license.setText(tr("about_license_line"))
        self._github.setText(tr("about_github"))
        self._close.setText(tr("close"))


def _open_stub_dialog(parent: QWidget | None, title_key: str) -> None:
    """Show an empty placeholder dialog."""
    dialog = QDialog(parent)
    dialog.setObjectName("settingsStubDialog")
    dialog.setFixedSize(420, 280)

    unregister = register_retranslate(lambda: dialog.setWindowTitle(tr(title_key)))
    dialog.finished.connect(lambda _result: unregister())
    dialog.setWindowTitle(tr(title_key))
    popup_shadow(dialog)
    dialog.exec()


def confirm_reset_defaults(parent: QWidget | None = None) -> bool:
    """Ask for confirmation, reset config to defaults, and apply language."""
    if not ask_yes_no(parent, tr("reset_defaults_confirm")):
        return False
    config = reset_app_config()
    apply_language(str(config.get("language", "en")))
    return True


def show_options(parent: QWidget | None = None, *, initial_tab: int = 0) -> None:
    OptionsDialog(parent, initial_tab=initial_tab).exec()


def show_general_settings(parent: QWidget | None = None) -> None:
    show_options(parent, initial_tab=0)


def show_view_settings(parent: QWidget | None = None) -> None:
    show_options(parent, initial_tab=1)


def show_about(parent: QWidget | None = None) -> None:
    AboutDialog(parent).exec()
