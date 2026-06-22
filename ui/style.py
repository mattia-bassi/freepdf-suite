"""Custom Qt style overrides layered on top of qt-material."""

from __future__ import annotations

# EaseOut dark elevation palette (lighter surfaces sit higher).
BG_VOID = "#0a0a0c"
BG_DARKEST = BG_VOID
BG_CONTENT = "#18181b"
CARD_NAV_BG = "#1c1c1f"
CARD_VIEWER_BG = "#141416"
NAV_GRADIENT_TOP = CARD_NAV_BG
NAV_GRADIENT_BOTTOM = "#161618"
SURFACE_GRADIENT = (
    f"qlineargradient(x1:0, y1:0, x2:0, y2:1, "
    f"stop:0 {NAV_GRADIENT_TOP}, stop:1 {NAV_GRADIENT_BOTTOM})"
)
PRIMARY_BTN_GRADIENT = (
    "qlineargradient(x1:0, y1:0, x2:0, y2:1, " "stop:0 #4f93ff, stop:1 #1565C0)"
)

TEXT_PRIMARY = "#e8e8ea"
TEXT_SECONDARY = "#9a9a9e"
INTERACTION_BORDER = "#448aff"
NAV_TAB_ACCENT = "#1565C0"
NAV_SEGMENT_BG = "#232326"
NAV_TAB_ACTIVE_BG = INTERACTION_BORDER
NAV_TAB_HOVER_BG = "#2a2a2e"
NAV_TAB_INACTIVE = TEXT_SECONDARY
NAV_TAB_HOVER_TEXT = "#c4c4c8"
NAV_TAB_TEXT = TEXT_PRIMARY
SEARCH_BAR_BG = NAV_SEGMENT_BG
ACCENT_RIM = "rgba(68, 138, 255, 0.5)"
DEFAULT_BORDER = "#2a2a2e"
THUMBNAIL_PANEL_BG = BG_CONTENT
VIEWER_BG = CARD_VIEWER_BG
CARD_RADIUS = "14px"

