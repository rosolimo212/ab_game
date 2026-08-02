# coding: utf-8
"""Тесты пресетов сложности."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.config import load_app_config
from core.difficulty import (
    DIFFICULTY_EASY,
    DIFFICULTY_HARD,
    DIFFICULTY_NORMAL,
    resolve_game_cfg,
)


def test_resolve_game_cfg_overrides_noise_and_range() -> None:
    root = Path(__file__).resolve().parents[1]
    game = load_app_config(root / "settings.yaml", None)["game"]

    easy = resolve_game_cfg(game, DIFFICULTY_EASY)
    hard = resolve_game_cfg(game, DIFFICULTY_HARD)
    normal = resolve_game_cfg(game, DIFFICULTY_NORMAL)

    assert easy["noise"] < normal["noise"] < hard["noise"]
    assert easy["effect_relative_range"] > normal["effect_relative_range"]
    # hard: шум выше, но сдвиг эффекта не меньше normal — иначе z-тест почти всегда null
    assert hard["effect_relative_range"] >= normal["effect_relative_range"]
    assert abs(float(hard["effect_probability"]) - 0.5) < 1e-9
    assert easy["base_p"] == game["base_p"]
    assert "base_p_min" in hard and "base_p_max" in hard


def test_resolve_unknown_difficulty() -> None:
    root = Path(__file__).resolve().parents[1]
    game = load_app_config(root / "settings.yaml", None)["game"]
    with pytest.raises(ValueError, match="Неизвестная"):
        resolve_game_cfg(game, "nightmare")
