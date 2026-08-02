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

## События в Postgres (`ab_game.events`)

Пишутся при `logging_enabled: true`. Таблица: `ab_game.events`, параметры — JSONB в `event_parameters`.

| event_name | Когда | Параметры |
|------------|--------|-----------|
| `start_screen_visit` | Первый заход / `handle_start` | — |
| `button_start` | Клик «Начать» | `action` |
| `button_restart` | Клик «Играть снова» | `action` |
| `button_guess_effect` | Клик «Эффект есть» | `action` |
| `button_guess_no_effect` | Клик «Эффекта нет» | `action` |
| `button_next_round` | Клик «Далее» | `action` |
| `session_start` | Старт новой игровой сессии | `rounds_per_session` |
| `round_shown` | Показан график раунда | `round_index`, `noise`, `mean_a`, `mean_b`, `p_value` |
| `guess_submitted` | Догадка обработана (после клика) | `round_index`, `user_answer` (`effect` / `no_effect`), `guess_has_effect`, `test_significant`, `points`, `p_value` |
| `game_finished` | Сессия завершена, показан итог | `n_correct`, `n_rounds`, `accuracy`, `ci_low`, `ci_high`, `p_value`, `significant` |

Пояснения:

- `mean_a` / `mean_b` — пулырованные доли веток за все дни раунда.
- `p_value` в `round_shown` — z-тест по данным графика (для аналитики; игрок его ещё не видит).
- Клики `button_*` и бизнес-события (`guess_submitted`, `round_shown`, …) пишутся отдельно: клик — факт нажатия, остальное — результат обработки.

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
