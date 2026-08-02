# coding: utf-8
"""
Экспорт сырых дневных точек сессии в CSV.

Колонки: round, branch, date, value
  round — номер раунда (1-based);
  branch — A или B;
  date — номер дня в раунде (1..n_days);
  value — доля (rate) за день.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Sequence

from core.models import RoundData


def session_rounds_to_csv_rows(
    rounds: Sequence[RoundData],
) -> list[dict[str, str | int | float]]:
    """Строки словарей для CSV (удобно тестировать без файла)."""
    rows: list[dict[str, str | int | float]] = []
    for round_index, round_data in enumerate(rounds, start=1):
        for branch in (round_data.branch_a, round_data.branch_b):
            for point in branch.points:
                rows.append(
                    {
                        "round": round_index,
                        "branch": branch.name,
                        "date": point.day,
                        "value": point.rate,
                    }
                )
    return rows


def session_rounds_to_csv_text(rounds: Sequence[RoundData]) -> str:
    """Готовый CSV-текст (UTF-8)."""
    rows = session_rounds_to_csv_rows(rounds)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["round", "branch", "date", "value"])
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def session_rounds_to_csv_bytes(rounds: Sequence[RoundData]) -> bytes:
    """Байты для st.download_button (BOM для Excel)."""
    text = session_rounds_to_csv_text(rounds)
    return ("\ufeff" + text).encode("utf-8")
