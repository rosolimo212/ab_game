# coding: utf-8
"""Тесты PostgresLogger (без реальной БД)."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from unittest.mock import MagicMock, patch

from core.identity import make_user_id
from core.logging.factory import build_logger
from core.logging.noop import NoopLogger
from core.logging.postgres import PostgresLogger
from core.models import UserIdentity

LOGGING_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "communication",
    "user": "roman",
    "password": "secret",
    "schema": "ab_game",
}


def test_build_logger_noop_when_disabled() -> None:
    logger = build_logger(
        {"app": {"logging_enabled": False}, "logging": LOGGING_CONFIG}
    )
    assert isinstance(logger, NoopLogger)


def test_build_logger_postgres_when_enabled() -> None:
    logger = build_logger(
        {"app": {"logging_enabled": True}, "logging": LOGGING_CONFIG}
    )
    assert isinstance(logger, PostgresLogger)
    assert logger.schema == "ab_game"


def test_postgres_allocate_internal_id_uses_sequence() -> None:
    logger = PostgresLogger(LOGGING_CONFIG)
    mock_cursor = MagicMock()
    mock_cursor.fetchone.side_effect = [
        ("ab_game.users_internal_user_id_seq",),
        (42,),
    ]
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    @contextmanager
    def _fake_scope(_cfg):
        yield mock_conn

    with patch("core.logging.postgres.postgres_connection", _fake_scope):
        internal = logger._allocate_internal_user_id()

    assert internal == 42


def test_postgres_ensure_user_returns_existing() -> None:
    logger = PostgresLogger(LOGGING_CONFIG)
    user_id = make_user_id("streamlit", "999")
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (user_id, 7, "999")
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    @contextmanager
    def _fake_scope(_cfg):
        yield mock_conn

    with patch("core.logging.postgres.postgres_connection", _fake_scope):
        identity = logger.ensure_user("streamlit", "999")

    assert identity.user_id == user_id
    assert identity.internal_user_id == 7


def test_postgres_log_event_inserts_jsonb() -> None:
    logger = PostgresLogger(LOGGING_CONFIG)
    identity = UserIdentity(
        user_id=make_user_id("streamlit", "x"),
        internal_user_id=1,
        external_user_id="x",
    )
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    @contextmanager
    def _fake_scope(_cfg):
        yield mock_conn

    with patch("core.logging.postgres.postgres_connection", _fake_scope):
        logger.log_event(
            identity=identity,
            event_name="guess_submitted",
            channel="streamlit",
            event_parameters={"points": 1},
            timestamp=datetime(2026, 1, 1, 12, 0, 0),
        )

    mock_cursor.execute.assert_called_once()
    sql, params = mock_cursor.execute.call_args[0]
    assert "ab_game.events" in sql.replace(" ", "") or "ab_game.events" in sql
    assert params[4] == "guess_submitted"
    assert params[5] == "streamlit"
    assert '"points": 1' in params[6]


def test_noop_profile_roundtrip(tmp_path) -> None:
    logger = NoopLogger(counter_path=tmp_path / "counter.json")
    identity = logger.ensure_user("streamlit", "a")
    logger.upsert_user(
        identity,
        user_name="Игрок",
        registration_date=datetime(2026, 1, 1),
        registration_channel="streamlit",
        last_active_at=datetime(2026, 1, 2),
    )
    profile = logger.get_user_profile(identity)
    assert profile is not None
    assert profile["user_name"] == "Игрок"
