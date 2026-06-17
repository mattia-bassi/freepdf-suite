"""Wave-3 Integrator end-to-end smoke tests.

Exercises the cross-layer wiring the contract pins down (intent-contract §2, §6,
§8) WITHOUT requiring optional/runtime deps that may be absent in CI:

* PyMuPDF (``fitz``) is imported lazily by ``core.pdf_engine`` and is NOT needed
  to import the engine or run these checks.
* Qt (PySide6) and a display are NOT touched here.

The ``module-manager/`` package is hyphenated, so it is loaded by filesystem path
via ``importlib.util.spec_from_file_location`` exactly as the UI shell loads it
(contract §2.1). This guards against the sibling-import regression fixed in Wave 3.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_MANAGER_DIR = REPO_ROOT / "module-manager"


def _load_by_path(name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(name, file_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_core_exports_and_version() -> None:
    import core

    assert core.__version__ == "0.1.0"
    assert core.PDFEngine.DEFAULT_DPI == 150
    # FormatHandler imports without the optional crypto/fitz deps present.
    assert core.FormatHandler is not None


def test_error_hierarchy_codes() -> None:
    from core import errors

    assert issubclass(errors.DocumentOpenError, errors.FreePDFError)
    assert errors.ManifestError.error_code == "MANIFEST_ERROR"
    assert errors.ModuleExecutionError.error_code == "MODULE_EXECUTION_ERROR"


def test_manifest_validation_roundtrip() -> None:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    schema = _load_by_path(
        "freepdf_manifest_schema", MODULE_MANAGER_DIR / "manifest_schema.py"
    )
    manifest = schema.validate_manifest(
        {
            "id": "mod-02",
            "name": "Merge",
            "version": "0.1.0",
            "category": "organize",
            "entry_point": "plugin:MergePlugin",
            "min_core_version": "0.1.0",
            "capabilities": ["merge_documents"],
        }
    )
    assert manifest.entry_file == "plugin"
    assert manifest.entry_class == "MergePlugin"


def test_manager_loads_by_path_and_degrades_gracefully() -> None:
    """Regression guard: manager.py must import via spec_from_file_location.

    Its sibling imports (manifest_schema, plugin_api) are resolved by the
    Wave-3 sys.path shim, not by the loader placing the dir on the path.
    """
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    plugin_api = _load_by_path(
        "freepdf_plugin_api", MODULE_MANAGER_DIR / "plugin_api.py"
    )
    manager_mod = _load_by_path(
        "freepdf_module_manager", MODULE_MANAGER_DIR / "manager.py"
    )

    from core import PDFEngine

    manager = manager_mod.ModuleManager(REPO_ROOT / "modules", PDFEngine())
    # No mod-NN scaffolds present yet -> empty, no crash (contract §2.3 tolerance).
    assert manager.discover() == []
    assert manager.list_modules() == []

    result = manager.execute("mod-99", plugin_api.ModuleRequest(action="noop"))
    assert result.success is False
    assert result.error_code == "MODULE_NOT_FOUND_ERROR"
