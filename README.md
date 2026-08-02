# ab_game — игра в A/B-тесты

Браузерное приложение (Streamlit): по графику двух временных рядов угадать, значим ли эффект, затем сразу сверить с **z-тестом**. За верные ответы — баллы; в конце сессии — доля верных с доверительным интервалом и p-value (мета-ирония).

**Полный контекст для агентов/новой сессии:** [`AGENTS.md`](AGENTS.md) · исходное ТЗ: [`task.md`](task.md)

## Статус

| # | Этап | Состояние |
|---|------|-----------|
| 1 | Каркас + settings / secrets | **готово** |
| 2 | Генератор биномиальных рядов | **готово** |
| 3 | Z-тест двух пропорций | **готово** |
| 4 | Scoring | **готово** |
| 5 | Plotly | **готово** |
| 6 | Streamlit / сценарий | не начат |
| 7 | Postgres (`ab_game`) | не начат |
| 8 | business_checks + pre_commit | не начат |

После каждого этапа обновляются этот README и `AGENTS.md`.

## Запуск тестов

Тесты: `tests/test_config.py`, `tests/test_generator.py`, `tests/test_stats.py`, `tests/test_scoring.py`, `tests/test_charts.py`.

```bash
# из корня репозитория
./run_tests.sh
```

Первый раз:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
./run_tests.sh
```

Сейчас ожидается: **24 passed**.

## Стек

- Python 3.10+
- UI: Streamlit (ещё не подключён)
- Графики: Plotly (`ui/charts.py`)
- Логи: PostgreSQL, БД `communication`, схема `ab_game`
- Конфиг: `settings.yaml` (в git) + локальный `secrets.yaml` (не в git)

## Конфиг

В git попадает **только** `settings.yaml` (см. `.gitignore`: `*.yaml` + исключение `!settings.yaml`).

Локально для паролей создайте `secrets.yaml` (не коммитить):

```yaml
logging:
  password: "..."
testing:
  password: "..."
```

При `app.logging_enabled: false` secrets не обязателен.

## Уже в коде

- `core/config.py` — merge settings ⊕ secrets  
- `core/generator.py` — `generate_round` → `RoundData`  
- `core/stats.py` — pooled z-тест пропорций  
- `core/scoring.py` — балл раунда + итог сессии (доля, Wilson CI, p vs 0.5)  
- `core/models.py` — `DayPoint`, `BranchSeries`, `RoundData`, `ZTestResult`, `RoundScore`, `SessionScore`  
- `ui/charts.py` — `build_ab_chart(round_data)` → Plotly Figure  

## Правила игры (MVP)

- 20 раундов, 2 ветки, биномиальная доля ∈ [0, 1], по умолчанию 14 дней.
- Правильный ответ = согласие с z-тестом при α = 5% (не флаг эффекта генератора).
- Генерация эффекта: 50% null / 50% сдвиг `±20%` от `base_p`; шум из settings.
- Фидбек сразу; итог = доля верных + Wilson CI + p-value против случайности (0.5).
- График: метрика за день; hover — rate, числитель, знаменатель.

## Дальше

6. Streamlit / AppService → 7. Postgres → 8. business_checks
