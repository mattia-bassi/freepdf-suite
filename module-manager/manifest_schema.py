"""Manifest dataclass + JSON-Schema validator (contract §5 / §6.6).

``validate_manifest(data)`` validates a parsed ``manifest.json`` dict against the
draft-2020-12 schema and returns a typed ``ModuleManifest``. Raises
``ManifestError`` on any violation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# core.errors is importable: module-manager depends on core only (contract §2.4).
from core.errors import ManifestError

CATEGORIES = (
    "view",
    "organize",
    "optimize",
    "convert",
    "enhance",
    "edit",
    "security",
    "extract",
)

_ID_RE = re.compile(r"^mod-[0-9]{2}$")
_SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_ENTRY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*:[A-Za-z_][A-Za-z0-9_]*$")

MANIFEST_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": [
        "id",
        "name",
        "version",
        "category",
        "entry_point",
        "min_core_version",
    ],
    "additionalProperties": False,
    "properties": {
        "id": {"type": "string", "pattern": "^mod-[0-9]{2}$"},
        "name": {"type": "string", "minLength": 1},
        "version": {"type": "string", "pattern": r"^[0-9]+\.[0-9]+\.[0-9]+$"},
        "description": {"type": "string"},
        "category": {"enum": list(CATEGORIES)},
        "entry_point": {"type": "string"},
        "capabilities": {"type": "array", "items": {"type": "string"}},
        "dependencies": {"type": "array", "items": {"type": "string"}},
        "min_core_version": {
            "type": "string",
            "pattern": r"^[0-9]+\.[0-9]+\.[0-9]+$",
        },
        "author": {"type": "string"},
        "license": {"type": "string"},
        "ui": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "menu_label": {"type": "string"},
                "icon": {"type": "string"},
                "order": {"type": "integer"},
            },
        },
    },
}


@dataclass(frozen=True)
class ModuleManifest:
    id: str
    name: str
    version: str
    category: str
    entry_point: str
    min_core_version: str
    description: str = ""
    capabilities: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    author: str = ""
    license: str = "MIT"
    ui: dict[str, Any] = field(default_factory=dict)

    @property
    def entry_file(self) -> str:
        """The ``<file_stem>`` part of ``entry_point`` (no extension)."""
        return self.entry_point.split(":", 1)[0]

    @property
    def entry_class(self) -> str:
        """The ``<ClassName>`` part of ``entry_point``."""
        return self.entry_point.split(":", 1)[1]


_REQUIRED = MANIFEST_SCHEMA["required"]
_ALLOWED = set(MANIFEST_SCHEMA["properties"])


def validate_manifest(data: dict[str, Any]) -> ModuleManifest:
    """Validate ``data`` and return a ``ModuleManifest`` or raise ``ManifestError``."""
    if not isinstance(data, dict):
        raise ManifestError(f"Manifest must be a JSON object, got {type(data).__name__}.")

    extra = set(data) - _ALLOWED
    if extra:
        raise ManifestError(f"Unknown manifest keys: {sorted(extra)}.")

    missing = [k for k in _REQUIRED if k not in data]
    if missing:
        raise ManifestError(f"Manifest missing required keys: {missing}.")

    _check_str(data, "id", _ID_RE)
    if not (isinstance(data["name"], str) and data["name"]):
        raise ManifestError("`name` must be a non-empty string.")
    _check_str(data, "version", _SEMVER_RE)
    _check_str(data, "min_core_version", _SEMVER_RE)

    if data["category"] not in CATEGORIES:
        raise ManifestError(
            f"`category` must be one of {CATEGORIES}, got {data['category']!r}."
        )

    if not (isinstance(data["entry_point"], str) and _ENTRY_RE.match(data["entry_point"])):
        raise ManifestError(
            f"`entry_point` must look like 'file_stem:ClassName', got "
            f"{data['entry_point']!r}."
        )

    caps = data.get("capabilities", [])
    deps = data.get("dependencies", [])
    _check_str_list(caps, "capabilities")
    _check_str_list(deps, "dependencies")
    for dep in deps:
        if not _ID_RE.match(dep):
            raise ManifestError(f"dependency {dep!r} is not a valid mod-NN id.")

    ui = data.get("ui", {})
    if not isinstance(ui, dict):
        raise ManifestError("`ui` must be an object.")

    return ModuleManifest(
        id=data["id"],
        name=data["name"],
        version=data["version"],
        category=data["category"],
        entry_point=data["entry_point"],
        min_core_version=data["min_core_version"],
        description=data.get("description", ""),
        capabilities=list(caps),
        dependencies=list(deps),
        author=data.get("author", ""),
        license=data.get("license", "MIT"),
        ui=dict(ui),
    )


def _check_str(data: dict[str, Any], key: str, pattern: re.Pattern[str]) -> None:
    value = data[key]
    if not (isinstance(value, str) and pattern.match(value)):
        raise ManifestError(f"`{key}` {value!r} does not match {pattern.pattern}.")


def _check_str_list(value: Any, key: str) -> None:
    if not (isinstance(value, list) and all(isinstance(i, str) for i in value)):
        raise ManifestError(f"`{key}` must be an array of strings.")
