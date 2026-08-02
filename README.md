# ab_game — игра в A/B-тесты

Браузерное приложение (Streamlit): по графику двух временных рядов угадать, значим ли эффект, затем сразу сверить с **z-тестом**. За верные ответы — баллы; в конце сессии — доля верных с доверительным интервалом и p-value (мета-ирония).

**Полный контекст для агентов/новой сессии:** [`AGENTS.md`](AGENTS.md) · исходное ТЗ: [`task.md`](task.md)

## Статус

| # | Этап | Состояние |
|---|------|-----------|
| 1 | Каркас + settings / secrets | **готово** |
| 2 | Генератор биномиальных рядов | **готово** |
| 3 | Z-тест двух пропорций | **готово** |
| 4 | Scoring | не начат |
| 5 | Plotly | не начат |
| 6 | Streamlit / сценарий | не начат |
| 7 | Postgres (`ab_game`) | не начат |
| 8 | business_checks + pre_commit | не начат |

После каждого этапа обновляются этот README и `AGENTS.md`.

## Запуск тестов

Тесты: `tests/test_config.py`, `tests/test_generator.py`, `tests/test_stats.py`.

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

Сейчас ожидается: **14 passed**.

## Стек

- Python 3.10+
- UI: Streamlit (ещё не подключён)
- Графики: Plotly (ещё не подключён)
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
- `core/models.py` — `DayPoint`, `BranchSeries`, `RoundData`, `ZTestResult`

## Правила игры (MVP)

- 20 раундов, 2 ветки, биномиальная доля ∈ [0, 1], по умолчанию 14 дней.
- Правильный ответ = согласие с z-тестом при α = 5% (не флаг эффекта генератора).
- Генерация эффекта: 50% null / 50% сдвиг `±20%` от `base_p`; шум из settings.
- Фидбек сразу; итог = доля верных + CI + p-value.
- График: метрика за день; hover — rate, числитель, знаменатель.

## Дальше

4. Scoring → 5. Plotly → 6. Streamlit → 7. Postgres → 8. business_checks
