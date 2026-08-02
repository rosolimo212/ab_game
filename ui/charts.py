# coding: utf-8
"""
Plotly-график двух веток A/B для одного раунда.

Цель:
    По RoundData построить фигуру: дневная доля по оси Y, день — по X.
    Ось Y: всегда от 0 до max(rate)*1.15.
    Стиль — kotelok (`../style/kotelok_plotly.py`), фон прозрачный (Streamlit).

Подписи осей и hover — из data/dialog_messages.json.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import plotly.graph_objects as go

from core.messages import message
from core.models import BranchSeries, RoundData

# Sibling: /home/roman/python/kotelok/style (как в stl.ipynb).
_STYLE_DIR = Path(__file__).resolve().parents[2] / "style"
if str(_STYLE_DIR) not in sys.path:
    sys.path.insert(0, str(_STYLE_DIR))

from kotelok_plotly import apply, color  # noqa: E402


def _branch_trace(
    branch: BranchSeries,
    color_hex: str,
    *,
    channel: str,
) -> go.Scatter:
    """Одна линия ветки; доля в hover — проценты с 2 знаками (Plotly `.2%`)."""
    days = [point.day for point in branch.points]
    rates = [point.rate for point in branch.points]
    nums = [point.numerator for point in branch.points]
    dens = [point.denominator for point in branch.points]

    # hovertemplate: {branch} подставляем мы; %{…} — плейсхолдеры Plotly.
    hover = message("chart_hover", channel, branch=branch.name)

    return go.Scatter(
        x=days,
        y=rates,
        mode="lines+markers",
        name=branch.name,
        line={"color": color_hex, "width": 3},
        marker={"size": 7, "color": color_hex},
        customdata=list(zip(nums, dens)),
        hovertemplate=hover,
    )


def y_axis_range(round_data: RoundData, *, headroom: float = 1.15) -> tuple[float, float]:
    """
    Диапазон оси Y: минимум 0, максимум = max(rate) * headroom.

    Если все точки 0 — небольшой запас, чтобы ось не схлопнулась.
    """
    rates = [p.rate for p in round_data.branch_a.points] + [
        p.rate for p in round_data.branch_b.points
    ]
    peak = max(rates) if rates else 0.0
    y_max = peak * headroom
    if y_max <= 0.0:
        y_max = 0.05
    return 0.0, y_max


def build_ab_chart(
    round_data: RoundData,
    *,
    title: str | None = "",
    channel: str = "streamlit",
) -> go.Figure:
    """
    Строит график двух временных рядов (ветка A и B).

    :param round_data: данные раунда
    :param title: заголовок; "" — взять chart_title из JSON; None — без title
    :param channel: канал для текстов из dialog_messages.json
    :return: Figure в стиле kotelok, с прозрачным фоном
    """
    fig = go.Figure()
    fig.add_trace(
        _branch_trace(round_data.branch_a, color_hex=color(0), channel=channel)
    )
    fig.add_trace(
        _branch_trace(round_data.branch_b, color_hex=color(1), channel=channel)
    )

    y0, y1 = y_axis_range(round_data)
    layout: dict[str, Any] = {
        "xaxis_title": message("chart_xaxis", channel),
        "yaxis_title": message("chart_yaxis", channel),
        "showlegend": True,
        "hovermode": "x unified",
    }
    if title is None:
        pass
    elif title == "":
        layout["title"] = message("chart_title", channel)
    else:
        layout["title"] = title
    fig.update_layout(**layout)

    # Как в style/stl.ipynb: apply на готовую фигуру (без фиксации width —
    # Streamlit тянет use_container_width).
    apply(fig)

    # kotelok.apply всегда кладёт layout.title без text → Plotly JS рисует
    # «undefined». Если заголовка нет — явно пустая строка; иначе оставляем
    # текст после apply/_align_title.
    if title is None:
        fig.update_layout(title_text="")

    # Игровые оси + прозрачный фон поверх белого из шаблона kotelok.
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified",
    )
    fig.update_yaxes(range=[y0, y1], tickformat=".2%", rangemode="tozero")
    fig.update_xaxes(title_text=message("chart_xaxis", channel))
    fig.update_yaxes(title_text=message("chart_yaxis", channel))
    return fig
