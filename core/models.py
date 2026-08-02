# coding: utf-8
"""
Общие структуры данных ядра ab_game.

Цель:
    Единые типы для дневных точек метрики, веток A/B, раунда, z-теста и баллов.

Выход:
    dataclass-объекты без I/O — ими обмениваются генератор, stats, scoring и UI.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DayPoint:
    """
    Одна точка дневной метрики «числитель / знаменатель».

    day — номер дня (1..n_days).
    numerator — число успехов за день.
    denominator — число испытаний за день (n).
    """

    day: int
    numerator: int
    denominator: int

    @property
    def rate(self) -> float:
        """Доля успехов за день; при denominator=0 возвращает 0.0."""
        if self.denominator <= 0:
            return 0.0
        return self.numerator / self.denominator


@dataclass(frozen=True)
class BranchSeries:
    """
    Временной ряд одной ветки A/B.

    name — метка ветки («A» или «B»).
    true_p — истинная базовая доля до дневного шума (для диагностики, не для баллов).
    points — дневные наблюдения.
    """

    name: str
    true_p: float
    points: tuple[DayPoint, ...]

    @property
    def total_numerator(self) -> int:
        """Сумма числителей за весь период."""
        return sum(point.numerator for point in self.points)

    @property
    def total_denominator(self) -> int:
        """Сумма знаменателей за весь период."""
        return sum(point.denominator for point in self.points)

    @property
    def pooled_rate(self) -> float:
        """Пулырованная доля за период."""
        den = self.total_denominator
        if den <= 0:
            return 0.0
        return self.total_numerator / den


@dataclass(frozen=True)
class RoundData:
    """
    Данные одного раунда игры: две ветки и флаг эффекта в генераторе.

    has_effect — генератор сдвинул p ветки B (диагностика; scoring смотрит только на z-тест).
    base_p — базовый p из конфига / генеральной совокупности.
    """

    branch_a: BranchSeries
    branch_b: BranchSeries
    has_effect: bool
    base_p: float


@dataclass(frozen=True)
class ZTestResult:
    """
    Результат двухвыборочного z-теста пропорций.

    significant — True, если p_value < alpha.
    """

    p_value: float
    z_stat: float
    significant: bool
    alpha: float
    successes_a: int
    trials_a: int
    successes_b: int
    trials_b: int
    rate_a: float
    rate_b: float


@dataclass(frozen=True)
class RoundScore:
    """
    Балл одного раунда: согласие догадки с вердиктом z-теста.

    points — 1 при совпадении guess_has_effect с test_significant, иначе 0.
    p_value — p-value z-теста раунда (для фидбека), не влияет на points напрямую.
    """

    guess_has_effect: bool
    test_significant: bool
    points: int
    p_value: float


@dataclass(frozen=True)
class SessionScore:
    """
    Итог сессии: доля верных + Wilson CI + p-value против случайности (p=0.5).

    Мета-ирония: к «навыку» игрока применяем тот же стат-подход, что и к A/B.
    significant — True, если доля верных значимо отличается от 0.5 при заданном alpha.
    """

    n_rounds: int
    n_correct: int
    accuracy: float
    ci_low: float
    ci_high: float
    p_value: float
    z_stat: float
    significant: bool
    alpha: float
