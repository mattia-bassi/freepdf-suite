"""Split and merge PDF dialogs for the page manager."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.errors import DocumentSaveError, PageIndexError
from core.page_manager import PageManager, parse_page_ranges, ranges_from_split_points

from .i18n import register_retranslate, tr
from .message_boxes import show_critical, show_information
from .split_pdf_visual import SplitPdfThumbnailStrip
from .visual_effects import popup_shadow


class SplitPdfDialog(QDialog):
    """Split the open document into multiple PDF files using visual split points."""

    def __init__(
        self,
        parent: QWidget | None,
        *,
        page_manager: PageManager,
        engine: Any,
        doc: Any,
        page_count: int,
        stem: str,
    ) -> None:
        super().__init__(parent)
        self._page_manager = page_manager
        self._engine = engine
        self._doc = doc
        self._page_count = page_count
        self._stem = stem
        self._output_paths: list[Path] = []

        self.setObjectName("splitPdfDialog")
        self.setWindowTitle(tr("split_pdf_title"))
        self.setModal(True)
        self.resize(700, 450)
        self.setMinimumSize(700, 450)
        popup_shadow(self)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        self._hint = QLabel(tr("split_pdf_visual_hint"))
        self._hint.setWordWrap(True)
        root.addWidget(self._hint)

        self._strip = SplitPdfThumbnailStrip(self, engine=engine, doc=doc, page_count=page_count)
        self._strip.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._strip.split_changed.connect(self._update_preview)
        root.addWidget(self._strip, 1)

        self._preview = QLabel()
        self._preview.setObjectName("splitPdfPreview")
        self._preview.setWordWrap(True)
        root.addWidget(self._preview)

        self._advanced_toggle = QCheckBox(tr("split_pdf_advanced_options"))
        self._advanced_toggle.toggled.connect(self._toggle_advanced)
        root.addWidget(self._advanced_toggle)

        self._advanced_panel = QWidget()
        advanced_layout = QVBoxLayout(self._advanced_panel)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        advanced_layout.setSpacing(6)
        advanced_layout.addWidget(QLabel(tr("split_pdf_ranges_hint")))
        self._ranges_edit = QLineEdit()
        self._ranges_edit.setPlaceholderText(tr("split_pdf_ranges_placeholder"))
        self._ranges_edit.textChanged.connect(self._update_preview)
        advanced_layout.addWidget(self._ranges_edit)
        self._advanced_panel.hide()
        root.addWidget(self._advanced_panel)

        folder_row = QHBoxLayout()
        self._folder_label = QLabel(tr("split_pdf_output_folder"))
        self._folder_edit = QLineEdit()
        self._browse_folder = QPushButton(tr("split_pdf_browse_folder"))
        self._browse_folder.clicked.connect(self._pick_folder)
        folder_row.addWidget(self._folder_edit, 1)
        folder_row.addWidget(self._browse_folder)
        root.addWidget(self._folder_label)
        root.addLayout(folder_row)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self._split_button = QPushButton(tr("split_pdf_split"))
        self._split_button.clicked.connect(self._on_split)
        self._close_button = QPushButton(tr("close"))
        self._close_button.clicked.connect(self.reject)
        buttons.addWidget(self._split_button)
        buttons.addWidget(self._close_button)
        root.addLayout(buttons)

        self._unregister = register_retranslate(self.retranslate_ui)
        self.finished.connect(lambda _result: self._unregister())
        self._update_preview()

    def retranslate_ui(self) -> None:
        self.setWindowTitle(tr("split_pdf_title"))
        self._hint.setText(tr("split_pdf_visual_hint"))
        self._advanced_toggle.setText(tr("split_pdf_advanced_options"))
        self._folder_label.setText(tr("split_pdf_output_folder"))
        self._browse_folder.setText(tr("split_pdf_browse_folder"))
        self._split_button.setText(tr("split_pdf_split"))
        self._close_button.setText(tr("close"))
        self._ranges_edit.setPlaceholderText(tr("split_pdf_ranges_placeholder"))
        self._update_preview()

    def output_paths(self) -> list[Path]:
        return list(self._output_paths)

    def _toggle_advanced(self, checked: bool) -> None:
        self._advanced_panel.setVisible(checked)
        self._update_preview()

    def _pick_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, tr("split_pdf_output_folder"))
        if folder:
            self._folder_edit.setText(folder)

    def _current_ranges(self) -> list[tuple[int, int]]:
        if self._advanced_toggle.isChecked() and self._ranges_edit.text().strip():
            return parse_page_ranges(self._ranges_edit.text(), self._page_count)
        splits = self._strip.active_split_points()
        if not splits:
            raise PageIndexError("No split points selected.")
        return ranges_from_split_points(self._page_count, splits)

    def _format_preview(self, ranges: list[tuple[int, int]]) -> str:
        parts: list[str] = []
        for index, (start, end) in enumerate(ranges, start=1):
            if start == end:
                parts.append(
                    tr("split_pdf_preview_single")
                    .replace("{n}", str(index))
                    .replace("{page}", str(start + 1))
                )
            else:
                parts.append(
                    tr("split_pdf_preview_range")
                    .replace("{n}", str(index))
                    .replace("{start}", str(start + 1))
                    .replace("{end}", str(end + 1))
                )
        return " | ".join(parts)

    def _update_preview(self) -> None:
        try:
            if self._advanced_toggle.isChecked() and self._ranges_edit.text().strip():
                ranges = parse_page_ranges(self._ranges_edit.text(), self._page_count)
            else:
                splits = self._strip.active_split_points()
                if not splits:
                    self._preview.setText(tr("split_pdf_preview_empty"))
                    return
                ranges = ranges_from_split_points(self._page_count, splits)
        except PageIndexError:
            self._preview.setText(tr("split_pdf_preview_empty"))
            return
        self._preview.setText(self._format_preview(ranges))

    def _on_split(self) -> None:
        folder_text = self._folder_edit.text().strip()
        if not folder_text:
            show_critical(self, tr("split_pdf_missing_folder"))
            return
        try:
            ranges = self._current_ranges()
            if len(ranges) < 2:
                show_critical(self, tr("split_pdf_no_splits"))
                return
            self._output_paths = self._page_manager.split_document(
                self._doc,
                ranges,
                Path(folder_text),
                stem=self._stem,
            )
        except (PageIndexError, ValueError) as exc:
            show_critical(self, tr("split_pdf_invalid_ranges").replace("{detail}", str(exc)))
            return
        except DocumentSaveError as exc:
            show_critical(self, str(exc))
            return
        show_information(
            self,
            tr("split_pdf_success")
            .replace("{count}", str(len(self._output_paths)))
            .replace("{folder}", folder_text),
        )
        self.accept()


class MergePdfDialog(QDialog):
    """Merge multiple PDF files into one output document."""

    open_result_requested = None  # set by factory

    def __init__(self, parent: QWidget | None, *, page_manager: PageManager) -> None:
        super().__init__(parent)
        self._page_manager = page_manager
        self._output_path: Path | None = None

        self.setObjectName("mergePdfDialog")
        self.setWindowTitle(tr("merge_pdf_title"))
        self.setModal(True)
        self.setFixedSize(520, 420)
        popup_shadow(self)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        self._file_list = QListWidget()
        self._file_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._file_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        root.addWidget(self._file_list)

        row = QHBoxLayout()
        add_files = QPushButton(tr("merge_pdf_add_files"))
        add_files.clicked.connect(self._add_files)
        remove_file = QPushButton(tr("merge_pdf_remove"))
        remove_file.clicked.connect(self._remove_selected)
        row.addWidget(add_files)
        row.addWidget(remove_file)
        row.addStretch(1)
        root.addLayout(row)

        output_row = QHBoxLayout()
        self._output_edit = QLineEdit()
        browse_output = QPushButton(tr("merge_pdf_browse_output"))
        browse_output.clicked.connect(self._pick_output)
        output_row.addWidget(self._output_edit, 1)
        output_row.addWidget(browse_output)
        root.addWidget(QLabel(tr("merge_pdf_output_file")))
        root.addLayout(output_row)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self._merge_button = QPushButton(tr("merge_pdf_merge"))
        self._merge_button.clicked.connect(self._on_merge)
        self._open_result_button = QPushButton(tr("merge_pdf_open_result"))
        self._open_result_button.setEnabled(False)
        self._open_result_button.clicked.connect(self._open_result)
        cancel = QPushButton(tr("close"))
        cancel.clicked.connect(self.reject)
        buttons.addWidget(self._open_result_button)
        buttons.addWidget(self._merge_button)
        buttons.addWidget(cancel)
        root.addLayout(buttons)

        self._open_result_callback = None
        self._unregister = register_retranslate(self.retranslate_ui)
        self.finished.connect(lambda _result: self._unregister())

    def retranslate_ui(self) -> None:
        self.setWindowTitle(tr("merge_pdf_title"))
        self._merge_button.setText(tr("merge_pdf_merge"))
        self._open_result_button.setText(tr("merge_pdf_open_result"))

    def set_open_result_callback(self, callback) -> None:  # noqa: ANN001
        self._open_result_callback = callback

    def _add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            tr("merge_pdf_add_files"),
            "",
            "PDF (*.pdf);;All files (*)",
        )
        existing = {self._file_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self._file_list.count())}
        for path in paths:
            if path in existing:
                continue
            item = QListWidgetItem(Path(path).name)
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setToolTip(path)
            self._file_list.addItem(item)

    def _remove_selected(self) -> None:
        for item in self._file_list.selectedItems():
            row = self._file_list.row(item)
            self._file_list.takeItem(row)

    def _pick_output(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("merge_pdf_output_file"),
            "",
            "PDF (*.pdf)",
        )
        if path:
            self._output_edit.setText(path)

    def _collect_paths(self) -> list[str]:
        return [
            str(self._file_list.item(i).data(Qt.ItemDataRole.UserRole))
            for i in range(self._file_list.count())
        ]

    def _on_merge(self) -> None:
        paths = self._collect_paths()
        if len(paths) < 2:
            show_critical(self, tr("merge_pdf_need_two"))
            return
        output_text = self._output_edit.text().strip()
        if not output_text:
            show_critical(self, tr("merge_pdf_missing_output"))
            return
        if not output_text.lower().endswith(".pdf"):
            output_text += ".pdf"
        try:
            self._output_path = self._page_manager.merge_documents(paths, output_text)
        except DocumentSaveError as exc:
            show_critical(self, str(exc))
            return
        self._open_result_button.setEnabled(True)
        show_information(
            self,
            tr("merge_pdf_success").replace("{filename}", Path(output_text).name),
        )

    def _open_result(self) -> None:
        if self._output_path is not None and self._open_result_callback is not None:
            self._open_result_callback(self._output_path)
            self.accept()


def show_split_pdf_dialog(
    parent: QWidget | None,
    *,
    page_manager: PageManager,
    engine: Any,
    doc: Any,
) -> list[Path]:
    page_count = int(getattr(doc, "page_count", 0))
    dialog = SplitPdfDialog(
        parent,
        page_manager=page_manager,
        engine=engine,
        doc=doc,
        page_count=page_count,
        stem=doc.path.stem,
    )
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.output_paths()
    return []


def show_merge_pdf_dialog(
    parent: QWidget | None,
    *,
    page_manager: PageManager,
    on_open_result,
) -> None:  # noqa: ANN001
    dialog = MergePdfDialog(parent, page_manager=page_manager)
    dialog.set_open_result_callback(on_open_result)
    dialog.exec()
