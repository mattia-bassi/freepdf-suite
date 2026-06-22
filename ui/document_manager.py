"""Multi-document tab state for the PDF viewer."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QStackedWidget, QWidget

from core.page_manager import PageManager

from .pdf_reader import PdfReaderWidget

CloseChoice = str | None  # "save" | "discard" | "cancel" | None (no prompt needed)


@dataclass
class DocumentState:
    """One open document tab: backend handle, viewer widget, and page edits."""

    file_path: Path
    document: Any
    reader: PdfReaderWidget
    page_manager: PageManager
    is_temp: bool = False
    current_page: int = 0
    zoom_level: float = 1.0
    fit_mode: str | None = None
    scroll_position: tuple[int, int] = field(default_factory=lambda: (0, 0))

    @property
    def display_name(self) -> str:
        """Return the filename shown on the tab strip."""
        return self.file_path.name

    @property
    def is_dirty(self) -> bool:
        """Return True when page edits have not been saved."""
        return self.page_manager.is_dirty

    def capture_viewer_state(self) -> None:
        """Snapshot scroll/zoom/page from the reader widget."""
        self.current_page = self.reader.current_page
        self.zoom_level = self.reader.zoom
        self.fit_mode = self.reader.fit_mode
        self.scroll_position = self.reader.scroll_position()

    def restore_viewer_state(self) -> None:
        """Restore scroll/zoom/page on the reader widget."""
        reader = self.reader
        if self.fit_mode == "width":
            reader.fit_width()
        elif self.fit_mode == "page":
            reader.fit_page()
        else:
            reader.set_zoom(self.zoom_level)
        if reader.page_count > 0:
            page = min(max(0, self.current_page), reader.page_count - 1)
            reader.go_to_page(page)
        reader.set_scroll_position(self.scroll_position)


class DocumentManager(QObject):
    """Track open documents, active tab, and stacked reader widgets."""

    active_changed = Signal(int)
    tabs_changed = Signal()
    dirty_changed = Signal(int, bool)

    def __init__(
        self,
        engine: Any,
        config: dict[str, Any],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._engine = engine
        self._config = dict(config)
        self._parent = parent
        self._tabs: list[DocumentState] = []
        self._active_index = -1
        self._confirm_close: Callable[[DocumentState], CloseChoice] | None = None
        self._reader_factory: Callable[[], PdfReaderWidget] | None = None

        self._stack = QStackedWidget(parent)
        self._empty_reader = PdfReaderWidget(self._config, parent)
        self._empty_reader.attach_engine(engine)
        self._stack.addWidget(self._empty_reader)

    def set_confirm_close_handler(
        self, handler: Callable[[DocumentState], CloseChoice]
    ) -> None:
        """Register a callback that prompts before closing a dirty tab."""
        self._confirm_close = handler

    def set_reader_factory(self, factory: Callable[[], PdfReaderWidget]) -> None:
        """Optional factory so MainWindow can wire reader signals when creating tabs."""
        self._reader_factory = factory

    @property
    def stack(self) -> QStackedWidget:
        """Stacked widget holding one reader per tab (plus the empty state)."""
        return self._stack

    @property
    def empty_reader(self) -> PdfReaderWidget:
        """Reader shown when no documents are open."""
        return self._empty_reader

    @property
    def active_index(self) -> int:
        return self._active_index

    def tab_count(self) -> int:
        return len(self._tabs)

    def tab_at(self, index: int) -> DocumentState | None:
        if 0 <= index < len(self._tabs):
            return self._tabs[index]
        return None

    def get_active(self) -> DocumentState | None:
        """Return the currently visible document, if any."""
        return self.tab_at(self._active_index)

    def tab_label(self, index: int) -> str:
        """Build tab text with optional dirty marker."""
        state = self.tab_at(index)
        if state is None:
            return ""
        prefix = "● " if state.is_dirty else ""
        name = state.display_name
        if len(name) > 20:
            name = name[:17] + "..."
        return f"{prefix}{name}"

    def paths_for_session(self) -> list[Path]:
        """Return non-temporary open paths for session persistence."""
        return [tab.file_path for tab in self._tabs if not tab.is_temp]

    def find_index_by_path(self, path: Path) -> int | None:
        """Return tab index for an already-open file, or None."""
        target = _resolve_path(path)
        for index, tab in enumerate(self._tabs):
            if _resolve_path(tab.file_path) == target:
                return index
        return None

    def open_document(
        self,
        document: Any,
        path: Path,
        *,
        is_temp: bool = False,
    ) -> int:
        """Register an opened document as a new tab or switch to an existing one."""
        existing = self.find_index_by_path(path)
        if existing is not None:
            self._engine.close(document)
            self.switch_to(existing)
            return existing

        reader = (
            self._reader_factory()
            if self._reader_factory is not None
            else PdfReaderWidget(self._config, self._parent)
        )
        reader.attach_engine(self._engine)
        page_manager = PageManager(self._engine)
        state = DocumentState(
            file_path=path,
            document=document,
            reader=reader,
            page_manager=page_manager,
            is_temp=is_temp,
            zoom_level=float(self._config.get("zoom_default", 1.0)),
        )
        reader.show_document(document)
        self._stack.addWidget(reader)
        self._tabs.append(state)
        index = len(self._tabs) - 1
        self.switch_to(index)
        self.tabs_changed.emit()
        return index

    def replace_current(
        self,
        document: Any,
        path: Path,
        *,
        is_temp: bool = False,
    ) -> int:
        """Replace the active tab's document in place without opening a new tab."""
        if self._active_index < 0 or self._active_index >= len(self._tabs):
            return self.open_document(document, path, is_temp=is_temp)

        state = self._tabs[self._active_index]
        self._engine.close(state.document)

        state.file_path = path
        state.document = document
        state.is_temp = is_temp
        state.page_manager.reset_dirty()
        state.current_page = 0
        state.zoom_level = float(self._config.get("zoom_default", 1.0))
        state.fit_mode = None
        state.scroll_position = (0, 0)

        state.reader.clear_selection()
        state.reader.show_document(document)
        self.tabs_changed.emit()
        self.active_changed.emit(self._active_index)
        return self._active_index

    def switch_to(self, index: int) -> None:
        """Activate a tab and show its reader widget."""
        if index < 0 or index >= len(self._tabs):
            return
        if self._active_index >= 0:
            active = self.get_active()
            if active is not None:
                active.reader.clear_selection()
                active.reader.invalidate_all_word_caches()
                active.capture_viewer_state()

        self._active_index = index
        state = self._tabs[index]
        self._stack.setCurrentWidget(state.reader)
        state.reader.clear_selection()
        state.reader.invalidate_all_word_caches()
        state.restore_viewer_state()
        self.active_changed.emit(index)

    def mark_dirty(self, index: int | None = None) -> None:
        """Notify listeners that a tab's dirty flag may have changed."""
        idx = self._active_index if index is None else index
        state = self.tab_at(idx)
        if state is not None:
            self.dirty_changed.emit(idx, state.is_dirty)

    def close_document(self, index: int, *, confirm: bool = True) -> bool:
        """Close one tab after optional unsaved-changes prompt. Returns True if closed."""
        if index < 0 or index >= len(self._tabs):
            return False
        state = self._tabs[index]
        if confirm and not self._maybe_confirm_close(state):
            return False
        self._remove_tab(index, confirm=False)
        return True

    def close_all(self) -> bool:
        """Close every tab; returns False if the user cancelled a prompt."""
        while self._tabs:
            if not self.close_document(len(self._tabs) - 1):
                return False
        return True

    def close_others(self, keep_index: int) -> bool:
        """Close every tab except ``keep_index``."""
        indices = [index for index in range(len(self._tabs)) if index != keep_index]
        for index in reversed(indices):
            if not self.close_document(index):
                return False
            if keep_index > index:
                keep_index -= 1
        return True

    def replace_document_at(
        self,
        index: int,
        document: Any,
        path: Path,
        *,
        is_temp: bool = False,
    ) -> int:
        """Replace the document at ``index`` after an unsaved-changes prompt."""
        if index < 0 or index >= len(self._tabs):
            return self.open_document(document, path, is_temp=is_temp)

        state = self._tabs[index]
        if not self._maybe_confirm_close(state):
            return index

        self._engine.close(state.document)
        self._stack.removeWidget(state.reader)
        state.reader.deleteLater()

        reader = (
            self._reader_factory()
            if self._reader_factory is not None
            else PdfReaderWidget(self._config, self._parent)
        )
        reader.attach_engine(self._engine)
        page_manager = PageManager(self._engine)
        new_state = DocumentState(
            file_path=path,
            document=document,
            reader=reader,
            page_manager=page_manager,
            is_temp=is_temp,
            zoom_level=float(self._config.get("zoom_default", 1.0)),
        )
        reader.show_document(document)
        self._stack.insertWidget(index + 1, reader)
        self._tabs[index] = new_state
        self._active_index = index
        self._stack.setCurrentWidget(reader)
        self.tabs_changed.emit()
        self.active_changed.emit(index)
        return index

    def _maybe_confirm_close(self, state: DocumentState) -> bool:
        if not state.is_dirty:
            return True
        if self._confirm_close is None:
            return True
        choice = self._confirm_close(state)
        if choice in (None, "discard", "save"):
            return True
        return False

    def _remove_tab(self, index: int, *, confirm: bool = True) -> None:
        state = self._tabs[index]
        if confirm and not self._maybe_confirm_close(state):
            return

        self._engine.close(state.document)
        self._stack.removeWidget(state.reader)
        state.reader.deleteLater()
        del self._tabs[index]

        if not self._tabs:
            self._active_index = -1
            self._stack.setCurrentWidget(self._empty_reader)
        elif index < self._active_index:
            self._active_index -= 1
        elif self._active_index >= len(self._tabs):
            self._active_index = len(self._tabs) - 1
            self._stack.setCurrentWidget(self._tabs[self._active_index].reader)
        elif self._active_index == index:
            self._active_index = min(index, len(self._tabs) - 1)
            self._stack.setCurrentWidget(self._tabs[self._active_index].reader)

        self.tabs_changed.emit()
        self.active_changed.emit(self._active_index)


def _resolve_path(path: Path) -> str:
    try:
        return str(path.resolve())
    except OSError:
        return str(path)
