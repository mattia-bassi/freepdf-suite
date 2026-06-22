"""Load application configuration from ``config/defaults.json``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .bootstrap import CONFIG_DIR

_DEFAULTS: dict[str, Any] = {
    "theme": "dark",
    "language": "en",
    "default_folder": "",
    "recent_files_limit": 10,
    "open_last_file_on_startup": False,
    "default_zoom": "1.0",
    "default_view_mode": "continuous_scroll",
    "show_thumbnails_on_startup": True,
    "render_dpi": 96,
    "encrypted_pdf": "always_ask",
    "p7m_files": "always_extract",
    "missing_fonts": "use_substitutes",
    "prerender_buffer_pages": 2,
    "rendering_quality": "normal",
    "enable_error_log": False,
    "zoom_default": 1.0,
}

_ALLOWED_RENDER_DPI = (72, 96, 144, 300)
_CONFIG_PATH = CONFIG_DIR / "defaults.json"


def builtin_defaults() -> dict[str, Any]:
    """Return a copy of built-in default settings."""
    return dict(_DEFAULTS)


def recent_files_path() -> Path:
    """Path to the persisted recent-files JSON store."""
    return CONFIG_DIR / "recent_files.json"


def _closest_render_dpi(value: int) -> int:
    return min(_ALLOWED_RENDER_DPI, key=lambda dpi: abs(dpi - value))


def normalize_config(config: dict[str, Any]) -> dict[str, Any]:
    """Validate and coerce configuration values."""
    merged = dict(_DEFAULTS)
    merged.update(config)

    theme = str(merged.get("theme", "dark")).lower()
    if theme not in {"dark", "light", "system"}:
        theme = "dark"
    merged["theme"] = theme

    merged["language"] = str(merged.get("language", "en"))
    merged["default_folder"] = str(merged.get("default_folder", ""))
    merged["recent_files_limit"] = max(
        5, min(50, int(merged.get("recent_files_limit", 10)))
    )
    merged["open_last_file_on_startup"] = bool(
        merged.get("open_last_file_on_startup", False)
    )

    default_zoom = merged.get("default_zoom")
    if default_zoom is None and "zoom_default" in merged:
        zoom_value = float(merged.get("zoom_default", 1.0))
        default_zoom = (
            f"{zoom_value:g}"
            if zoom_value not in (0.5, 0.75, 1.25, 1.5, 2.0)
            else str(zoom_value)
        )
    default_zoom = str(default_zoom if default_zoom is not None else "1.0")
    if default_zoom not in {
        "fit_page",
        "fit_width",
        "0.5",
        "0.75",
        "1.0",
        "1.25",
        "1.5",
        "2.0",
    }:
        try:
            default_zoom = f"{float(default_zoom):g}"
        except (TypeError, ValueError):
            default_zoom = "1.0"
    merged["default_zoom"] = default_zoom
    if default_zoom in {"fit_page", "fit_width"}:
        merged["zoom_default"] = float(merged.get("zoom_default", 1.0))
    else:
        merged["zoom_default"] = max(0.1, min(4.0, float(default_zoom)))

    view_mode = str(merged.get("default_view_mode", "continuous_scroll"))
    if view_mode not in {"single_page", "continuous_scroll"}:
        view_mode = "continuous_scroll"
    merged["default_view_mode"] = view_mode
    merged["show_thumbnails_on_startup"] = bool(
        merged.get("show_thumbnails_on_startup", True)
    )
    merged["render_dpi"] = _closest_render_dpi(int(merged.get("render_dpi", 96)))

    encrypted = str(merged.get("encrypted_pdf", "always_ask"))
    if encrypted not in {"always_ask", "remember_password"}:
        encrypted = "always_ask"
    merged["encrypted_pdf"] = encrypted

    p7m_mode = str(merged.get("p7m_files", "always_extract"))
    if p7m_mode not in {"always_extract", "ask_confirmation"}:
        p7m_mode = "always_extract"
    merged["p7m_files"] = p7m_mode

    missing_fonts = str(merged.get("missing_fonts", "use_substitutes"))
    if missing_fonts not in {"use_substitutes", "show_warning"}:
        missing_fonts = "use_substitutes"
    merged["missing_fonts"] = missing_fonts

    merged["prerender_buffer_pages"] = max(
        1,
        min(10, int(merged.get("prerender_buffer_pages", 2))),
    )

    quality = str(merged.get("rendering_quality", "normal"))
    if quality not in {"normal", "high"}:
        quality = "normal"
    merged["rendering_quality"] = quality
    merged["enable_error_log"] = bool(merged.get("enable_error_log", False))
    return merged


def load_app_config() -> dict[str, Any]:
    """Return merged application settings (file overrides built-in defaults)."""
    if not _CONFIG_PATH.is_file():
        return normalize_config({})
    try:
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return normalize_config({})
    if not isinstance(data, dict):
        return normalize_config({})
    return normalize_config(data)


def save_app_config(updates: dict[str, Any]) -> None:
    """Persist configuration updates to ``config/defaults.json``."""
    config = load_app_config()
    config.update(updates)
    _write_config(normalize_config(config))


def reset_app_config() -> dict[str, Any]:
    """Restore built-in defaults and persist them."""
    config = normalize_config(dict(_DEFAULTS))
    _write_config(config)
    return config


def _write_config(config: dict[str, Any]) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
