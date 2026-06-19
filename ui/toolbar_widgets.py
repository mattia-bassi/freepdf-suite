"""Navigation bar and reader tool-strip widgets for the PDF shell."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEasingCurve, QEvent, QPoint, QPropertyAnimation, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QEnterEvent, QFont, QMouseEvent, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QStyledItemDelegate,
    QStyle,
    QStyleOptionViewItem,
    QWidget,
)

from .i18n import tr
from .style import INTERACTION_BORDER, NAV_TAB_ACCENT, NAV_TAB_HOVER_TEXT, NAV_TAB_INACTIVE
from .visual_effects import (
    accent_tab_glow,
    clear_shadow,
    primary_button_glow,
    shadow_popup_window,
)

NAV_ICON_SIZE = 14
NAV_ICON_STROKE = 1.4
SEARCH_ICON_INACTIVE = "#9a9a9e"
SEARCH_ICON_ACTIVE = INTERACTION_BORDER
NAV_TAB_ACTIVE_TEXT = "#ffffff"


def _draw_search_icon(size: int = 14, color: str = SEARCH_ICON_INACTIVE) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color))
    pen.setWidthF(1.5)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(2, 2, size - 8, size - 8)
    painter.drawLine(size - 7, size - 7, size - 2, size - 2)
    painter.end()
    return pixmap


def _draw_nav_icon(kind: str, color: QColor, size: int = NAV_ICON_SIZE) -> QPixmap:
    """Draw a simple monochrome navigation tab icon (uniform 14px / 1.4 stroke)."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(color)
    pen.setWidthF(NAV_ICON_STROKE)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    if kind == "file":
        painter.drawRoundedRect(3, 2, 8, 10, 1.5, 1.5)
        painter.drawLine(5, 2, 5, 5)
        painter.drawLine(5, 2, 8, 5)
    elif kind == "view":
        painter.drawEllipse(3, 4, 8, 6)
        painter.drawEllipse(6, 6, 2, 2)
    elif kind == "tools":
        painter.drawEllipse(5, 5, 4, 4)
        for angle in range(0, 360, 45):
            painter.save()
            painter.translate(7, 7)
            painter.rotate(angle)
            painter.drawLine(0, -4, 0, -2)
            painter.restore()
    elif kind == "pdf":
        painter.drawRoundedRect(3, 2, 8, 10, 1.5, 1.5)
        painter.drawLine(5, 6, 9, 6)
        painter.drawLine(5, 8, 9, 8)
    elif kind == "options":
        painter.drawEllipse(5, 5, 4, 4)
        painter.drawEllipse(6, 6, 2, 2)
        painter.drawLine(7, 2, 7, 4)
        painter.drawLine(7, 10, 7, 12)
        painter.drawLine(2, 7, 4, 7)
        painter.drawLine(10, 7, 12, 7)
    elif kind == "help":
        painter.drawEllipse(2, 2, 10, 10)
        painter.drawArc(5, 4, 4, 5, 60 * 16, 180 * 16)
        painter.drawEllipse(6, 9, 2, 2)
    else:
        painter.drawEllipse(3, 3, 8, 8)

    painter.end()
    return pixmap


def _nav_divider(parent: QWidget) -> QFrame:
    """Thin vertical separator for the navigation bar."""
    divider = QFrame(parent)
    divider.setObjectName("navBarDivider")
    divider.setFixedSize(1, 28)
    return divider


