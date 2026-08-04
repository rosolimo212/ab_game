# coding: utf-8
"""
Общие структуры данных ядра ab_game.

Цель:
    Единые типы для метрики A/B, баллов, сценария UI и идентичности пользователя.

Выход:
    dataclass-объекты без I/O — ими обмениваются генератор, stats, scoring, app и UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Screen(str, Enum):
    """Экраны пользовательского сценария."""

    START = "start"
    DIFFICULTY = "difficulty"
    ROUND = "round"
    FEEDBACK = "feedback"
    SUMMARY = "summary"


# Действия UI → AppService.handle_action (не путать с event_name в логах).
ACTION_NAME_ENTERED = "name_entered"
ACTION_DIFFICULTY_EASY = "difficulty_easy"
ACTION_DIFFICULTY_NORMAL = "difficulty_normal"
ACTION_DIFFICULTY_HARD = "difficulty_hard"
ACTION_GUESS_EFFECT = "guess_effect"
ACTION_GUESS_NO_EFFECT = "guess_no_effect"
ACTION_NEXT_ROUND = "next_round"
ACTION_END_GAME = "end_game"
ACTION_EXPORT_CSV = "export_csv"
ACTION_RESTART = "restart"

# Совместимость: старый start_session = выбор нормальной сложности.
ACTION_START_SESSION = ACTION_DIFFICULTY_NORMAL


@dataclass(frozen=True)
class UserIdentity:
    """
    Тройка идентификаторов пользователя.

    user_id — sha256(channel:external_user_id), PK в postgres.
    internal_user_id — BIGSERIAL для аналитики.
    external_user_id — uuid сессии streamlit (или telegram id позже).
    """

    user_id: str
    internal_user_id: int
    external_user_id: str


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
    Данные одного раунда игры: две ветки и явный флаг эффекта.

    has_effect — целевой флаг раунда: должен ли z-тест быть значимым
    (после калибровки генератора). Scoring по-прежнему смотрит на z-тест.
    base_p — базовый p ветки A / генеральной совокупности.
    calibrate_steps — сколько раз подгоняли |p_B−p_A| под флаг (0 = сразу совпало).
    """

    branch_a: BranchSeries
    branch_b: BranchSeries
    has_effect: bool
    base_p: float
    calibrate_steps: int = 0


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


@dataclass
class GameSession:
    """
    Состояние игровой сессии (живёт в UI session_state между rerun).

    round_index — 1-based номер текущего раунда (на FEEDBACK — только что сыгранного).
    round_data — данные текущего раунда (для графика и z-теста); None на START/SUMMARY.
    """

    round_index: int
    rounds_per_session: int
    round_data: RoundData | None = None
    round_scores: tuple[RoundScore, ...] = ()
    last_z_result: ZTestResult | None = None
    last_round_score: RoundScore | None = None
    session_score: SessionScore | None = None
    difficulty: str = "normal"
    user_name: str = ""
    # Рабочий noise для текущей сложности (для логов / UI).
    noise: float = 0.05
    # Все показанные раунды сессии (для CSV-экспорта).
    round_history: tuple[RoundData, ...] = ()


@dataclass
class AppResponse:
    """
    Ответ ядра клиенту после шага сценария.

    UI только показывает text/buttons, переходит на screen и сохраняет game.
    """

    text: str
    buttons: list[str] = field(default_factory=list)
    screen: Screen = Screen.START
    finished: bool = False
    game: GameSession | None = None
    user_name: str | None = None


@dataclass
class UserRecord:
    """Запись пользователя для таблицы ab_game.users."""

    user_id: str
    internal_user_id: int
    external_user_id: str
    user_name: str
    registration_date: datetime
    registration_channel: str
    last_active_at: datetime
    is_paid: bool = False
    is_trial: bool = False
    is_active: bool = True


@dataclass
class EventRecord:
    """Запись события для таблицы ab_game.events."""

    timestamp: datetime
    user_id: str
    internal_user_id: int
    external_user_id: str
    event_name: str
    channel: str
    event_parameters: dict[str, Any] | None = None
