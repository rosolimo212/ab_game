# coding: utf-8
"""
Уровни сложности игры.

лёгкий — большая разница метрик, низкий шум;
нормальный — базовые параметры из game;
тяжёлый — малая разница, высокий шум.
"""

from __future__ import annotations

from typing import Any, Mapping

DIFFICULTY_EASY = "easy"
DIFFICULTY_NORMAL = "normal"
DIFFICULTY_HARD = "hard"

DIFFICULTY_LABELS = {
    DIFFICULTY_EASY: "лёгкий",
    DIFFICULTY_NORMAL: "нормальный",
    DIFFICULTY_HARD: "тяжёлый",
}

DIFFICULTY_KEYS = (DIFFICULTY_EASY, DIFFICULTY_NORMAL, DIFFICULTY_HARD)


def resolve_game_cfg(
    game_cfg: Mapping[str, Any],
    difficulty: str,
) -> dict[str, Any]:
    """
    Собирает параметры генератора для выбранной сложности.

    Берёт game.* и перекрывает noise / effect_relative_range из game.difficulties.
    """
    if difficulty not in DIFFICULTY_KEYS:
        raise ValueError(f"Неизвестная сложность: {difficulty!r}")

    merged = dict(game_cfg)
    difficulties = game_cfg.get("difficulties") or {}
    if not isinstance(difficulties, dict) or difficulty not in difficulties:
        raise ValueError(f"В game.difficulties нет уровня {difficulty!r}")

    preset = difficulties[difficulty]
    if not isinstance(preset, dict):
        raise ValueError(f"Пресет сложности {difficulty!r} должен быть словарём")

    for key in ("noise", "effect_relative_range"):
        if key not in preset:
            raise ValueError(f"В пресете {difficulty!r} нужен ключ {key!r}")
        merged[key] = preset[key]

    merged["difficulty"] = difficulty
    return merged


def difficulty_label(difficulty: str) -> str:
    """Русская подпись уровня."""
    return DIFFICULTY_LABELS.get(difficulty, difficulty)
