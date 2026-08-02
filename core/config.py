# coding: utf-8
"""
Загрузка настроек и секретов из двух yaml-файлов.

Цель:
    Собрать единый dict конфигурации без хранения паролей/токенов в git.

Файлы:
    settings.yaml  — публичные параметры (единственный yaml в git).
    secrets.yaml   — Postgres (host/port/user/password/…) и токены (НЕ в git).

Вход:
    Пути к settings и secrets (secrets можно не требовать, если logging_enabled=false).

Выход:
    dict с ключами app, game, logging; опционально testing, telegram.

Риски:
    Все *.yaml кроме settings.yaml игнорируются git — не ослаблять .gitignore.
    При logging_enabled=true полный блок logging должен быть после merge (обычно из secrets).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ALLOWED_INTERFACES = ("streamlit", "telegram", "console")
REQUIRED_GAME_KEYS = (
    "base_p",
    "noise",
    "n_per_day",
    "n_days",
    "effect_probability",
    "effect_relative_range",
    "rounds_per_session",
    "alpha",
)
REQUIRED_LOGGING_CONN_KEYS = ("host", "port", "database", "user", "password", "schema")


def _load_yaml_file(yaml_file: str | Path) -> dict[str, Any]:
    """Читает yaml целиком; пустой файл → пустой dict."""
    path = Path(yaml_file)
    with path.open("r", encoding="utf-8") as yaml_stream:
        data = yaml.full_load(yaml_stream)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Корень yaml {path!r} должен быть словарём")
    return data


def read_yaml_config(yaml_file: str | Path, section: str) -> dict[str, Any]:
    """
    Читает одну секцию из yaml-файла.

    :param yaml_file: путь к yaml
    :param section: имя секции верхнего уровня
    :return: содержимое секции как dict
    """
    descriptor = _load_yaml_file(yaml_file)
    if section not in descriptor:
        raise ValueError(f"Секция {section!r} не найдена в файле {Path(yaml_file)!r}")

    section_data = descriptor[section]
    if not isinstance(section_data, dict):
        raise ValueError(f"Секция {section!r} должна быть словарём")

    return section_data


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """
    Рекурсивно сливает override поверх base.

    Вложенные dict объединяются; остальные ключи из override заменяют base.
    """
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _validate_game_section(game_cfg: dict[str, Any]) -> None:
    """Проверяет секцию game и диапазоны параметров."""
    for key in REQUIRED_GAME_KEYS:
        if key not in game_cfg:
            raise ValueError(f"В секции game обязателен ключ {key!r}")

    base_p = float(game_cfg["base_p"])
    if not 0.0 < base_p < 1.0:
        raise ValueError(f"game.base_p должен быть в (0, 1), получено {base_p}")

    noise = float(game_cfg["noise"])
    if noise < 0.0:
        raise ValueError(f"game.noise не может быть отрицательным, получено {noise}")

    n_per_day = int(game_cfg["n_per_day"])
    if n_per_day < 1:
        raise ValueError(f"game.n_per_day должен быть >= 1, получено {n_per_day}")

    n_days = int(game_cfg["n_days"])
    if n_days < 1:
        raise ValueError(f"game.n_days должен быть >= 1, получено {n_days}")

    effect_probability = float(game_cfg["effect_probability"])
    if not 0.0 <= effect_probability <= 1.0:
        raise ValueError(
            f"game.effect_probability должен быть в [0, 1], получено {effect_probability}"
        )

    effect_relative_range = float(game_cfg["effect_relative_range"])
    if effect_relative_range < 0.0:
        raise ValueError(
            "game.effect_relative_range не может быть отрицательным, "
            f"получено {effect_relative_range}"
        )

    rounds_per_session = int(game_cfg["rounds_per_session"])
    if rounds_per_session < 1:
        raise ValueError(
            f"game.rounds_per_session должен быть >= 1, получено {rounds_per_session}"
        )

    alpha = float(game_cfg["alpha"])
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"game.alpha должен быть в (0, 1), получено {alpha}")

    difficulties = game_cfg.get("difficulties")
    if not isinstance(difficulties, dict):
        raise ValueError("В секции game обязателен словарь difficulties")
    for level in ("easy", "normal", "hard"):
        if level not in difficulties or not isinstance(difficulties[level], dict):
            raise ValueError(f"game.difficulties должен содержать пресет {level!r}")
        preset = difficulties[level]
        for key in ("noise", "effect_relative_range"):
            if key not in preset:
                raise ValueError(f"game.difficulties.{level} нужен ключ {key!r}")
            if float(preset[key]) < 0.0:
                raise ValueError(
                    f"game.difficulties.{level}.{key} не может быть отрицательным"
                )


def _validate_merged_config(cfg: dict[str, Any]) -> None:
    """Проверяет итоговый (settings ⊕ secrets) конфиг."""
    if "app" not in cfg or not isinstance(cfg["app"], dict):
        raise ValueError("Обязательна секция app в settings.yaml")
    if "game" not in cfg or not isinstance(cfg["game"], dict):
        raise ValueError("Обязательна секция game в settings.yaml")
    if "logging" not in cfg or not isinstance(cfg["logging"], dict):
        raise ValueError("Обязательна секция logging (settings и/или secrets)")

    app_cfg = cfg["app"]
    game_cfg = cfg["game"]
    logging_cfg = cfg["logging"]

    interface = app_cfg.get("interface")
    if interface not in ALLOWED_INTERFACES:
        raise ValueError(
            f"app.interface должен быть одним из {ALLOWED_INTERFACES}, получено {interface!r}"
        )

    if "logging_enabled" not in app_cfg:
        raise ValueError("В секции app обязателен ключ logging_enabled")

    _validate_game_section(game_cfg)

    if logging_cfg.get("schema") != "ab_game":
        raise ValueError("Схема логирования должна называться ab_game")

    logging_enabled = bool(app_cfg["logging_enabled"])
    if logging_enabled:
        missing = [k for k in REQUIRED_LOGGING_CONN_KEYS if not logging_cfg.get(k)]
        if missing:
            raise ValueError(
                "При logging_enabled=true в secrets.yaml (секция logging) нужны ключи: "
                + ", ".join(REQUIRED_LOGGING_CONN_KEYS)
                + f". Не хватает: {', '.join(missing)}"
            )

    if interface == "telegram":
        telegram_cfg = cfg.get("telegram") or {}
        if not isinstance(telegram_cfg, dict) or not telegram_cfg.get("token"):
            raise ValueError(
                "Для interface=telegram нужен telegram.token в secrets.yaml"
            )


def load_app_config(
    settings_file: str | Path = "settings.yaml",
    secrets_file: str | Path | None = "secrets.yaml",
) -> dict[str, Any]:
    """
    Собирает и проверяет конфигурацию: settings + secrets.

    :param settings_file: публичные настройки (в git)
    :param secrets_file: креды (не в git). None — не читать secrets.
        Если файл указан, но отсутствует: при logging_enabled=false это допустимо;
        при logging_enabled=true — FileNotFoundError.
    :return: проверенный объединённый конфиг
    """
    settings_path = Path(settings_file)
    if not settings_path.exists():
        raise FileNotFoundError(
            f"Файл {settings_path!r} не найден. Нужен settings.yaml в корне проекта."
        )

    merged = _load_yaml_file(settings_path)

    app_preview = merged.get("app") if isinstance(merged.get("app"), dict) else {}
    logging_enabled = bool(app_preview.get("logging_enabled", False))

    if secrets_file is not None:
        secrets_path = Path(secrets_file)
        if secrets_path.exists():
            secrets_data = _load_yaml_file(secrets_path)
            merged = _deep_merge(merged, secrets_data)
        elif logging_enabled:
            raise FileNotFoundError(
                f"Файл {secrets_path!r} не найден. "
                "Создайте secrets.yaml с паролями (образец в AGENTS.md / README.md)."
            )

    _validate_merged_config(merged)

    result: dict[str, Any] = {
        "app": merged["app"],
        "game": merged["game"],
        "logging": merged["logging"],
    }
    if isinstance(merged.get("testing"), dict):
        result["testing"] = merged["testing"]
    if isinstance(merged.get("telegram"), dict):
        result["telegram"] = merged["telegram"]

    return result
