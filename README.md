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
| 6 | Streamlit / сценарий | **готово** |
| 7 | Postgres (`ab_game`) | **готово** |
| 8 | business_checks + pre_commit | не начат |

После каждого этапа обновляются этот README и `AGENTS.md`.

## Запуск приложения

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
# при logging_enabled: false secrets.yaml не обязателен
streamlit run ui/streamlit_app.py
# или: python main.py
```

## Запуск тестов

```bash
.venv/bin/pip install -r requirements-dev.txt
./run_tests.sh
```

Сейчас ожидается: **42 passed**.

## Стек

- Python 3.10+
- UI: Streamlit (`ui/streamlit_app.py`)
- Графики: Plotly (`ui/charts.py`)
- Логи: PostgreSQL, БД `communication`, схема `ab_game` (`sql/001_init.sql`)
- Конфиг: `settings.yaml` (в git) + локальный `secrets.yaml` (не в git)

## Конфиг

В git попадает **только** `settings.yaml`. Локально для паролей:

```yaml
logging:
  password: "..."
testing:
  password: "..."
```

При `app.logging_enabled: false` secrets не обязателен. Для записи логов:

1. `psql -h localhost -U roman -d communication -f sql/001_init.sql`
2. В `settings.yaml`: `app.logging_enabled: true`
3. Пароль в `secrets.yaml`

## Уже в коде

- `core/config.py` — merge settings ⊕ secrets  
- `core/generator.py` — `generate_round` → `RoundData`  
- `core/stats.py` — pooled z-тест пропорций  
- `core/scoring.py` — балл раунда + итог сессии  
- `core/app.py` / `core/brain.py` — сценарий START → ROUND → FEEDBACK → SUMMARY  
- `core/logging/` — PostgresLogger / NoopLogger  
- `ui/charts.py` — Plotly Figure  
- `ui/streamlit_app.py` — клиент  
- `data/dialog_messages.json` — тексты  

## Правила игры (MVP)

- 20 раундов, 2 ветки, биномиальная доля ∈ [0, 1], по умолчанию 14 дней.
- Правильный ответ = согласие с z-тестом при α = 5% (не флаг эффекта генератора).
- Фидбек сразу; итог = доля верных + Wilson CI + p-value против 0.5.
- График: метрика за день; hover — rate, числитель, знаменатель.

## Дальше

8. business_checks + pre_commit
