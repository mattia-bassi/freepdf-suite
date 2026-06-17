"""The plugin contract every module implements (contract §6.5).

This is the single stable interface modules are written against. Do NOT change
its signatures in later waves.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # avoid importing core at module import time (one-way dep)
    from core.pdf_engine import PDFEngine


class ModuleCategory(str, Enum):
    VIEW = "view"
    ORGANIZE = "organize"
    OPTIMIZE = "optimize"
    CONVERT = "convert"
    ENHANCE = "enhance"
    EDIT = "edit"
    SECURITY = "security"
    EXTRACT = "extract"


@dataclass
class ModuleContext:
    engine: "PDFEngine"  # injected core engine instance
    config: dict[str, Any]  # merged app + module config
    workspace: Path  # scratch dir for temp output
    # logger is obtained via logging.getLogger(f"freepdf.{module_id}")


@dataclass
class ModuleRequest:
    action: str  # one of the module's capability keys
    input_paths: list[Path] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModuleResult:
    success: bool
    message: str = ""
    output_paths: list[Path] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None  # set when success is False (see core.errors §8)

    @classmethod
    def ok(
        cls,
        *,
        message: str = "",
        output_paths: list[Path] | None = None,
        data: dict[str, Any] | None = None,
    ) -> "ModuleResult":
        return cls(
            success=True,
            message=message,
            output_paths=list(output_paths or []),
            data=dict(data or {}),
        )

    @classmethod
    def fail(cls, error_code: str, message: str) -> "ModuleResult":
        return cls(success=False, message=message, error_code=error_code)


class ModulePlugin(ABC):
    # populated by the manager from the manifest at load time
    id: str
    name: str
    version: str

    @abstractmethod
    def setup(self, context: ModuleContext) -> None: ...

    @abstractmethod
    def execute(self, request: ModuleRequest) -> ModuleResult: ...

    def teardown(self) -> None:  # optional override, default no-op
        return None

    def capabilities(self) -> list[str]:  # default reads from manifest
        return list(getattr(self, "_capabilities", []))
