"""Tests for application configuration loading and persistence."""

from __future__ import annotations

from ui.config_loader import (
    builtin_defaults,
    load_app_config,
    normalize_config,
    reset_app_config,
    save_app_config,
)


def test_normalize_config_clamps_limits() -> None:
    config = normalize_config(
        {
            "recent_files_limit": 100,
            "prerender_buffer_pages": 0,
            "render_dpi": 150,
        }
    )
    assert config["recent_files_limit"] == 50
    assert config["prerender_buffer_pages"] == 1
    assert config["render_dpi"] == 144


def test_save_and_load_round_trip(monkeypatch, tmp_path) -> None:
    import ui.config_loader as config_loader

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "defaults.json"
    monkeypatch.setattr(config_loader, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config_loader, "_CONFIG_PATH", config_path)

    save_app_config(
        {
            "language": "fr",
            "theme": "light",
            "default_zoom": "fit_width",
            "render_dpi": 300,
            "enable_error_log": True,
        }
    )
    loaded = load_app_config()
    assert loaded["language"] == "fr"
    assert loaded["theme"] == "light"
    assert loaded["default_zoom"] == "fit_width"
    assert loaded["render_dpi"] == 300
    assert loaded["enable_error_log"] is True


def test_reset_app_config_restores_defaults(monkeypatch, tmp_path) -> None:
    import ui.config_loader as config_loader

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "defaults.json"
    monkeypatch.setattr(config_loader, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config_loader, "_CONFIG_PATH", config_path)

    save_app_config({"language": "de", "theme": "system"})
    reset = reset_app_config()
    assert reset == load_app_config()
    assert reset["language"] == builtin_defaults()["language"]
    assert reset["theme"] == builtin_defaults()["theme"]
