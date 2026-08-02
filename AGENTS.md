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
4. Тексты пользователя → **только** `data/dialog_messages.json` (в т.ч. панель FEEDBACK, оси/hover графика, вердикты). Числа → `core/format_text.py` (`fmt_pct` ≤ 2 знака + `%`).
5. Избыточные тесты: pytest + `business_checks.py` + `./pre_commit_check.sh`.
6. **Конфиги:** в git только `settings.yaml`. Все остальные `*.yaml` в `.gitignore`.
7. Коммиты только по просьбе.

Легенда Plotly — **под** графиком (`legend.y < 0`), чтобы не наезжала на текст сверху.

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

Экраны: `START` (имя) → `DIFFICULTY` → `ROUND` → `FEEDBACK` → … → `SUMMARY`.  
Кнопка «Закончить игру» на ROUND/FEEDBACK. SUMMARY: имя, сложность, **Экспорт CSV**, «Играть снова».

`app.debug_mode` — показывать события логов на экране (`TeeEventLogger` + expander).

`base_p` раунда ∈ [`base_p_min`, `base_p_max`]; hard не должен давать «эффекта нет» почти всегда (см. `game.difficulties.hard`).

| Action | Смысл |
|--------|--------|
| `name_entered` | Сохранить имя → DIFFICULTY |
| `difficulty_easy` / `normal` / `hard` | Старт сессии с пресетом |
| `guess_effect` / `guess_no_effect` | Догадка → FEEDBACK |
| `next_round` | Следующий раунд или SUMMARY |
| `end_game` | Досрочный итог |
| `export_csv` | Экспорт сырых данных сессии (лог) |
| `restart` | Снова к DIFFICULTY (имя сохраняется) |

`GameSession` живёт в `st.session_state`. События логов — см. README.

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

./run_tests.sh              # слой 1: pytest → 55 passed
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
