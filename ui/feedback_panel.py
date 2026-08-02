# coding: utf-8
"""
Сводка метрик раунда под графиком (экран FEEDBACK).

Тексты шаблонов — только из data/dialog_messages.json.
"""

from __future__ import annotations

from core.format_text import fmt_p_value, fmt_pct, fmt_signed_pct_points
from core.messages import message
from core.models import RoundData, ZTestResult


def format_feedback_stats(
    round_data: RoundData,
    z_result: ZTestResult,
    *,
    channel: str = "streamlit",
) -> str:
    """
    Текст под графиком: целевые / фактические средние (%), разница, p-value.

    Целевое — true_p ветки (до дневного шума).
    Фактическое — пулырованная доля по наблюдениям (с шумом и выборкой).
    """
    target_a = round_data.branch_a.true_p
    target_b = round_data.branch_b.true_p
    actual_a = round_data.branch_a.pooled_rate
    actual_b = round_data.branch_b.pooled_rate

    if actual_a > 0.0:
        diff_line = message(
            "feedback_stats_diff",
            channel,
            diff_pct=fmt_signed_pct_points((actual_b - actual_a) / actual_a),
        )
    else:
        diff_line = message("feedback_stats_diff_na", channel)

    return message(
        "feedback_stats",
        channel,
        target_a=fmt_pct(target_a),
        actual_a=fmt_pct(actual_a),
        target_b=fmt_pct(target_b),
        actual_b=fmt_pct(actual_b),
        diff_line=diff_line,
        p_value=fmt_p_value(z_result.p_value),
    )
