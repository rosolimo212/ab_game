# coding: utf-8
"""
Форматирование чисел для UI (проценты, p-value).

Все user-facing шаблоны фраз — в data/dialog_messages.json;
здесь только числа.
"""

from __future__ import annotations


def fmt_pct(rate: float, *, decimals: int = 2) -> str:
    """
    Доля ∈ [0, 1] → строка процентов, не больше `decimals` знаков после запятой.

    Пример: 0.1234 → «12.34%».
    """
    return f"{100.0 * rate:.{decimals}f}%"


def fmt_signed_pct_points(delta_ratio: float, *, decimals: int = 2) -> str:
    """
    Относительная разница (доля) → процентные пункты со знаком.

    delta_ratio = (b - a) / a; вывод вида «+12.34%».
    """
    return f"{100.0 * delta_ratio:+.{decimals}f}%"


def fmt_p_value(value: float) -> str:
    """p-value для отображения: научная запись при очень малых значениях."""
    if value < 0.001:
        return f"{value:.2e}"
    return f"{value:.4f}"
