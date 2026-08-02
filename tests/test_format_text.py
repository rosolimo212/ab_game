# coding: utf-8
"""Тесты форматирования процентов и p-value."""

from __future__ import annotations

from core.format_text import fmt_p_value, fmt_pct, fmt_signed_pct_points


def test_fmt_pct_two_decimals() -> None:
    assert fmt_pct(0.1) == "10.00%"
    assert fmt_pct(0.12345) == "12.35%"
    assert fmt_pct(0.12345, decimals=1) == "12.3%"


def test_fmt_signed_pct_points() -> None:
    assert fmt_signed_pct_points(0.1) == "+10.00%"
    assert fmt_signed_pct_points(-0.05) == "-5.00%"


def test_fmt_p_value() -> None:
    assert fmt_p_value(0.04) == "0.0400"
    assert "e" in fmt_p_value(1e-5).lower()
