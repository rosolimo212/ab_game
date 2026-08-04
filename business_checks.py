# coding: utf-8
"""
Слой 2 тестирования — бизнес-проверки ab_game (поверх pytest).

Цель:
    Прогнать сквозной игровой сценарий и инварианты MVP из task.md / AGENTS.md
    без реальной БД и без Streamlit.

Запуск:
    python3 business_checks.py
    # или через ./pre_commit_check.sh
"""

from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.app import AppService
from core.config import load_app_config
from core.generator import generate_round
from core.identity import make_user_id
from core.logging.factory import build_logger
from core.logging.noop import NoopLogger
from core.messages import button, clear_messages_cache, message
from core.models import (
    ACTION_DIFFICULTY_NORMAL,
    ACTION_GUESS_EFFECT,
    ACTION_GUESS_NO_EFFECT,
    ACTION_NAME_ENTERED,
    ACTION_NEXT_ROUND,
    GameSession,
    Screen,
    UserIdentity,
    ZTestResult,
)
from core.scoring import score_round
from core.stats import z_test_round
from ui.charts import build_ab_chart

REQUIRED_EVENTS = [
    "start_screen_visit",
    "button_continue",
    "name_entered",
    "button_difficulty_click",
    "session_start",
    "round_shown",
    "button_guess_effect",
    "guess_submitted",
    "button_next_round",
    "game_finished",
]

REQUIRED_FILES = [
    "settings.yaml",
    "core/app.py",
    "core/brain.py",
    "core/scoring.py",
    "core/stats.py",
    "core/generator.py",
    "core/logging/postgres.py",
    "ui/streamlit_app.py",
    "ui/charts.py",
    "style/kotelok_plotly.py",
    "style/big_kettler.png",
    "deploy/DEPLOY.md",
    "deploy/ab-game.service",
    "deploy/nginx-ab-game.conf",
    "data/dialog_messages.json",
    "sql/001_init.sql",
    "sql/002_round_parameters.sql",
]

MAX_LATENCY_SEC = 8.0
SHORT_SESSION_ROUNDS = 3


