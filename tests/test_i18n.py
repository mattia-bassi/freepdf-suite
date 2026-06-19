"""Tests for dict-based UI translations."""

from __future__ import annotations

from ui.i18n import apply_language, init_language, set_language, tr


def test_tr_returns_english_by_default() -> None:
    set_language("en")
    assert tr("open") == "Open"
    assert tr("file") == "File"


def test_tr_italian() -> None:
    set_language("it")
    assert tr("open") == "Apri"
    assert tr("ready_open_pdf") == "Pronto"
    assert tr("general_settings") == "Impostazioni generali"
    assert tr("view_settings") == "Visualizzazione"
    assert tr("advanced") == "Avanzate"
    assert tr("reset_defaults") == "Ripristina predefiniti"
    assert tr("encrypted_pdf") == "PDF Crittografati"
    assert tr("remember_password") == "Ricorda la password"
    assert tr("use_substitutes") == "Usa font sostitutivi"
    set_language("en")


def test_tr_falls_back_to_english_for_unknown_key() -> None:
    set_language("de")
    assert tr("unknown_key") == "unknown_key"
    set_language("en")


def test_apply_language_updates_active_code() -> None:
    apply_language("fr")
    assert tr("file") == "Fichier"
    apply_language("en")


def test_init_language_reads_config(monkeypatch, tmp_path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "defaults.json"
    config_path.write_text('{"language": "es"}', encoding="utf-8")

    import ui.config_loader as config_loader

    monkeypatch.setattr(config_loader, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config_loader, "_CONFIG_PATH", config_path)

    assert init_language() == "es"
    assert tr("open") == "Abrir"
    set_language("en")
