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

Наследовать принципы и каркас из `/home/roman/python/kotelok/template`; UI/logging-паттерны — из `/home/roman/python/wvs_bot` (без копирования WVS-логики).

---

## Принципы

1. Максимальная инкапсуляция (UI / ядро / stats / генератор / логи сменяемы).
2. Предельная простота; комментарии **на русском**.
3. UI без бизнес-логики; домен без I/O.
4. Тексты пользователя → `data/dialog_messages.json` (когда появится UI).
5. Избыточные тесты: pytest + позже `business_checks.py`.
6. **Конфиги:** в git только `settings.yaml`. Все остальные `*.yaml` в `.gitignore` (в т.ч. `secrets.yaml`).
7. Коммиты только по просьбе.

---

## Конфиг (важно)

| Файл | Git | Назначение |
|------|-----|------------|
| `settings.yaml` | **да** (единственный yaml в репо) | `app`, `game`, публичный `logging`/`testing` |
| `secrets.yaml` | **нет** | пароли, токены |

`.gitignore`: `*.yaml` + `!settings.yaml`.

Создать секреты локально:

```yaml
# secrets.yaml  (не коммитить)
logging:
  password: "..."
testing:
  password: "..."
# telegram:
#   token: "..."
```

`load_app_config("settings.yaml", "secrets.yaml")` — deep-merge.  
При `logging_enabled: false` файл secrets можно не создавать.

---

## Зафиксированные правила игры (MVP)

**Баллы раунда** (не `has_effect` генератора!):

| Догадка | Условие z-теста | Балл |
|---------|-----------------|------|
| эффект есть | `p_value < 0.05` | 1 |
| эффекта нет | `p_value >= 0.05` | 1 |
| иначе | | 0 |

**Итог сессии** (`core/scoring.py`):

- `accuracy` = доля раундов с `points=1`
- Wilson CI для доли при `alpha` из settings
- z-тест H0: accuracy = 0.5 → `p_value` / `significant` (мета-ирония)

**Генератор** (`core/generator.py`): биномиальная доля [0,1]; 2 ветки; с вероятностью 0.5 сдвиг B: `base_p * (1 + U(-0.2,+0.2))`; иначе тот же `p`; дневной `noise`; дефолт 14 дней; `n_per_day` из settings.

**Стат-тест** (`core/stats.py`): pooled z-тест двух пропорций по сумме дней; `alpha=0.05`.

**График** (`ui/charts.py`): Plotly — дневная доля; hover: rate / числитель / знаменатель; `build_ab_chart(round_data)`.

**UX (ещё не в коде):** 20 раундов; фидбек сразу; Streamlit показывает график + кнопки догадки + итог сессии.

**Postgres:** БД `communication`, схема `ab_game`.

---

## Структура сейчас

```
core/config.py models.py generator.py stats.py scoring.py
ui/charts.py          # Plotly Figure из RoundData
data/ sql/            # placeholder
tests/
  test_config.py
  test_generator.py
  test_stats.py
  test_scoring.py
  test_charts.py
settings.yaml         # в git
run_tests.sh          # ./run_tests.sh
requirements.txt
requirements-dev.txt
```

---

## Как запускать тесты

Тесты лежат в `tests/`. Запуск из корня проекта:

```bash
./run_tests.sh
# или:
.venv/bin/pytest tests/ -q
```

Первая установка:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
# минимум для ядра: numpy PyYAML plotly pytest
./run_tests.sh
```

Ожидаемо: **24 passed** (config, generator, stats, scoring, charts).

---

## Статус этапов

| # | Этап | Состояние |
|---|------|-----------|
| 1 | Каркас + settings/secrets split | **готово** |
| 2 | Генератор | **готово** |
| 3 | Z-тест | **готово** |
| 4 | Scoring раунда/сессии | **готово** |
| 5 | Plotly | **готово** |
| 6 | AppService + Streamlit | не начат |
| 7 | Postgres logging | не начат |
| 8 | business_checks + pre_commit | не начат |

Следующий по плану: **6. AppService + Streamlit**.

---

## Локальные незакоммиченные правки (на момент записи)

Возможно есть незакоммиченные изменения этапов 1–5 и инфраструктуры (gitignore, run_tests.sh и т.д.).  
Коммитить **только по просьбе пользователя**.
