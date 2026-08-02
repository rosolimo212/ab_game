# coding: utf-8
"""
Подключение к postgres.

Цель:
    Единые функции для psycopg2-соединения со схемой ab_game.

Вход:
    Секция logging из объединённого конфига.

Выход:
    connection; предпочтительно with postgres_connection(...).
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator

import psycopg2


def get_connection(logging_config: dict[str, Any]):
    """
    Открывает psycopg2-соединение.

    Вызывающий обязан закрыть соединение или использовать postgres_connection().
    """
    return psycopg2.connect(
        host=logging_config["host"],
        port=logging_config["port"],
        database=logging_config["database"],
        user=logging_config["user"],
        password=logging_config["password"],
    )


@contextmanager
def postgres_connection(
    logging_config: dict[str, Any],
) -> Generator[Any, None, None]:
    """Context manager: commit / rollback / close."""
    conn = get_connection(logging_config)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
