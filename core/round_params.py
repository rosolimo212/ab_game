# coding: utf-8
"""Сериализация раунда для ab_game.round_parameters."""

from __future__ import annotations

from typing import Any

from core.models import BranchSeries, RoundData, ZTestResult


def branch_to_series_rows(branch: BranchSeries) -> list[dict[str, Any]]:
    """Дневные точки ветки для JSONB."""
    return [
        {
            "day": point.day,
            "numerator": point.numerator,
            "denominator": point.denominator,
            "rate": point.rate,
        }
        for point in branch.points
    ]


def round_series_payload(round_data: RoundData) -> dict[str, Any]:
    """{"A": [...], "B": [...]} — значения графика."""
    return {
        "A": branch_to_series_rows(round_data.branch_a),
        "B": branch_to_series_rows(round_data.branch_b),
    }


def round_parameters_row(
    round_data: RoundData,
    z_result: ZTestResult,
    *,
    round_index: int,
    difficulty: str,
    noise: float,
) -> dict[str, Any]:
    """Поля строки round_parameters (без user_id / времени)."""
    want = bool(round_data.has_effect)
    significant = bool(z_result.significant)
    return {
        "round_index": round_index,
        "difficulty": difficulty,
        "noise": noise,
        "base_p": float(round_data.base_p),
        "target_a": float(round_data.branch_a.true_p),
        "target_b": float(round_data.branch_b.true_p),
        "want_effect": want,
        "p_value": float(z_result.p_value),
        "significant": significant,
        "aligned": want is significant,
        "calibrate_steps": int(round_data.calibrate_steps),
        "series": round_series_payload(round_data),
    }
