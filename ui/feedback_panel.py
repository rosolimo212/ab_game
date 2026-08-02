# coding: utf-8
"""
Сводка метрик раунда для панели рядом с графиком (экран FEEDBACK).
"""

from __future__ import annotations

from core.models import RoundData, ZTestResult


def format_feedback_stats(round_data: RoundData, z_result: ZTestResult) -> str:
    """
    Текст панели: целевые / фактические средние, относительная разница, p-value.

    Целевое — true_p ветки (до дневного шума).
    Фактическое — пулырованная доля по наблюдениям (с шумом и выборкой).
    """
    target_a = round_data.branch_a.true_p
    target_b = round_data.branch_b.true_p
    actual_a = round_data.branch_a.pooled_rate
    actual_b = round_data.branch_b.pooled_rate

    if actual_a > 0.0:
        diff_pct = 100.0 * (actual_b - actual_a) / actual_a
        diff_line = f"{diff_pct:+.1f}% относительно A"
    else:
        diff_line = "н/д (среднее A = 0)"

    return (
        "**Метрики раунда**\n\n"
        f"**A** — целевое: `{target_a:.4f}`, фактическое: `{actual_a:.4f}`\n\n"
        f"**B** — целевое: `{target_b:.4f}`, фактическое: `{actual_b:.4f}`\n\n"
        f"**Разница (факт.)**: {diff_line}\n\n"
        f"**p-value (z-тест)**: `{z_result.p_value:.4g}`"
    )
