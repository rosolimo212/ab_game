# coding: utf-8
"""Тесты загрузки настроек и секретов."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from core.config import load_app_config, read_yaml_config

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = ROOT / "settings.yaml"
SECRETS_EXAMPLE = ROOT / "secrets.example.yaml"


def test_read_yaml_config_app_section() -> None:
    app_cfg = read_yaml_config(SETTINGS, "app")
    assert app_cfg["interface"] == "streamlit"
    assert "logging_enabled" in app_cfg


def test_load_settings_without_secrets_when_logging_disabled() -> None:
    config = load_app_config(SETTINGS, secrets_file=None)
    assert config["logging"]["schema"] == "ab_game"
    assert config["game"]["n_days"] == 14
    assert config["game"]["rounds_per_session"] == 20
    assert config["game"]["alpha"] == 0.05
    assert "password" not in config["logging"]


def test_load_settings_plus_secrets_example(tmp_path: Path) -> None:
    secrets_path = tmp_path / "secrets.yaml"
    secrets_path.write_text(SECRETS_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")

    # Временно включаем logging, чтобы проверить требование password.
    settings_data = yaml.safe_load(SETTINGS.read_text(encoding="utf-8"))
    settings_data["app"]["logging_enabled"] = True
    settings_path = tmp_path / "settings.yaml"
    settings_path.write_text(yaml.dump(settings_data), encoding="utf-8")

    config = load_app_config(settings_path, secrets_path)
    assert config["logging"]["password"] == "YOUR_PASSWORD_HERE"
    assert config["logging"]["schema"] == "ab_game"
    assert config["testing"]["password"] == "YOUR_TESTER_PASSWORD_HERE"


def test_logging_enabled_requires_secrets_file(tmp_path: Path) -> None:
    settings_data = yaml.safe_load(SETTINGS.read_text(encoding="utf-8"))
    settings_data["app"]["logging_enabled"] = True
    settings_path = tmp_path / "settings.yaml"
    settings_path.write_text(yaml.dump(settings_data), encoding="utf-8")

    with pytest.raises(FileNotFoundError):
        load_app_config(settings_path, tmp_path / "missing_secrets.yaml")


def test_load_app_config_missing_settings() -> None:
    with pytest.raises(FileNotFoundError):
        load_app_config(ROOT / "no_such_settings.yaml", secrets_file=None)
