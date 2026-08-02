# coding: utf-8
"""Streamlit-клиент ab_game."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.export_csv import session_rounds_to_csv_bytes
from core.messages import button, message
from core.models import (
    ACTION_DIFFICULTY_EASY,
    ACTION_DIFFICULTY_HARD,
    ACTION_DIFFICULTY_NORMAL,
    ACTION_END_GAME,
    ACTION_EXPORT_CSV,
    ACTION_GUESS_EFFECT,
    ACTION_GUESS_NO_EFFECT,
    ACTION_NAME_ENTERED,
    ACTION_NEXT_ROUND,
    ACTION_RESTART,
    Screen,
)
from ui.base import build_app_service
from ui.charts import build_ab_chart
from ui.feedback_panel import format_feedback_stats
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


def _dispatch(service: Any, state: Any, action: str, *, text: str | None = None) -> None:
    identity = get_identity(state)
    payload = build_payload(
        game=state.get("game"),
        screen=state.get("screen"),
        user_name=state.get("user_name"),
        text=text,
    )
    response = service.handle_action(identity, "streamlit", action, payload)
    apply_response(state, response)


def _end_game_button(service: Any, state: Any) -> None:
    import streamlit as st

    if st.button(button("end_game", "streamlit"), key="btn_end_game"):
        _dispatch(service, state, ACTION_END_GAME)
        st.rerun()


def _render_debug_panel(state: Any) -> None:
    """Панель debug_mode: последние события логирования."""
    import streamlit as st

    events = list(state.get("debug_events") or [])
    if not events:
        return
    with st.expander(message("debug_panel_title", "streamlit"), expanded=False):
        # Показываем хвост, чтобы экран не раздувался.
        for item in events[-40:]:
            params = item.get("event_parameters")
            params_txt = json.dumps(params, ensure_ascii=False) if params else "—"
            st.markdown(
                f"**`{item.get('event_name')}`** · `{item.get('channel')}`\n\n"
                f"`{params_txt}`"
            )


def run_streamlit(config: dict[str, Any]) -> None:
    import streamlit as st

    st.set_page_config(
        page_title=message("browser_page_title", "streamlit"),
        page_icon="📊",
    )

    debug_mode = bool(config.get("app", {}).get("debug_mode", False))
    state = st.session_state
    if debug_mode:
        state.setdefault("debug_events", [])
        service = build_app_service(config, event_sink=state["debug_events"])
    else:
        service = build_app_service(config)

    if not state.get("initialized"):
        _init_session(service, state)

    st.title(message("browser_title", "streamlit"))
    # Текст сценария; отступ перед графиком, чтобы не слипался с Plotly.
    st.markdown(state.get("last_text", ""))
    st.markdown("")

    screen = state.get("screen", Screen.START.value)
    game = state.get("game")

    if screen == Screen.START.value:
        name = st.text_input(
            message("browser_name_label", "streamlit"),
            key="name_input",
            value=str(state.get("user_name") or ""),
        )
        if st.button(button("continue", "streamlit"), key="btn_continue"):
            _dispatch(service, state, ACTION_NAME_ENTERED, text=name)
            st.rerun()

    elif screen == Screen.DIFFICULTY.value:
        cols = st.columns(3)
        actions = (
            (ACTION_DIFFICULTY_EASY, "difficulty_easy", "btn_diff_easy"),
            (ACTION_DIFFICULTY_NORMAL, "difficulty_normal", "btn_diff_normal"),
            (ACTION_DIFFICULTY_HARD, "difficulty_hard", "btn_diff_hard"),
        )
        for col, (action, btn_name, key) in zip(cols, actions):
            with col:
                if st.button(button(btn_name, "streamlit"), key=key):
                    _dispatch(service, state, action)
                    st.rerun()

    elif screen == Screen.ROUND.value:
        if game is not None and game.round_data is not None:
            # title="" → подпись из dialog_messages (chart_title)
            fig = build_ab_chart(game.round_data, title="")
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
        _end_game_button(service, state)

    elif screen == Screen.FEEDBACK.value:
        left, right = st.columns([2, 1])
        with left:
            if game is not None and game.round_data is not None:
                fig = build_ab_chart(game.round_data, title=None)
                st.plotly_chart(fig, use_container_width=True)
        with right:
            if (
                game is not None
                and game.round_data is not None
                and game.last_z_result is not None
            ):
                st.markdown(
                    format_feedback_stats(game.round_data, game.last_z_result)
                )
        if st.button(button("next_round", "streamlit"), key="btn_next"):
            _dispatch(service, state, ACTION_NEXT_ROUND)
            st.rerun()
        _end_game_button(service, state)

    elif screen == Screen.SUMMARY.value:
        if game is not None and game.round_history:
            csv_bytes = session_rounds_to_csv_bytes(game.round_history)
            clicked = st.download_button(
                label=button("export_csv", "streamlit"),
                data=csv_bytes,
                file_name="ab_game_session.csv",
                mime="text/csv",
                key="btn_export_csv",
            )
            if clicked:
                _dispatch(service, state, ACTION_EXPORT_CSV)
        if st.button(button("restart", "streamlit"), key="btn_restart"):
            _dispatch(service, state, ACTION_RESTART)
            st.rerun()

    if debug_mode:
        _render_debug_panel(state)


if __name__ == "__main__":
    from core.config import load_app_config

    run_streamlit(load_app_config(ROOT / "settings.yaml", ROOT / "secrets.yaml"))
