# coding: utf-8
"""Тесты identity."""

from __future__ import annotations

from core.identity import make_user_id, new_external_user_id


def test_make_user_id_stable() -> None:
    a = make_user_id("streamlit", "abc")
    b = make_user_id("streamlit", "abc")
    assert a == b
    assert len(a) == 64


def test_make_user_id_differs_by_channel() -> None:
    assert make_user_id("streamlit", "1") != make_user_id("telegram", "1")


def test_new_external_user_id_unique() -> None:
    ids = {new_external_user_id("streamlit") for _ in range(20)}
    assert len(ids) == 20
