# coding: utf-8
"""Отложенный прогрев Plotly.js в Streamlit (без утяжеления первого paint)."""

from __future__ import annotations

import time
from datetime import timedelta
from typing import Any


def warmup_plotly_js_delayed(state: Any, *, delay_sec: float = 1.0) -> None:
    """
    Через ``delay_sec`` после первого открытия сессии один раз монтирует
    крошечный ``st.plotly_chart``, чтобы браузер подтянул Plotly.js
    (обычно пока пользователь на START вводит имя).

    Первый ответ сервера не ждёт Plotly: START рисуется сразу.
    """
    import plotly.graph_objects as go
    import streamlit as st

    if state.get("_plotly_warmup_done"):
        return

    state.setdefault("_plotly_warmup_t0", time.monotonic())

    # Скрыть служебный график, если он успел появиться в layout.
    st.markdown(
        """
        <style>
        div.element-container:has(div[data-testid="stPlotlyChart"]
          iframe[title*="_ab_game_plotly_warmup"]) {
            height: 0 !important;
            min-height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    @st.fragment(run_every=timedelta(seconds=1))
    def _warm_fragment() -> None:
        if st.session_state.get("_plotly_warmup_done"):
            return
        t0 = float(st.session_state.get("_plotly_warmup_t0") or time.monotonic())
        # Первый вызов fragment часто сразу; ждём минимум delay_sec от старта сессии.
        if time.monotonic() - t0 < delay_sec:
            return
        fig = go.Figure()
        fig.update_layout(
            height=10,
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
        )
        st.plotly_chart(
            fig,
            use_container_width=False,
            config={"displayModeBar": False, "staticPlot": True},
            key="_ab_game_plotly_warmup",
        )
        st.session_state["_plotly_warmup_done"] = True

    _warm_fragment()
