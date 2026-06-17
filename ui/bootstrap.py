"""Runtime wiring helpers for the UI shell.

The ``module-manager/`` directory is hyphenated and therefore NOT importable as a
normal Python package (intent-contract Section 2.1). The UI loads ``ModuleManager``
and the plugin API via ``importlib.util.spec_from_file_location`` against the repo
root, exactly as the contract mandates. All access here is read-only against the
backend worker's call surfaces — the UI never reaches into the manager internals.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

# repo root = parent of the ui/ package directory.
REPO_ROOT: Path = Path(__file__).resolve().parent.parent
MODULES_DIR: Path = REPO_ROOT / "modules"
MODULE_MANAGER_DIR: Path = REPO_ROOT / "module-manager"


def _load_path_module(name: str, file_path: Path) -> ModuleType:
    """Load a single .py file by filesystem path (contract Section 2.1)."""
    spec = importlib.util.spec_from_file_location(name, file_path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"cannot load {name} from {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_backend() -> dict[str, Any]:
    """Return the backend call surfaces the UI needs.

    Tolerant by design: the backend worker runs in the SAME wave and may not be
    merged yet. Missing pieces degrade to ``None`` so the window still opens.
    """
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    surfaces: dict[str, Any] = {
        "PDFEngine": None,
        "ModuleManager": None,
        "ModuleRequest": None,
    }

    try:
        from core.pdf_engine import PDFEngine  # type: ignore

        surfaces["PDFEngine"] = PDFEngine
    except Exception:  # pragma: no cover - backend not merged yet
        pass

    manager_file = MODULE_MANAGER_DIR / "manager.py"
    plugin_api_file = MODULE_MANAGER_DIR / "plugin_api.py"
    try:
        if plugin_api_file.exists():
            plugin_api = _load_path_module("freepdf_plugin_api", plugin_api_file)
            surfaces["ModuleRequest"] = getattr(plugin_api, "ModuleRequest", None)
        if manager_file.exists():
            manager_mod = _load_path_module("freepdf_module_manager", manager_file)
            surfaces["ModuleManager"] = getattr(manager_mod, "ModuleManager", None)
    except Exception:  # pragma: no cover - backend not merged yet
        pass

    return surfaces