class NavTabButton(QFrame):
    """Icon + label navigation tab with pill highlight when active."""

    clicked = Signal()

    def __init__(self, icon_kind: str, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("navTab")
        self.setProperty("active", "false")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._icon_kind = icon_kind

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 5, 12, 5)
        layout.setSpacing(6)

        self._icon = QLabel(self)
        self._icon.setObjectName("navTabIcon")
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon.setFixedSize(NAV_ICON_SIZE, NAV_ICON_SIZE)
        self._icon.setScaledContents(True)

        self._label = QLabel(label, self)
        self._label.setObjectName("navTabLabel")
        label_font = QFont(self._label.font())
        label_font.setPixelSize(13)
        label_font.setWeight(QFont.Weight.Medium)
        self._label.setFont(label_font)

        layout.addWidget(self._icon)
        layout.addWidget(self._label)
        self._refresh_icon()

    def set_text(self, label: str) -> None:
        """Update the visible tab label."""
        self._label.setText(label)

    def _icon_color(self) -> QColor:
        if self.isChecked():
            return QColor(NAV_TAB_ACTIVE_TEXT)
        if self.underMouse():
            return QColor(NAV_TAB_HOVER_TEXT)
        return QColor(NAV_TAB_INACTIVE)

    def _refresh_icon(self) -> None:
        self._icon.setPixmap(_draw_nav_icon(self._icon_kind, self._icon_color()))

    def setChecked(self, checked: bool) -> None:
        self.setProperty("active", "true" if checked else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        if checked:
            accent_tab_glow(self)
        else:
            clear_shadow(self)
        self._refresh_icon()
        self.update()

    def isChecked(self) -> bool:
        return self.property("active") == "true"

    def enterEvent(self, event: QEnterEvent) -> None:  # noqa: N802
        self._refresh_icon()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: ANN001, N802
        self._refresh_icon()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class NavTabUnderline(QFrame):
    """Animated accent underline beneath the active navigation tab."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("navTabUnderline")
        self.setFixedHeight(2)
        self.hide()
        self._anim = QPropertyAnimation(self, b"geometry", self)
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def move_to(self, tab: NavTabButton | None, *, animate: bool = True) -> None:
        """Slide the underline to sit under the given tab."""
        if tab is None:
            self.hide()
            return
        top_left = tab.mapTo(self.parentWidget(), QPoint(0, 0))
        parent = self.parentWidget()
        y = parent.height() - self.height() if parent is not None else top_left.y() + tab.height()
        target = QRect(top_left.x(), y, tab.width(), self.height())
        if not self.isVisible() or not animate:
            self.setGeometry(target)
            self.show()
            self.raise_()
            return
        self._anim.stop()
        self._anim.setStartValue(self.geometry())
        self._anim.setEndValue(target)
        self.show()
        self.raise_()
        self._anim.start()


class ZoomComboDelegate(QStyledItemDelegate):
    """Highlight the combo's current zoom value inside the dropdown list."""

    def __init__(self, combo: QComboBox) -> None:
        super().__init__(combo)
        self._combo = combo

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:  # noqa: ANN001
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        if index.row() == self._combo.currentIndex():
            painter.fillRect(opt.rect, QColor(NAV_TAB_ACCENT))
            opt.palette.setColor(opt.palette.ColorRole.Text, QColor(NAV_TAB_ACTIVE_TEXT))
            opt.palette.setColor(opt.palette.ColorRole.HighlightedText, QColor(NAV_TAB_ACTIVE_TEXT))
        super().paint(painter, opt, index)


class TopNavBar(QWidget):
    """Application navigation bar: brand, icon tabs, search."""

    file_clicked = Signal()
    view_clicked = Signal()
    tools_clicked = Signal()
    pdf_clicked = Signal()
    options_clicked = Signal()
    help_clicked = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        logo_path: str | Path | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("topNavBar")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumHeight(44)

        self._menu_tab: NavTabButton | None = None

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        brand = QHBoxLayout()
        brand.setSpacing(10)
        brand.setContentsMargins(0, 0, 0, 0)
        brand.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        if logo_path is not None:
            self._logo = QLabel(self)
            self._logo.setObjectName("navBarLogo")
            pixmap = QPixmap(str(logo_path))
            self._logo.setPixmap(
                pixmap.scaled(
                    32,
                    32,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            self._logo.setFixedSize(32, 32)
            brand.addWidget(self._logo)

        self._brand_title = QLabel("FreePDF Suite", self)
        self._brand_title.setObjectName("navBrandTitle")
        title_font = QFont(self._brand_title.font())
        title_font.setPixelSize(16)
        title_font.setWeight(QFont.Weight.Bold)
        self._brand_title.setFont(title_font)
        brand.addWidget(self._brand_title)
        root.addLayout(brand, 0)

        root.addSpacing(16)
        root.addWidget(_nav_divider(self), 0, Qt.AlignmentFlag.AlignVCenter)
        root.addSpacing(16)

        self._tab_group = QFrame(self)
        self._tab_group.setObjectName("navTabGroup")
        tabs_row = QHBoxLayout(self._tab_group)
        tabs_row.setSpacing(4)
        tabs_row.setContentsMargins(4, 4, 4, 4)
        tabs_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._file_tab = NavTabButton("file", tr("file"), self._tab_group)
        self._view_tab = NavTabButton("view", tr("view"), self._tab_group)
        self._tools_tab = NavTabButton("tools", tr("tools"), self._tab_group)
        self._pdf_tab = NavTabButton("pdf", tr("pdf"), self._tab_group)
        self._options_tab = NavTabButton("options", tr("options"), self._tab_group)
        self._help_tab = NavTabButton("help", tr("help"), self._tab_group)
        self._tabs = (
            self._file_tab,
            self._view_tab,
            self._tools_tab,
            self._pdf_tab,
            self._options_tab,
            self._help_tab,
        )

        for tab in self._tabs:
            tabs_row.addWidget(tab)

        self._file_tab.clicked.connect(self.file_clicked.emit)
        self._view_tab.clicked.connect(self.view_clicked.emit)
        self._tools_tab.clicked.connect(self.tools_clicked.emit)
        self._pdf_tab.clicked.connect(self.pdf_clicked.emit)
        self._options_tab.clicked.connect(self.options_clicked.emit)
        self._help_tab.clicked.connect(self.help_clicked.emit)

        root.addWidget(self._tab_group, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addStretch(1)

        self._search = SearchBar(self)
        root.addWidget(self._search, 0, Qt.AlignmentFlag.AlignVCenter)

        self._refresh_tabs()

    @property
    def tab_group(self) -> QFrame:
        return self._tab_group

    @property
    def search_bar(self) -> SearchBar:
        return self._search

    @property
    def file_tab(self) -> NavTabButton:
        return self._file_tab

    @property
    def view_tab(self) -> NavTabButton:
        return self._view_tab

    @property
    def tools_tab(self) -> NavTabButton:
        return self._tools_tab

    @property
    def pdf_tab(self) -> NavTabButton:
        return self._pdf_tab

    @property
    def options_tab(self) -> NavTabButton:
        return self._options_tab

    @property
    def help_tab(self) -> NavTabButton:
        return self._help_tab

    def show_menu_tab(self, tab: NavTabButton) -> None:
        """Temporarily highlight a tab while its dropdown menu is open."""
        self._menu_tab = tab
        self._refresh_tabs()

    def hide_menu_tab(self) -> None:
        """Clear tab highlight after a menu closes."""
        self._menu_tab = None
        self._refresh_tabs()

    def retranslate_ui(self) -> None:
        """Refresh navigation labels for the active language."""
        self._file_tab.set_text(tr("file"))
        self._view_tab.set_text(tr("view"))
        self._tools_tab.set_text(tr("tools"))
        self._pdf_tab.set_text(tr("pdf"))
        self._options_tab.set_text(tr("options"))
        self._help_tab.set_text(tr("help"))
        self._search.retranslate_ui()

    def _refresh_tabs(self) -> None:
        for tab in self._tabs:
            tab.setChecked(tab is self._menu_tab)


class PageNavigator(QWidget):
    """Compact page control: < current / total >."""

    value_changed = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("pageNavigator")
        self._maximum = 1

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._prev = QPushButton("<")
        self._prev.setObjectName("pageNavArrow")
        self._prev.setFixedSize(26, 26)
        self._prev.setFlat(True)
        self._prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self._prev.clicked.connect(self._go_prev)

        self._current = QLineEdit("1")
        self._current.setObjectName("pageNavCurrent")
        self._current.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._current.setFixedWidth(32)
        self._current.returnPressed.connect(self._commit)
        self._current.editingFinished.connect(self._commit)

        self._total = QLabel("/ 1")
        self._total.setObjectName("pageNavTotal")

        self._next = QPushButton(">")
        self._next.setObjectName("pageNavArrow")
        self._next.setFixedSize(26, 26)
        self._next.setFlat(True)
        self._next.setCursor(Qt.CursorShape.PointingHandCursor)
        self._next.clicked.connect(self._go_next)

        layout.addWidget(self._prev)
        layout.addWidget(self._current)
        layout.addWidget(self._total)
        layout.addWidget(self._next)
        self._apply_tooltips()

    def retranslate_ui(self) -> None:
        """Refresh navigator tooltips for the active language."""
        self._apply_tooltips()

    def _apply_tooltips(self) -> None:
        self._prev.setToolTip(tr("tooltip_prev_page"))
        self._next.setToolTip(tr("tooltip_next_page"))

    @property
    def prev_button(self) -> QPushButton:
        return self._prev

    @property
    def next_button(self) -> QPushButton:
        return self._next

    def value(self) -> int:
        try:
            return int(self._current.text())
        except ValueError:
            return 1

    def set_value(self, one_based: int) -> None:
        self._current.blockSignals(True)
        self._current.setText(str(max(1, one_based)))
        self._current.blockSignals(False)

    def set_range(self, maximum: int) -> None:
        self._maximum = max(1, maximum)
        self._total.setText(f"/ {self._maximum}")

    def set_nav_enabled(self, enabled: bool) -> None:
        self._prev.setEnabled(enabled)
        self._next.setEnabled(enabled)

    def _go_prev(self) -> None:
        page = max(1, self.value() - 1)
        self.set_value(page)
        self.value_changed.emit(page)

    def _go_next(self) -> None:
        page = min(self._maximum, self.value() + 1)
        self.set_value(page)
        self.value_changed.emit(page)

    def _commit(self) -> None:
        page = max(1, min(self.value(), self._maximum))
        self.set_value(page)
        self.value_changed.emit(page)


class ReaderToolStrip(QWidget):
    """Reader controls below the nav bar: Open, centered page nav, zoom and fit on the right."""

    open_clicked = Signal()
    page_changed = Signal(int)
    zoom_changed = Signal(float)
    fit_width_clicked = Signal()
    fit_page_clicked = Signal()

    def __init__(
        self,
        zoom_presets: list[tuple[str, float]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("readerToolStrip")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)
        root.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._open_btn = QPushButton(tr("open"))
        self._open_btn.setObjectName("readerOpenBtn")
        self._open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_btn.clicked.connect(self.open_clicked.emit)
        self._open_btn.installEventFilter(self)
        root.addWidget(self._open_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        self._page_nav = PageNavigator(self)
        self._page_nav.value_changed.connect(self.page_changed.emit)
        root.addWidget(self._page_nav, 0, Qt.AlignmentFlag.AlignVCenter)

        root.addStretch(1)

        self._fit_group = QFrame(self)
        self._fit_group.setObjectName("readerFitGroup")
        fit_layout = QHBoxLayout(self._fit_group)
        fit_layout.setContentsMargins(4, 4, 4, 4)
        fit_layout.setSpacing(4)
        fit_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._fit_width = QPushButton(tr("fit_width"))
        self._fit_width.setObjectName("readerFitBtn")
        self._fit_width.setProperty("active", "false")
        self._fit_width.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fit_width.clicked.connect(self._on_fit_width)

        self._fit_page = QPushButton(tr("fit_page"))
        self._fit_page.setObjectName("readerFitBtn")
        self._fit_page.setProperty("active", "false")
        self._fit_page.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fit_page.clicked.connect(self._on_fit_page)

        fit_layout.addWidget(self._fit_width)
        fit_layout.addWidget(self._fit_page)

        self._zoom_combo = QComboBox()
        self._zoom_combo.setObjectName("readerZoomCombo")
        self._zoom_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        for label, value in zoom_presets:
            self._zoom_combo.addItem(label, value)
        self._zoom_combo.setItemDelegate(ZoomComboDelegate(self._zoom_combo))
        self._zoom_combo.currentIndexChanged.connect(self._emit_zoom)
        self._zoom_combo.currentIndexChanged.connect(lambda _i: self._zoom_combo.view().update())
        self._wrap_zoom_popup()

        root.addWidget(self._fit_group, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addWidget(self._zoom_combo, 0, Qt.AlignmentFlag.AlignVCenter)
        self._apply_tooltips()
        self.set_fit_mode(None)

    def _on_fit_width(self) -> None:
        self.fit_width_clicked.emit()

    def _on_fit_page(self) -> None:
        self.fit_page_clicked.emit()

    def set_fit_mode(self, mode: str | None) -> None:
        """Highlight the active fit button; None clears both to neutral."""
        self._fit_width.setProperty("active", "true" if mode == "width" else "false")
        self._fit_page.setProperty("active", "true" if mode == "page" else "false")
        for button in (self._fit_width, self._fit_page):
            button.style().unpolish(button)
            button.style().polish(button)
            if button.property("active") == "true":
                accent_tab_glow(button)
            else:
                clear_shadow(button)
            button.update()

    def _wrap_zoom_popup(self) -> None:
        """Add a deep shadow to the zoom dropdown popup window."""
        original_show = self._zoom_combo.showPopup

        def show_with_shadow() -> None:
            original_show()
            shadow_popup_window(self._zoom_combo.view())

        self._zoom_combo.showPopup = show_with_shadow  # type: ignore[method-assign]

    def eventFilter(self, watched, event) -> bool:  # noqa: ANN001, N802
        if watched is self._open_btn:
            if event.type() == QEvent.Type.Enter:
                primary_button_glow(self._open_btn)
            elif event.type() == QEvent.Type.Leave:
                clear_shadow(self._open_btn)
        return super().eventFilter(watched, event)

    def _apply_tooltips(self) -> None:
        self._open_btn.setToolTip(tr("tooltip_open_file"))
        self._fit_width.setToolTip(tr("tooltip_fit_width"))
        self._fit_page.setToolTip(tr("tooltip_fit_page"))
        self._page_nav.retranslate_ui()

    @property
    def page_navigator(self) -> PageNavigator:
        return self._page_nav

    @property
    def zoom_combo(self) -> QComboBox:
        return self._zoom_combo

    def _emit_zoom(self, _index: int) -> None:
        value = self._zoom_combo.currentData()
        if value is not None:
            self.zoom_changed.emit(float(value))

    def retranslate_ui(self) -> None:
        """Refresh reader strip labels for the active language."""
        self._open_btn.setText(tr("open"))
        self._fit_width.setText(tr("fit_width"))
        self._fit_page.setText(tr("fit_page"))
        self._apply_tooltips()


class SearchBar(QWidget):
    """Rounded search field with a leading magnifier icon."""

    returnPressed = Signal()
    textChanged = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("toolbarSearchBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(8)

        self._icon = QLabel(self)
        self._icon.setObjectName("toolbarSearchIcon")
        self._icon.setFixedSize(14, 14)

        self._edit = QLineEdit()
        self._edit.setObjectName("toolbarSearchEdit")
        self._edit.setPlaceholderText(tr("search_placeholder"))
        self._edit.setClearButtonEnabled(True)
        self._edit.returnPressed.connect(self.returnPressed.emit)
        self._edit.textChanged.connect(self.textChanged.emit)
        self._edit.textChanged.connect(self._update_search_icon)
        self._edit.installEventFilter(self)

        layout.addWidget(self._icon)
        layout.addWidget(self._edit, 1)
        self._update_search_icon()

    def eventFilter(self, watched, event) -> bool:  # noqa: ANN001, N802
        if watched is self._edit and event.type() in (QEvent.Type.FocusIn, QEvent.Type.FocusOut):
            self._update_search_icon()
        return super().eventFilter(watched, event)

    def _update_search_icon(self, _text: str = "") -> None:
        active = self._edit.hasFocus() or bool(self._edit.text().strip())
        color = SEARCH_ICON_ACTIVE if active else SEARCH_ICON_INACTIVE
        self._icon.setPixmap(_draw_search_icon(14, color))

    def text(self) -> str:
        return self._edit.text()

    def setFocus(self) -> None:  # noqa: N802
        self._edit.setFocus()

    def retranslate_ui(self) -> None:
        """Refresh the search placeholder for the active language."""
        self._edit.setPlaceholderText(tr("search_placeholder"))

    def minimumSizeHint(self):  # noqa: ANN001
        hint = super().minimumSizeHint()
        return QSize(max(200, hint.width()), 34)