# Overrides for widgets not covered by qt-material's dark_blue theme.
APP_STYLESHEET = f"""
QMainWindow {{
    background: {BG_VOID};
}}
QWidget#appCanvas {{
    background: {BG_VOID};
}}
QFrame#navCard,
QFrame#readerStripCard,
QFrame#documentTabCard {{
    background: {CARD_NAV_BG};
    border: none;
    border-radius: {CARD_RADIUS};
}}
QTabBar#documentTabBar {{
    background: transparent;
    border: none;
}}
QTabBar#documentTabBar::tab {{
    background: {NAV_SEGMENT_BG};
    color: {NAV_TAB_INACTIVE};
    padding: 6px 12px 6px 10px;
    margin-right: 4px;
    border-radius: 8px;
    min-height: 28px;
}}
QTabBar#documentTabBar::tab:selected {{
    background: {NAV_TAB_ACTIVE_BG};
    color: {TEXT_PRIMARY};
    border-bottom: 2px solid {INTERACTION_BORDER};
}}
QTabBar#documentTabBar::tab:hover {{
    background: {NAV_TAB_HOVER_BG};
    color: {NAV_TAB_HOVER_TEXT};
}}
QToolButton#documentTabCloseButton {{
    color: {TEXT_SECONDARY};
    border: none;
    padding: 0 4px;
    font-size: 11px;
}}
QToolButton#documentTabCloseButton:hover {{
    color: {TEXT_PRIMARY};
}}
QFrame#thumbnailCard {{
    background: {BG_CONTENT};
    border: none;
    border-radius: {CARD_RADIUS};
}}
QFrame#viewerCard {{
    background: {CARD_VIEWER_BG};
    border: none;
    border-radius: {CARD_RADIUS};
}}
QToolBar#topNavToolBar {{
    background: transparent;
    border: none;
    padding: 0;
    margin: 0;
}}
QWidget#topNavBar {{
    background: transparent;
    min-height: 44px;
    max-height: 44px;
}}
QLabel#navBarLogo {{
    background: transparent;
}}
QLabel#navBrandTitle {{
    color: {TEXT_PRIMARY};
    background: transparent;
}}
QFrame#navBarDivider {{
    background: #333333;
    border: none;
    margin: 0;
    min-height: 24px;
    max-height: 28px;
}}

QFrame#navTabGroup {{
    background: {NAV_SEGMENT_BG};
    border: none;
    border-radius: 10px;
}}
QFrame#navTab {{
    background: transparent;
    border: none;
    border-radius: 8px;
}}
QFrame#navTab[active="true"] {{
    background: {NAV_TAB_ACTIVE_BG};
    border: none;
    border-radius: 8px;
}}
QFrame#navTab:hover[active="false"] {{
    background: {NAV_TAB_HOVER_BG};
    border-radius: 8px;
}}
QFrame#navTab[active="true"]:hover {{
    background: {NAV_TAB_ACTIVE_BG};
    border: none;
}}
QLabel#navTabIcon,
QLabel#navTabLabel {{
    background: transparent;
    border: none;
}}
QFrame#navTab[active="false"] QLabel#navTabLabel {{
    color: {TEXT_SECONDARY};
}}
QFrame#navTab[active="true"] QLabel#navTabLabel {{
    color: #ffffff;
}}
QFrame#navTab:hover[active="false"] QLabel#navTabLabel {{
    color: {NAV_TAB_HOVER_TEXT};
}}

QWidget#toolbarSearchBar {{
    background: {NAV_SEGMENT_BG};
    border: 1px solid transparent;
    border-radius: 10px;
    min-height: 34px;
    max-height: 34px;
    min-width: 200px;
}}
QWidget#toolbarSearchBar:focus-within {{
    border: 1px solid rgba(68, 138, 255, 0.4);
    background: {NAV_SEGMENT_BG};
}}
QLineEdit#toolbarSearchEdit {{
    background: transparent;
    border: none;
    color: {TEXT_PRIMARY};
    padding: 2px 0;
    font-size: 13px;
}}
QLineEdit#toolbarSearchEdit::placeholder {{
    color: {TEXT_SECONDARY};
}}

QWidget#readerToolStrip {{
    background: transparent;
    border: none;
    min-height: 36px;
}}
QPushButton#readerOpenBtn {{
    background: {PRIMARY_BTN_GRADIENT};
    border: none;
    border-radius: 10px;
    color: {TEXT_PRIMARY};
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 600;
    min-height: 30px;
}}
QPushButton#readerOpenBtn:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5a9dff, stop:1 #1976d2);
    color: {TEXT_PRIMARY};
}}
QPushButton#readerOpenBtn:pressed {{
    background: {NAV_TAB_ACCENT};
    color: {TEXT_PRIMARY};
    padding-top: 9px;
    padding-bottom: 7px;
    padding-left: 17px;
    padding-right: 15px;
}}
QFrame#readerFitGroup {{
    background: {NAV_SEGMENT_BG};
    border: none;
    border-radius: 10px;
}}
QPushButton#readerFitBtn {{
    background: transparent;
    border: none;
    border-radius: 8px;
    color: {TEXT_SECONDARY};
    padding: 8px 14px;
    font-size: 12px;
    min-height: 28px;
}}
QPushButton#readerFitBtn:hover {{
    background: {NAV_TAB_HOVER_BG};
    color: {TEXT_PRIMARY};
}}
QPushButton#readerFitBtn[active="true"] {{
    background: {NAV_TAB_ACTIVE_BG};
    color: #ffffff;
    border: none;
    border-radius: 8px;
}}
QPushButton#readerFitBtn[active="true"]:hover {{
    background: {NAV_TAB_ACTIVE_BG};
    color: #ffffff;
}}
QPushButton#readerFitBtn:pressed {{
    background: #333338;
    color: {TEXT_PRIMARY};
    padding-top: 9px;
    padding-bottom: 7px;
    padding-left: 15px;
    padding-right: 13px;
}}
QPushButton#readerFitBtn[active="true"]:pressed {{
    background: {NAV_TAB_ACCENT};
    color: #ffffff;
    padding-top: 9px;
    padding-bottom: 7px;
    padding-left: 15px;
    padding-right: 13px;
}}
QFrame#navTabUnderline {{
    background: {NAV_TAB_ACCENT};
    border: none;
    border-radius: 1px;
}}
QWidget#pageNavigator {{
    background: {NAV_SEGMENT_BG};
    border: none;
    border-radius: 10px;
}}
QPushButton#pageNavArrow {{
    background: transparent;
    border: none;
    border-radius: 8px;
    color: {TEXT_SECONDARY};
    font-size: 13px;
    font-weight: bold;
    min-width: 26px;
    max-width: 26px;
    min-height: 26px;
    max-height: 26px;
}}
QPushButton#pageNavArrow:hover {{
    color: {TEXT_PRIMARY};
    background: {NAV_TAB_HOVER_BG};
    border: none;
}}
QPushButton#pageNavArrow:pressed {{
    background: #333338;
    color: {TEXT_PRIMARY};
    border: none;
}}
QPushButton#pageNavArrow:disabled {{
    color: #555558;
    background: transparent;
    border: none;
}}
QLineEdit#pageNavCurrent {{
    background: transparent;
    border: none;
    border-radius: 4px;
    color: {TEXT_PRIMARY};
    font-size: 12px;
    padding: 2px 0;
}}
QLineEdit#pageNavCurrent:focus {{
    border: none;
    background: {NAV_TAB_HOVER_BG};
}}
QLabel#pageNavTotal {{
    color: {TEXT_SECONDARY};
    font-size: 12px;
}}
QComboBox#readerZoomCombo {{
    background: {NAV_TAB_HOVER_BG};
    border: none;
    border-radius: 10px;
    color: {TEXT_PRIMARY};
    padding: 8px 12px;
    min-height: 30px;
    min-width: 72px;
}}
QComboBox#readerZoomCombo:hover,
QComboBox#readerZoomCombo:focus {{
    background: #333338;
    border: none;
}}
QComboBox#readerZoomCombo::drop-down {{
    border: none;
    width: 18px;
}}
QComboBox#readerZoomCombo QAbstractItemView {{
    background: #1f1f23;
    color: {TEXT_PRIMARY};
    selection-background-color: {NAV_TAB_ACCENT};
    border: 1px solid {DEFAULT_BORDER};
    border-radius: 6px;
    outline: none;
}}
QComboBox#readerZoomCombo QAbstractItemView::item {{
    padding: 6px 10px;
    min-height: 22px;
}}
QComboBox#readerZoomCombo QAbstractItemView::item:hover {{
    background: #2a2a2e;
}}
QComboBox#readerZoomCombo QAbstractItemView::item:selected {{
    background: {NAV_TAB_ACCENT};
    color: {TEXT_PRIMARY};
}}

QScrollArea#pdfViewerScroll {{
    background: transparent;
    border: none;
}}
QWidget#pdfViewerCanvas {{
    background: {CARD_VIEWER_BG};
}}
QLabel#viewerPlaceholder {{
    color: {TEXT_SECONDARY};
    background: transparent;
    font-size: 14px;
}}
QWidget#viewerEmptyState {{
    background: transparent;
}}
QLabel#viewerEmptyTitle {{
    color: {TEXT_PRIMARY};
    background: transparent;
    font-size: 16px;
    font-weight: bold;
}}
QLabel#viewerEmptyHints {{
    color: {TEXT_SECONDARY};
    background: transparent;
    font-size: 13px;
}}
QMenu::item:disabled {{
    color: {TEXT_SECONDARY};
    font-style: italic;
}}
QDialog#aboutDialog {{
    background: #1f1f23;
    color: {TEXT_PRIMARY};
}}
QLabel#aboutTitle {{
    color: {TEXT_PRIMARY};
    font-size: 20px;
    font-weight: bold;
}}
QLabel#aboutVersion,
QLabel#aboutTagline,
QLabel#aboutBuiltWith {{
    color: {TEXT_SECONDARY};
    font-size: 13px;
}}
QLabel#aboutLicense {{
    color: {TEXT_PRIMARY};
    font-size: 13px;
}}
QLabel#aboutGithub {{
    color: {INTERACTION_BORDER};
    font-size: 12px;
}}
QPushButton#aboutCloseBtn {{
    background: {PRIMARY_BTN_GRADIENT};
    border: none;
    border-radius: 6px;
    color: {TEXT_PRIMARY};
    padding: 8px 24px;
    font-size: 13px;
    font-weight: 600;
    min-width: 96px;
}}
QPushButton#aboutCloseBtn:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5a9dff, stop:1 #1976d2);
}}
QWidget#thumbnailPanel {{
    background: transparent;
    border: none;
}}
QLabel#thumbnailTitle {{
    color: {TEXT_PRIMARY};
    font-size: 13px;
    font-weight: bold;
    padding-left: 4px;
    background: transparent;
}}
QListWidget#thumbnailList {{
    background: transparent;
    border: none;
    color: {TEXT_SECONDARY};
    outline: none;
}}
QListWidget#thumbnailList::item {{
    background: transparent;
    border: none;
    padding: 2px 0;
}}
QStatusBar#appStatusBar {{
    background: {BG_VOID};
    color: {TEXT_SECONDARY};
    border-top: none;
    padding-left: 8px;
}}
QStatusBar#appStatusBar QLabel {{
    color: {TEXT_SECONDARY};
    padding-left: 8px;
}}
QStatusBar#appStatusBar[flash="true"] QLabel {{
    color: {INTERACTION_BORDER};
}}
QProgressBar#ocrStatusProgress {{
    background: {NAV_SEGMENT_BG};
    border: none;
    border-radius: 6px;
    height: 10px;
    text-align: center;
    color: {TEXT_PRIMARY};
    font-size: 11px;
    margin-right: 8px;
}}
QProgressBar#ocrStatusProgress::chunk {{
    background: {NAV_TAB_ACTIVE_BG};
    border-radius: 6px;
}}
QWidget#ocrProcessingOverlay {{
    background: rgba(10, 10, 12, 160);
}}
QWidget#ocrProcessingPanel {{
    background: #1f1f23;
    border: 1px solid #3a3a3e;
    border-radius: 12px;
}}
QLabel#ocrProcessingMessage {{
    color: {TEXT_PRIMARY};
    font-size: 14px;
    font-weight: 600;
}}

QDialog#generalSettingsDialog,
QDialog#optionsDialog,
QDialog#settingsStubDialog,
QDialog#ocrDialog {{
    background: #1f1f23;
    color: {TEXT_PRIMARY};
    border-radius: 12px;
}}
QLabel#ocrDialogTitle {{
    color: {TEXT_PRIMARY};
    font-size: 16px;
    font-weight: bold;
}}
QLabel#ocrMissingMessage,
QLabel#ocrProgressLabel {{
    color: {TEXT_SECONDARY};
    font-size: 13px;
}}
QProgressBar#ocrProgressBar {{
    background: {NAV_SEGMENT_BG};
    border: none;
    border-radius: 6px;
    height: 8px;
    text-align: center;
    color: transparent;
}}
QProgressBar#ocrProgressBar::chunk {{
    background: {NAV_TAB_ACTIVE_BG};
    border-radius: 6px;
}}
QLabel#settingsSectionTitle {{
    color: {TEXT_PRIMARY};
    font-size: 14px;
    font-weight: bold;
}}
QLabel#settingsFieldLabel {{
    color: {TEXT_SECONDARY};
    font-size: 13px;
}}
QComboBox#settingsCombo {{
    background: {BG_CONTENT};
    border: 1px solid #3a3a3e;
    border-radius: 6px;
    color: {TEXT_PRIMARY};
    padding: 0 10px;
    height: 28px;
    min-height: 28px;
    max-height: 28px;
    max-width: 180px;
}}
QComboBox#settingsCombo:hover {{
    border-color: {NAV_TAB_ACCENT};
}}
QComboBox#settingsCombo::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox#settingsCombo QAbstractItemView {{
    background: #1f1f23;
    color: {TEXT_PRIMARY};
    selection-background-color: {NAV_TAB_ACCENT};
}}
QComboBox#settingsPdfCombo {{
    background: {BG_CONTENT};
    border: 1px solid #3a3a3e;
    border-radius: 6px;
    color: {TEXT_PRIMARY};
    padding: 0 10px;
    height: 28px;
    min-height: 28px;
    max-height: 28px;
    max-width: 180px;
}}
QComboBox#settingsPdfCombo:hover {{
    border-color: {NAV_TAB_ACCENT};
}}
QComboBox#settingsPdfCombo::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox#settingsPdfCombo QAbstractItemView {{
    background: #1f1f23;
    color: {TEXT_PRIMARY};
    selection-background-color: {NAV_TAB_ACCENT};
    min-width: 180px;
}}
QLabel#settingsFormLabel {{
    color: {TEXT_SECONDARY};
    font-size: 13px;
    min-height: 28px;
    max-height: 28px;
}}
QPushButton#settingsSaveButton {{
    background: {PRIMARY_BTN_GRADIENT};
    border: none;
    border-radius: 6px;
    color: {TEXT_PRIMARY};
    padding: 8px 20px;
    font-size: 13px;
    min-width: 80px;
}}
QPushButton#settingsSaveButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5a9dff, stop:1 #1976d2);
}}
QTabWidget#optionsTabWidget::pane {{
    border: 1px solid #2a2a2e;
    border-radius: 6px;
    background: {BG_CONTENT};
}}
QTabWidget#optionsTabWidget QTabBar::tab {{
    background: #1f1f23;
    color: {TEXT_SECONDARY};
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}}
QTabWidget#optionsTabWidget QTabBar::tab:selected {{
    background: #2a2a2e;
    color: {TEXT_PRIMARY};
}}
QLineEdit#settingsLineEdit {{
    background: {BG_CONTENT};
    border: 1px solid #3a3a3e;
    border-radius: 6px;
    color: {TEXT_PRIMARY};
    padding: 6px 10px;
    min-height: 28px;
}}
QLineEdit#settingsLineEdit:hover,
QLineEdit#settingsLineEdit:focus {{
    border-color: {NAV_TAB_ACCENT};
}}
QSpinBox#settingsSpinBox {{
    background: {BG_CONTENT};
    border: 1px solid #3a3a3e;
    border-radius: 6px;
    color: {TEXT_PRIMARY};
    padding: 0 8px;
    height: 28px;
    min-height: 28px;
    max-height: 28px;
    max-width: 180px;
}}
QCheckBox#settingsCheckBox {{
    color: {TEXT_SECONDARY};
    spacing: 8px;
}}
QPushButton#settingsBrowseButton,
QPushButton#settingsResetButton {{
    background: transparent;
    border: 1px solid #3a3a3e;
    border-radius: 6px;
    color: {TEXT_PRIMARY};
    padding: 6px 14px;
}}
QPushButton#settingsBrowseButton:hover,
QPushButton#settingsResetButton:hover {{
    border-color: {NAV_TAB_ACCENT};
    color: {TEXT_PRIMARY};
}}
"""
