"""Main application window: module-driven menu + page viewer.

The menu is built from ``ModuleManager.list_modules()`` (contract 6.6), grouped by
the closed ``category`` enum (6.5). Selecting a module action dispatches a
``ModuleRequest`` through ``ModuleManager.execute`` using the module's primary
capability as the action. All backend access is tolerant: when the backend slice
is not yet merged, the window still opens with a disabled/empty module menu.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMenu,
    QMessageBox,
)

from .bootstrap import MODULES_DIR, load_backend
from .style import CATEGORY_COLORS
from .viewer_widget import ViewerWidget

# Human labels for the closed category enum (contract Section 4 / 6.5).
CATEGORY_LABELS: dict[str, str] = {
    "view": "View",
    "organize": "Organize",
    "optimize": "Optimize",
    "convert": "Convert",
    "enhance": "Enhance",
    "edit": "Edit",
    "security": "Security",
    "extract": "Extract",
}


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FreePDF Suite")
        self.resize(1100, 800)

        self._backend = load_backend()
        self._engine = self._make_engine()
        self._manager = self._make_manager()
        self._doc: Any = None

        self._viewer = ViewerWidget(self)
        self._viewer.attach_engine(self._engine)
        self.setCentralWidget(self._viewer)

        self._build_file_menu()
        self._build_module_menus()
        self.statusBar().showMessage(self._ready_message())

    # -- construction --------------------------------------------------------

    def _make_engine(self) -> Any:
        cls = self._backend.get("PDFEngine")
        try:
            return cls() if cls is not None else None
        except Exception:
            return None

    def _make_manager(self) -> Any:
        cls = self._backend.get("ModuleManager")
        if cls is None or self._engine is None:
            return None
        try:
            return cls(MODULES_DIR, self._engine)
        except Exception:
            return None

    def _ready_message(self) -> str:
        if self._manager is None:
            return "Ready — modules unavailable (backend not wired yet)"
        return "Ready"

    # -- menus ---------------------------------------------------------------

    def _build_file_menu(self) -> None:
        menu = self.menuBar().addMenu("&File")

        open_action = QAction("&Open…", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open)
        menu.addAction(open_action)

        menu.addSeparator()
        quit_action = QAction("E&xit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        menu.addAction(quit_action)

    def _build_module_menus(self) -> None:
        menu = self.menuBar().addMenu("&Tools")
        manifests = self._discover_manifests()
        if not manifests:
            placeholder = QAction("No modules available", self)
            placeholder.setEnabled(False)
            menu.addAction(placeholder)
            return

        # Group actions by category submenu, ordered by manifest ui.order.
        by_category: dict[str, list[Any]] = {}
        for manifest in manifests:
            category = self._field(manifest, "category", "view")
            by_category.setdefault(category, []).append(manifest)

        for category, items in sorted(by_category.items()):
            submenu: QMenu = menu.addMenu(CATEGORY_LABELS.get(category, category.title()))
            color = CATEGORY_COLORS.get(category, "#d4d4d4")
            submenu.setStyleSheet(f"QMenu::item:selected {{ color: {color}; }}")
            items.sort(key=lambda m: self._ui_order(m))
            for manifest in items:
                submenu.addAction(self._module_action(manifest))

    def _module_action(self, manifest: Any) -> QAction:
        module_id = self._field(manifest, "id", "?")
        label = self._menu_label(manifest)
        action = QAction(label, self)
        action.triggered.connect(lambda _=False, mid=module_id: self._on_run_module(mid))
        return action

    # -- handlers ------------------------------------------------------------

    def _on_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open PDF", "", "PDF & signed (*.pdf *.p7m *.pdf.p7m);;All files (*)"
        )
        if not path:
            return
        if self._engine is None:
            QMessageBox.warning(self, "Unavailable", "Core engine not wired yet.")
            return
        try:
            self._doc = self._engine.open(Path(path))
            self._viewer.show_document(self._doc)
            self.statusBar().showMessage(f"Opened {Path(path).name}")
        except Exception as exc:
            QMessageBox.critical(self, "Open failed", str(exc))

    def _on_run_module(self, module_id: str) -> None:
        if self._manager is None:
            QMessageBox.information(self, module_id, "Module manager not wired yet.")
            return
        request_cls = self._backend.get("ModuleRequest")
        manifest = self._manifest_for(module_id)
        action = self._primary_capability(manifest)
        try:
            if request_cls is not None:
                inputs = [self._doc.path] if self._doc is not None else []
                request = request_cls(action=action, input_paths=inputs)
                result = self._manager.execute(module_id, request)
                msg = getattr(result, "message", "") or "Done."
                ok = getattr(result, "success", True)
                box = QMessageBox.information if ok else QMessageBox.warning
                box(self, module_id, msg)
            else:
                QMessageBox.information(self, module_id, "Request type unavailable.")
        except Exception as exc:
            QMessageBox.critical(self, module_id, str(exc))

    # -- manifest helpers (tolerant of dataclass OR dict shapes) -------------

    def _discover_manifests(self) -> list[Any]:
        if self._manager is not None:
            try:
                return list(self._manager.list_modules())
            except Exception:
                pass
        return self._scan_manifests_on_disk()

    def _scan_manifests_on_disk(self) -> list[Any]:
        """Fallback discovery straight from modules/*/manifest.json.

        Lets the menu populate from the scaffold worker's output even before the
        ModuleManager is merged. Mirrors the manager's scan (contract 2.2).
        """
        import json

        manifests: list[Any] = []
        if not MODULES_DIR.exists():
            return manifests
        for manifest_path in sorted(MODULES_DIR.glob("mod-*/manifest.json")):
            try:
                manifests.append(json.loads(manifest_path.read_text(encoding="utf-8")))
            except Exception:
                continue
        return manifests

    def _manifest_for(self, module_id: str) -> Any:
        for manifest in self._discover_manifests():
            if self._field(manifest, "id", None) == module_id:
                return manifest
        return {}

    @staticmethod
    def _field(manifest: Any, key: str, default: Any) -> Any:
        if isinstance(manifest, dict):
            return manifest.get(key, default)
        return getattr(manifest, key, default)

    def _ui_order(self, manifest: Any) -> int:
        ui = self._field(manifest, "ui", {}) or {}
        order = ui.get("order") if isinstance(ui, dict) else getattr(ui, "order", None)
        return order if isinstance(order, int) else 999

    def _menu_label(self, manifest: Any) -> str:
        ui = self._field(manifest, "ui", {}) or {}
        label = ui.get("menu_label") if isinstance(ui, dict) else getattr(ui, "menu_label", None)
        return label or self._field(manifest, "name", "Module")

    def _primary_capability(self, manifest: Any) -> str:
        caps = self._field(manifest, "capabilities", []) or []
        return caps[0] if caps else "run"
