# AGENTS.md — полный контекст для новой сессии Cursor

Читать **в первую очередь** при открытии проекта `/home/roman/python/kotelok/ab_game`.  
Дополнения: [`README.md`](README.md) (статус/запуск), [`task.md`](task.md) (исходное ТЗ).

**Workspace:** корень = эта папка. Не вызывать `move_agent_to_root`.  
**Процесс:** после каждого этапа обновлять `README.md` и этот файл.  
**Коммиты / push** — только по явной просьбе.

---

## Что это

Мини-игра в браузере (Streamlit): по графику A/B угадать, есть ли значимый эффект → сразу сверить с **z-тестом**. Баллы за согласие с тестом; в конце сессии — доля верных + CI + p-value (мета-ирония).

Стек: Python · Streamlit · Plotly · PostgreSQL · YAML.

Наследовать принципы и каркас из `/home/roman/python/kotelok/template`; UI/logging-паттерны — оттуда же (wvs_bot отсутствует).

---

## Принципы

1. Максимальная инкапсуляция (UI / ядро / stats / генератор / логи сменяемы).
2. Предельная простота; комментарии **на русском**.
3. UI без бизнес-логики; домен без I/O.
4. Тексты пользователя → `data/dialog_messages.json`.
5. Избыточные тесты: pytest + `business_checks.py` + `./pre_commit_check.sh`.
6. **Конфиги:** в git только `settings.yaml`. Все остальные `*.yaml` в `.gitignore`.
7. Коммиты только по просьбе.

---

## Конфиг (важно)

| Файл | Git | Назначение |
|------|-----|------------|
| `settings.yaml` | **да** | `app`, `game`, публичный `logging.schema` |
| `secrets.yaml` | **нет** (`*.yaml` в `.gitignore`) | Postgres host/port/db/user/password + `logging_enabled` |

`load_app_config("settings.yaml", "secrets.yaml")` — deep-merge.  
При `logging_enabled: false` (дефолт в settings) файл secrets можно не создавать.

Локальный образец `secrets.yaml`:

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

---

## Сценарий UI

Экраны: `START` → `ROUND` → `FEEDBACK` → … → `SUMMARY`.

| Action | Смысл |
|--------|--------|
| `start_session` / `restart` | Новая сессия, раунд 1 |
| `guess_effect` / `guess_no_effect` | Догадка → z-тест + балл → FEEDBACK |
| `next_round` | Следующий раунд или SUMMARY |

`GameSession` живёт в `st.session_state` (AppService пересоздаётся на rerun).

**События логов** (подробнее в README):  
`start_screen_visit`, `button_*`, `session_start`, `round_shown` (noise/mean_a/mean_b/p_value), `guess_submitted` (+ `user_answer`), `game_finished`.

---

## Зафиксированные правила игры (MVP)

**Баллы раунда** (не `has_effect` генератора!):

| Догадка | Условие z-теста | Балл |
|---------|-----------------|------|
| эффект есть | `p_value < 0.05` | 1 |
| эффекта нет | `p_value >= 0.05` | 1 |
| иначе | | 0 |

**Итог сессии:** accuracy + Wilson CI + z-тест H0: p=0.5.

**Postgres:** БД `communication`, схема `ab_game` (`sql/001_init.sql`).

---

## Структура

```
core/          # конфиг, модели, generator, stats, scoring, app, brain, logging
ui/            # charts, helpers, streamlit_app
data/dialog_messages.json
sql/001_init.sql
business_checks.py
pre_commit_check.sh
run_tests.sh
main.py
settings.yaml
tests/
```

---

## Как запускать

```bash
streamlit run ui/streamlit_app.py

./run_tests.sh              # слой 1: pytest → 43 passed
./pre_commit_check.sh       # слой 1 + слой 2 (business_checks)
```

Схема БД (если `logging_enabled: true`):

```bash
psql -h localhost -U roman -d communication -f sql/001_init.sql
```

---

## Статус этапов

| # | Этап | Состояние |
|---|------|-----------|
| 1 | Каркас + settings/secrets split | **готово** |
| 2 | Генератор | **готово** |
| 3 | Z-тест | **готово** |
| 4 | Scoring раунда/сессии | **готово** |
| 5 | Plotly | **готово** |
| 6 | AppService + Streamlit | **готово** |
| 7 | Postgres logging | **готово** |
| 8 | business_checks + pre_commit | **готово** |

**MVP по плану завершён.** Дальше — только по новым запросам (telegram/console, cookies, CI и т.д.).

---

## Коммиты

Коммитить **только по просьбе пользователя**.
