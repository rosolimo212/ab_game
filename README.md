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
| 8 | business_checks + pre_commit | **готово** |

MVP по плану завершён.

## Запуск приложения

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
# при logging_enabled: false secrets.yaml не обязателен
streamlit run ui/streamlit_app.py
# или: python main.py
```

## Тесты

```bash
.venv/bin/pip install -r requirements-dev.txt

# слой 1 — unit/integration pytest
./run_tests.sh

# слой 1 + слой 2 (business_checks) — перед коммитом
./pre_commit_check.sh
```

Ожидается: **43 passed** (pytest) и **15 OK** (business_checks).

## Стек

- Python 3.10+
- UI: Streamlit (`ui/streamlit_app.py`)
- Графики: Plotly (`ui/charts.py`)
- Логи: PostgreSQL, БД `communication`, схема `ab_game` (`sql/001_init.sql`)
- Конфиг: `settings.yaml` (в git) + локальный `secrets.yaml` (не в git)

## Конфиг

В git попадает **только** `settings.yaml` (`.gitignore`: `*.yaml` + `!settings.yaml`).  
Параметры Postgres и включение логов — в локальном `secrets.yaml`:

```yaml
app:
  logging_enabled: true

logging:
  host: localhost
  port: 5432
  database: communication
  user: roman
  password: "..."
  schema: ab_game

testing:
  host: localhost
  port: 5432
  database: communication
  user: tester
  password: "..."
  schema: ab_game
```

При `app.logging_enabled: false` в settings (дефолт) secrets не обязателен.  
Для записи логов: `psql … -f sql/001_init.sql` + блок выше в `secrets.yaml` (включая `logging_enabled: true`).

## Уже в коде

- `core/` — конфиг, генератор, z-тест, scoring, AppService, logging  
- `ui/` — Plotly + Streamlit  
- `data/dialog_messages.json` — тексты  
- `business_checks.py` + `pre_commit_check.sh` — слой 2  

## Правила игры (MVP)

- 20 раундов, 2 ветки, биномиальная доля ∈ [0, 1], по умолчанию 14 дней.
- Правильный ответ = согласие с z-тестом при α = 5% (не флаг эффекта генератора).
- Фидбек сразу; итог = доля верных + Wilson CI + p-value против 0.5.
- График: метрика за день; hover — rate, числитель, знаменатель.
