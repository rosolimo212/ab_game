# coding: utf-8
"""Тесты калибровки раунда под флаг эффекта."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from core.config import load_app_config
from core.generator import generate_round
from core.stats import z_test_round

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = ROOT / "settings.yaml"


def _game():
    return dict(load_app_config(SETTINGS, secrets_file=None)["game"])


def test_calibrate_want_effect_matches_z_test() -> None:
    game = _game()
    game["effect_probability"] = 1.0
    rng = np.random.default_rng(7)
    aligned = 0
    n = 40
    for _ in range(n):
        rd = generate_round(game, rng=rng)
        assert rd.has_effect is True
        zt = z_test_round(rd, alpha=float(game["alpha"]))
        if zt.significant:
            aligned += 1
    assert aligned / n >= 0.85


def test_calibrate_want_null_matches_z_test() -> None:
    game = _game()
    game["effect_probability"] = 0.0
    rng = np.random.default_rng(11)
    aligned = 0
    n = 40
    for _ in range(n):
        rd = generate_round(game, rng=rng)
        assert rd.has_effect is False
        zt = z_test_round(rd, alpha=float(game["alpha"]))
        if not zt.significant:
            aligned += 1
    assert aligned / n >= 0.9


def test_without_calibrate_flag_may_diverge() -> None:
    """Контроль: без калибровки флаг — только про сдвиг генератора."""
    game = _game()
    game["effect_probability"] = 1.0
    game["effect_relative_range"] = 0.05
    game["noise"] = 0.15
    rng = np.random.default_rng(3)
    rd = generate_round(game, rng=rng, calibrate=False)
    assert rd.has_effect is True
    assert rd.calibrate_steps == 0