class MemoryLogger:
    """In-memory EventLogger для бизнес-проверок."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.users: dict[str, dict[str, Any]] = {}
        self._by_external: dict[tuple[str, str], UserIdentity] = {}
        self._counter = 0

    def ensure_user(self, channel: str, external_user_id: str) -> UserIdentity:
        key = (channel, external_user_id)
        if key in self._by_external:
            return self._by_external[key]

        user_id = make_user_id(channel, external_user_id)
        if user_id in self.users:
            identity = UserIdentity(
                user_id,
                self.users[user_id]["internal_user_id"],
                external_user_id,
            )
            self._by_external[key] = identity
            return identity

        self._counter += 1
        self.users[user_id] = {
            "internal_user_id": self._counter,
            "external_user_id": external_user_id,
            "user_name": "",
            "registration_date": datetime.now(),
        }
        identity = UserIdentity(user_id, self._counter, external_user_id)
        self._by_external[key] = identity
        return identity

    def upsert_user(
        self,
        identity: UserIdentity,
        user_name: str,
        registration_date: datetime,
        registration_channel: str,
        last_active_at: datetime,
        is_paid: bool = False,
        is_trial: bool = False,
        is_active: bool = True,
    ) -> None:
        self.users[identity.user_id] = {
            "internal_user_id": identity.internal_user_id,
            "external_user_id": identity.external_user_id,
            "user_name": user_name,
            "registration_date": registration_date,
            "registration_channel": registration_channel,
            "last_active_at": last_active_at,
            "is_paid": is_paid,
            "is_trial": is_trial,
            "is_active": is_active,
        }
        self._by_external[(registration_channel, identity.external_user_id)] = identity

    def log_event(
        self,
        identity: UserIdentity,
        event_name: str,
        channel: str,
        event_parameters: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        _ = timestamp
        self.events.append(
            {
                "user_id": identity.user_id,
                "internal_user_id": identity.internal_user_id,
                "external_user_id": identity.external_user_id,
                "event_name": event_name,
                "channel": channel,
                "event_parameters": event_parameters,
            }
        )

    def log_round_parameters(
        self,
        identity: UserIdentity,
        parameters: dict[str, Any],
        *,
        played_at: datetime | None = None,
    ) -> None:
        _ = played_at
        self.events.append(
            {
                "user_id": identity.user_id,
                "internal_user_id": identity.internal_user_id,
                "external_user_id": identity.external_user_id,
                "event_name": "round_parameters",
                "channel": "db",
                "event_parameters": parameters,
            }
        )

    def get_user_profile(self, identity: UserIdentity) -> dict[str, Any] | None:
        row = self.users.get(identity.user_id)
        if row is None:
            return None
        return {
            "user_name": str(row.get("user_name", "")),
            "registration_date": row.get("registration_date"),
        }


def _load_config(rounds: int = SHORT_SESSION_ROUNDS) -> dict[str, Any]:
    cfg = load_app_config(ROOT / "settings.yaml", None)
    cfg["game"] = dict(cfg["game"])
    cfg["game"]["rounds_per_session"] = rounds
    return cfg


def _make_service(
    logger: MemoryLogger | None = None,
    rounds: int = SHORT_SESSION_ROUNDS,
) -> tuple[AppService, MemoryLogger]:
    log = logger or MemoryLogger()
    service = AppService(
        logger=log,
        config=_load_config(rounds),
        rng=np.random.default_rng(7),
    )
    return service, log


def _play_full_session(
    service: AppService,
    logger: MemoryLogger,
    channel: str,
    *,
    external_id: str = "biz-check-user",
) -> tuple[UserIdentity, GameSession]:
    """Проходит имя → сложность → все раунды → SUMMARY; чередует догадки."""
    identity = logger.ensure_user(channel, external_id)
    service.handle_start(identity, channel)
    service.handle_action(
        identity, channel, ACTION_NAME_ENTERED, {"text": "Бизнес-тест"}
    )
    resp = service.handle_action(
        identity,
        channel,
        ACTION_DIFFICULTY_NORMAL,
        {"user_name": "Бизнес-тест"},
    )
    game = resp.game
    if game is None:
        raise AssertionError("После выбора сложности нет game")

    rounds_total = game.rounds_per_session
    for i in range(rounds_total):
        action = ACTION_GUESS_EFFECT if i % 2 == 0 else ACTION_GUESS_NO_EFFECT
        fb = service.handle_action(
            identity,
            channel,
            action,
            {"game": game, "user_name": "Бизнес-тест"},
        )
        if fb.screen != Screen.FEEDBACK or fb.game is None:
            raise AssertionError(f"Ожидали FEEDBACK на раунде {i + 1}")
        nxt = service.handle_action(
            identity,
            channel,
            ACTION_NEXT_ROUND,
            {"game": fb.game, "user_name": "Бизнес-тест"},
        )
        game = nxt.game
        if game is None:
            raise AssertionError(f"Нет game после next на раунде {i + 1}")

    if game.session_score is None:
        raise AssertionError("Сессия закончилась без session_score")
    return identity, game


def check_project_scaffold_exists() -> None:
    missing = [p for p in REQUIRED_FILES if not (ROOT / p).exists()]
    if missing:
        raise AssertionError("Не найдены файлы: " + ", ".join(missing))


def check_settings_load_and_schema() -> None:
    cfg = load_app_config(ROOT / "settings.yaml", None)
    if cfg["logging"]["schema"] != "ab_game":
        raise AssertionError("Схема должна быть ab_game")
    if int(cfg["game"]["rounds_per_session"]) < 1:
        raise AssertionError("rounds_per_session должен быть >= 1")
    if not 0.0 < float(cfg["game"]["alpha"]) < 1.0:
        raise AssertionError("alpha вне (0, 1)")


def check_logger_factory_builds() -> None:
    logger = build_logger(
        {"app": {"logging_enabled": False}, "logging": {"schema": "ab_game"}}
    )
    if not isinstance(logger, NoopLogger):
        raise AssertionError("При logging_enabled=false ожидался NoopLogger")


def check_dialog_messages_and_buttons() -> None:
    clear_messages_cache()
    welcome = message("welcome", "streamlit", rounds_total=20)
    if "20" not in welcome:
        raise AssertionError("welcome не подставляет rounds_total")
    for name in (
        "continue",
        "difficulty_easy",
        "difficulty_normal",
        "difficulty_hard",
        "guess_effect",
        "guess_no_effect",
        "next_round",
        "end_game",
        "export_csv",
        "restart",
    ):
        if not button(name, "streamlit").strip():
            raise AssertionError(f"Пустая кнопка {name!r}")


def check_scoring_follows_z_test_not_generator() -> None:
    """Балл = согласие с significant, не с has_effect генератора."""
    significant = ZTestResult(
        p_value=0.01,
        z_stat=2.5,
        significant=True,
        alpha=0.05,
        successes_a=10,
        trials_a=100,
        successes_b=30,
        trials_b=100,
        rate_a=0.1,
        rate_b=0.3,
    )
    null = ZTestResult(
        p_value=0.4,
        z_stat=0.5,
        significant=False,
        alpha=0.05,
        successes_a=10,
        trials_a=100,
        successes_b=11,
        trials_b=100,
        rate_a=0.1,
        rate_b=0.11,
    )
    if score_round(True, significant).points != 1:
        raise AssertionError("Догадка «эффект» при significant должна дать 1")
    if score_round(False, significant).points != 0:
        raise AssertionError("Догадка «нет» при significant должна дать 0")
    if score_round(False, null).points != 1:
        raise AssertionError("Догадка «нет» при null должна дать 1")
    if score_round(True, null).points != 0:
        raise AssertionError("Догадка «эффект» при null должна дать 0")


def check_generator_two_branches_and_rates() -> None:
    cfg = _load_config()["game"]
    round_data = generate_round(cfg, rng=np.random.default_rng(1))
    if round_data.branch_a.name != "A" or round_data.branch_b.name != "B":
        raise AssertionError("Ожидались ветки A и B")
    if len(round_data.branch_a.points) != int(cfg["n_days"]):
        raise AssertionError("Число дней ветки A не совпало с n_days")
    for point in round_data.branch_a.points + round_data.branch_b.points:
        if not 0.0 <= point.rate <= 1.0:
            raise AssertionError(f"rate вне [0, 1]: {point.rate}")


def check_chart_builds_for_round() -> None:
    cfg = _load_config()["game"]
    round_data = generate_round(cfg, rng=np.random.default_rng(2))
    fig = build_ab_chart(round_data)
    if len(fig.data) != 2:
        raise AssertionError("График должен содержать 2 трассы")


def check_full_session_events_and_summary() -> None:
    service, logger = _make_service(rounds=SHORT_SESSION_ROUNDS)
    identity, game = _play_full_session(service, logger, "streamlit")
    logged = {e["event_name"] for e in logger.events}
    missing = [n for n in REQUIRED_EVENTS if n not in logged]
    if missing:
        raise AssertionError(f"Не залогированы: {missing}")

    shown = [
        e for e in logger.events if e["event_name"] == "round_shown"
    ]
    guesses = [
        e for e in logger.events if e["event_name"] == "guess_submitted"
    ]
    if len(shown) != SHORT_SESSION_ROUNDS:
        raise AssertionError(f"round_shown: {len(shown)} != {SHORT_SESSION_ROUNDS}")
    if len(guesses) != SHORT_SESSION_ROUNDS:
        raise AssertionError(f"guess_submitted: {len(guesses)} != {SHORT_SESSION_ROUNDS}")

    session = game.session_score
    assert session is not None
    if session.n_rounds != SHORT_SESSION_ROUNDS:
        raise AssertionError("n_rounds в итоге не совпал")
    if not (0.0 <= session.ci_low <= session.accuracy <= session.ci_high <= 1.0):
        raise AssertionError("Wilson CI не согласован с accuracy")
    if identity.user_id not in logger.users:
        raise AssertionError("Пользователь не сохранён")


def check_users_have_three_ids() -> None:
    service, logger = _make_service(rounds=1)
    identity, _ = _play_full_session(
        service, logger, "streamlit", external_id="three-ids"
    )
    row = logger.users[identity.user_id]
    if not row.get("external_user_id"):
        raise AssertionError("external_user_id не сохранён")
    if row["internal_user_id"] != identity.internal_user_id:
        raise AssertionError("internal_user_id не совпадает")
    if not identity.user_id:
        raise AssertionError("user_id пуст")


def check_users_last_active_updates() -> None:
    service, logger = _make_service(rounds=1)
    identity = logger.ensure_user("streamlit", "active-upd")
    service.handle_start(identity, "streamlit")
    first = logger.users[identity.user_id]["last_active_at"]
    time.sleep(0.02)
    service.handle_action(
        identity, "streamlit", ACTION_NAME_ENTERED, {"text": "Актив"}
    )
    second = logger.users[identity.user_id]["last_active_at"]
    if second < first:
        raise AssertionError("last_active_at не обновился")


def check_no_user_id_collisions() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        counter = Path(tmp) / "user_counter.json"
        logger = NoopLogger(counter_path=counter)
        internals: list[int] = []
        hashes: set[str] = set()
        for i in range(50):
            ident = logger.ensure_user("streamlit", f"session-{i}")
            internals.append(ident.internal_user_id)
            if ident.user_id in hashes:
                raise AssertionError("коллизия hash user_id")
            hashes.add(ident.user_id)
        if len(internals) != len(set(internals)):
            raise AssertionError("коллизии internal_user_id")


def check_guess_event_params_match_score() -> None:
    service, logger = _make_service(rounds=1)
    identity = logger.ensure_user("streamlit", "guess-params")
    service.handle_start(identity, "streamlit")
    service.handle_action(
        identity, "streamlit", ACTION_NAME_ENTERED, {"text": "Геймер"}
    )
    round_resp = service.handle_action(
        identity,
        "streamlit",
        ACTION_DIFFICULTY_NORMAL,
        {"user_name": "Геймер"},
    )
    assert round_resp.game is not None and round_resp.game.round_data is not None
    fb = service.handle_action(
        identity,
        "streamlit",
        ACTION_GUESS_EFFECT,
        {"game": round_resp.game, "user_name": "Геймер"},
    )
    assert fb.game is not None and fb.game.last_round_score is not None
    guess_events = [e for e in logger.events if e["event_name"] == "guess_submitted"]
    if not guess_events:
        raise AssertionError("Нет guess_submitted")
    params = guess_events[-1]["event_parameters"] or {}
    if params.get("points") != fb.game.last_round_score.points:
        raise AssertionError("points в логе != RoundScore")
    if params.get("guess_has_effect") is not True:
        raise AssertionError("guess_has_effect в логе неверен")
    if params.get("user_answer") != "effect":
        raise AssertionError("user_answer в логе неверен")

    shown = [e for e in logger.events if e["event_name"] == "round_shown"]
    if not shown:
        raise AssertionError("Нет round_shown")
    rp = shown[0]["event_parameters"] or {}
    for key in ("noise", "mean_a", "mean_b", "p_value", "round_index"):
        if key not in rp:
            raise AssertionError(f"В round_shown нет {key}")


def check_z_test_round_smoke() -> None:
    cfg = _load_config()["game"]
    round_data = generate_round(cfg, rng=np.random.default_rng(3))
    result = z_test_round(round_data, alpha=float(cfg["alpha"]))
    if not 0.0 <= result.p_value <= 1.0:
        raise AssertionError("p_value вне [0, 1]")
    if result.significant is not (result.p_value < result.alpha):
        raise AssertionError("significant не согласован с p_value и alpha")


def check_session_latency_under_limit() -> None:
    service, logger = _make_service(rounds=SHORT_SESSION_ROUNDS)
    started = time.monotonic()
    _play_full_session(service, logger, "streamlit", external_id="latency")
    elapsed = time.monotonic() - started
    if elapsed >= MAX_LATENCY_SEC:
        raise AssertionError(f"Сценарий занял {elapsed:.2f} с (>= {MAX_LATENCY_SEC})")


def check_sql_init_mentions_ab_game() -> None:
    sql = (ROOT / "sql" / "001_init.sql").read_text(encoding="utf-8")
    if "CREATE SCHEMA IF NOT EXISTS ab_game" not in sql:
        raise AssertionError("001_init.sql не создаёт схему ab_game")
    if "ab_game.users" not in sql or "ab_game.events" not in sql:
        raise AssertionError("001_init.sql без таблиц users/events")
    if "ab_game.round_parameters" not in sql:
        raise AssertionError("001_init.sql без round_parameters")
    sql2 = (ROOT / "sql" / "002_round_parameters.sql").read_text(encoding="utf-8")
    if "round_parameters" not in sql2:
        raise AssertionError("002_round_parameters.sql пустой/битый")


def run_all_checks() -> None:
    checks = [
        ("каркас проекта", check_project_scaffold_exists),
        ("settings + схема ab_game", check_settings_load_and_schema),
        ("фабрика логгера", check_logger_factory_builds),
        ("диалоги и кнопки", check_dialog_messages_and_buttons),
        ("scoring = согласие с z-тестом", check_scoring_follows_z_test_not_generator),
        ("генератор: 2 ветки, rate∈[0,1]", check_generator_two_branches_and_rates),
        ("z-тест smoke", check_z_test_round_smoke),
        ("Plotly-график строится", check_chart_builds_for_round),
        ("полная сессия + события + итог", check_full_session_events_and_summary),
        ("параметры guess в логе", check_guess_event_params_match_score),
        ("три id в users", check_users_have_three_ids),
        ("last_active_at обновляется", check_users_last_active_updates),
        ("нет коллизий user_id", check_no_user_id_collisions),
        (f"латентность сессии < {MAX_LATENCY_SEC} с", check_session_latency_under_limit),
        ("SQL init для ab_game", check_sql_init_mentions_ab_game),
    ]

    print("business_checks:")
    for title, fn in checks:
        fn()
        print(f"  OK: {title}")

    print("business_checks: OK")


if __name__ == "__main__":
    run_all_checks()
