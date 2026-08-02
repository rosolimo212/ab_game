# coding: utf-8
"""Streamlit-клиент ab_game."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.messages import button, message
from core.models import (
    ACTION_GUESS_EFFECT,
    ACTION_GUESS_NO_EFFECT,
    ACTION_NEXT_ROUND,
    ACTION_RESTART,
    ACTION_START_SESSION,
    Screen,
)
from ui.base import build_app_service
from ui.charts import build_ab_chart
from ui.helpers import (
    apply_response,
    build_payload,
    get_identity,
    init_user_identity,
)


def _init_session(service: Any, state: Any) -> None:
    if state.get("initialized"):
        return
    state["initialized"] = True
    identity = init_user_identity(service, state, "streamlit")
    response = service.handle_start(identity, "streamlit")
    apply_response(state, response)


def _dispatch(service: Any, state: Any, action: str) -> None:
    identity = get_identity(state)
    payload = build_payload(game=state.get("game"), screen=state.get("screen"))
    response = service.handle_action(identity, "streamlit", action, payload)
    apply_response(state, response)


def run_streamlit(config: dict[str, Any]) -> None:
    import streamlit as st

    st.set_page_config(
        page_title=message("browser_page_title", "streamlit"),
        page_icon="📊",
    )

    service = build_app_service(config)
    state = st.session_state

    if not state.get("initialized"):
        _init_session(service, state)

    st.title(message("browser_title", "streamlit"))
    st.markdown(state.get("last_text", ""))

    screen = state.get("screen", Screen.START.value)
    game = state.get("game")

    if screen == Screen.START.value:
        if st.button(button("start", "streamlit"), key="btn_start"):
            _dispatch(service, state, ACTION_START_SESSION)
            st.rerun()

    elif screen == Screen.ROUND.value:
        if game is not None and game.round_data is not None:
            fig = build_ab_chart(game.round_data)
            st.plotly_chart(fig, use_container_width=True)
        cols = st.columns(2)
        with cols[0]:
            if st.button(button("guess_effect", "streamlit"), key="btn_guess_effect"):
                _dispatch(service, state, ACTION_GUESS_EFFECT)
                st.rerun()
        with cols[1]:
            if st.button(
                button("guess_no_effect", "streamlit"), key="btn_guess_no_effect"
            ):
                _dispatch(service, state, ACTION_GUESS_NO_EFFECT)
                st.rerun()

    elif screen == Screen.FEEDBACK.value:
        if game is not None and game.round_data is not None:
            fig = build_ab_chart(game.round_data, title=None)
            st.plotly_chart(fig, use_container_width=True)
        if st.button(button("next_round", "streamlit"), key="btn_next"):
            _dispatch(service, state, ACTION_NEXT_ROUND)
            st.rerun()

    elif screen == Screen.SUMMARY.value:
        if st.button(button("restart", "streamlit"), key="btn_restart"):
            _dispatch(service, state, ACTION_RESTART)
            st.rerun()


if __name__ == "__main__":
    from core.config import load_app_config

    run_streamlit(load_app_config(ROOT / "settings.yaml", ROOT / "secrets.yaml"))
