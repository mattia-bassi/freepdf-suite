"""Module discovery & lifecycle manager (contract §6.6).

Discovery = scan ``modules/*/manifest.json`` (contract §2.2). Loading resolves
each manifest's ``entry_point`` (``file_stem:ClassName``) via ``importlib`` from
the module's own directory. Hyphen/digit dir names are never statically imported.

Canonical access helper: this file is loaded by the app with
``importlib.util.spec_from_file_location`` because ``module-manager`` is not an
importable package name (contract §2.1).
"""

from __future__ import annotations

import importlib.util
import json
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from core.errors import (
    ManifestError,
    ModuleExecutionError,
    ModuleLoadError,
    ModuleNotFoundError,
)

# WIRING (Wave-3 Integrator): this file is loaded by path via
# ``spec_from_file_location`` (contract §2.1), so its sibling modules are NOT on
# ``sys.path``. Make this directory importable so the bare sibling imports below
# resolve regardless of who loads us. No signatures/APIs change.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from manifest_schema import ModuleManifest, validate_manifest  # noqa: E402
from plugin_api import ModulePlugin, ModuleRequest, ModuleResult  # noqa: E402

if TYPE_CHECKING:
    from core.pdf_engine import PDFEngine

_log = logging.getLogger("freepdf.manager")


class ModuleManager:
    def __init__(self, modules_dir: str | Path, engine: "PDFEngine") -> None:
        self._modules_dir = Path(modules_dir)
        self._engine = engine
        self._manifests: dict[str, ModuleManifest] = {}
        self._plugins: dict[str, ModulePlugin] = {}

    def discover(self) -> list[ModuleManifest]:
        """Scan ``modules/*/manifest.json``; skip invalid ones (logged)."""
        self._manifests.clear()
        if not self._modules_dir.is_dir():
            _log.warning("modules dir not found: %s", self._modules_dir)
            return []
        for manifest_path in sorted(self._modules_dir.glob("*/manifest.json")):
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest = validate_manifest(data)
            except (OSError, json.JSONDecodeError, ManifestError) as exc:
                _log.warning("ManifestError: skipping %s (%s)", manifest_path, exc)
                continue
            if manifest.id in self._manifests:
                _log.warning("duplicate module id %s; keeping first", manifest.id)
                continue
            self._manifests[manifest.id] = manifest
        return list(self._manifests.values())

    def list_modules(self) -> list[ModuleManifest]:
        if not self._manifests:
            self.discover()
        return list(self._manifests.values())

    def load(self, module_id: str) -> ModulePlugin:
        if module_id in self._plugins:
            return self._plugins[module_id]
        manifest = self._manifest_for(module_id)
        plugin = self._instantiate(manifest)
        self._plugins[module_id] = plugin
        return plugin

    def load_all(self) -> dict[str, ModulePlugin]:
        for manifest in self.list_modules():
            try:
                self.load(manifest.id)
            except ModuleLoadError as exc:
                _log.warning("ModuleLoadError: %s (%s)", manifest.id, exc)
        return dict(self._plugins)

    def get(self, module_id: str) -> ModulePlugin:
        if module_id not in self._plugins:
            return self.load(module_id)
        return self._plugins[module_id]

    def execute(self, module_id: str, request: ModuleRequest) -> ModuleResult:
        """Run a module action, wrapping any escaped exception (contract §8)."""
        try:
            plugin = self.get(module_id)
        except (ModuleNotFoundError, ModuleLoadError) as exc:
            return ModuleResult.fail(getattr(exc, "error_code", "MODULE_ERROR"), str(exc))
        try:
            return plugin.execute(request)
        except Exception as exc:  # noqa: BLE001 - boundary guard
            _log.exception("module %s execution failed", module_id)
            return ModuleResult.fail("MODULE_EXECUTION_ERROR", str(exc))

    # --- internals ----------------------------------------------------------
    def _manifest_for(self, module_id: str) -> ModuleManifest:
        if not self._manifests:
            self.discover()
        manifest = self._manifests.get(module_id)
        if manifest is None:
            raise ModuleNotFoundError(f"No module with id {module_id!r}.")
        return manifest

    def _instantiate(self, manifest: ModuleManifest) -> ModulePlugin:
        mod_dir = self._modules_dir / manifest.id
        entry_file = mod_dir / f"{manifest.entry_file}.py"
        if not entry_file.is_file():
            # Wave-2 stub tolerance (contract §5): skip cleanly, don't crash.
            raise ModuleLoadError(f"entry-point file missing: {entry_file}")

        spec = importlib.util.spec_from_file_location(
            f"freepdf_module_{manifest.id.replace('-', '_')}", entry_file
        )
        if spec is None or spec.loader is None:
            raise ModuleLoadError(f"cannot create import spec for {entry_file}")
        py_module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(py_module)
        except Exception as exc:  # noqa: BLE001
            raise ModuleLoadError(f"importing {entry_file} failed: {exc}") from exc

        cls = getattr(py_module, manifest.entry_class, None)
        if cls is None or not isinstance(cls, type) or not issubclass(cls, ModulePlugin):
            raise ModuleLoadError(
                f"{manifest.entry_class} in {entry_file} is not a ModulePlugin subclass."
            )

        try:
            plugin: ModulePlugin = cls()
        except Exception as exc:  # noqa: BLE001
            raise ModuleLoadError(f"instantiating {manifest.entry_class} failed: {exc}") from exc

        # Populate manager-managed fields from the manifest (contract §6.5).
        plugin.id = manifest.id
        plugin.name = manifest.name
        plugin.version = manifest.version
        plugin._capabilities = list(manifest.capabilities)  # type: ignore[attr-defined]
        return plugin
