# AGENTS.md — контекст для AI-агентов и разработчиков

Краткая выжимка по проекту **ab_game**. Читать перед правками кода.  
Источники: `task.md` (исходное ТЗ), этот файл и `README.md` (актуальные решения).  
Репозиторий: `/home/roman/python/kotelok/ab_game`.  
Workspace: работать **здесь**, **без** `move_agent_to_root`.

**Процесс:** после каждого промежуточного этапа обновлять `README.md` и `AGENTS.md`.  
**Коммиты / push** — только по явной просьбе пользователя.

## Что это

Браузерная мини-игра: пользователь «на глаз» оценивает по графику двух временных рядов, есть ли значимый эффект в A/B-тесте, затем сразу сравнивает догадку с z-тестом. За верные ответы — баллы; в конце сессии — доля верных (+ CI и p-value как мета-ирония).

Стек MVP: **Python**, **Streamlit**, **Plotly**, логирование в **PostgreSQL**, настройки в **YAML**.

## Откуда наследовать

| Источник | Что брать |
|----------|-----------|
| `/home/roman/python/kotelok/template` | Принципы, каркас `core/` + `ui/`, yaml, postgres logging (noop/factory), identity, messages JSON, двухслойные тесты, `pre_commit_check.sh` |
| `/home/roman/python/wvs_bot` | Паттерны Streamlit, cookies/`external_user_id`, Plotly в UI, схема логов в БД `communication` |

Не копировать телеграм/опросы/аналитику WVS. Каркас — новый репозиторий, нужные куски из template переносятся вручную.

## Принципы (обязательные)

1. Максимальная инкапсуляция.
2. Предельная простота.
3. Документируем всё (комментарии на русском).
4. Гибкие зависимости.
5. Избыточное тестирование (pytest + `business_checks.py`).
6. UI без бизнес-логики.
7. Доменная логика без I/O.
8. Тексты в `data/dialog_messages.json`.
9. **Два конфига:** `settings.yaml` в git; `secrets.yaml` категорически не в git (только `secrets.example.yaml` как шаблон).
10. Коммиты / push — только по просьбе.

## Зафиксированные решения MVP

### Правильный ответ (scoring раунда)

Сравниваем догадку с вердиктом z-теста (`alpha = 0.05`):

| Догадка | Условие | Итог |
|---------|---------|------|
| «эффект есть» | `p_value < 0.05` | +1 |
| «эффекта нет» | `p_value >= 0.05` | +1 |
| иначе | — | 0 |

`has_effect` генератора **не** критерий баллов.

### Генерация рядов (`core/generator.py`) — реализовано

- `base_p` + дневной относительный `noise`: `p_day = clip(true_p * (1 + N(0, noise)), 0, 1)`, затем `Binomial(n_per_day, p_day)`.
- С вероятностью `effect_probability` (дефолт 0.5) ветка B: `p_B = clip(base_p * (1 + U(-range, +range)), 0, 1)`, `range=effect_relative_range` (дефолт 0.2).
- Иначе `p_B = base_p`.
- Дефолт: 14 дней, параметры в секции `game` конфига.

### Стат-тест (`core/stats.py`) — реализовано

- Двухсторонний **z-тест двух пропорций** (pooled SE) по сумме числителей/знаменателей за период.
- `alpha` из конфига (дефолт 0.05).
- Вырождение (se=0 или trials=0) → `p_value=1.0`, `significant=False`.

### UX / инфра (ещё не в коде)

- 20 раундов; фидбек сразу; итог = доля верных + CI + p-value.
- График Plotly: дневная метрика; hover: rate, num, den.
- Postgres: БД `communication`, схема `ab_game`.
- UI: Streamlit.

## Структура репозитория (сейчас)

```
core/
  config.py      # settings.yaml ⊕ secrets.yaml
  models.py      # DayPoint, BranchSeries, RoundData, ZTestResult
  generator.py   # generate_round
  stats.py       # two_proportion_z_test, z_test_round
ui/              # заглушка
data/            # placeholder
sql/             # placeholder
tests/           # test_config, test_generator, test_stats
settings.yaml           # в git
secrets.example.yaml    # в git (шаблон)
secrets.yaml            # НЕ в git
requirements.txt
requirements-dev.txt
```

## Логирование (postgres) — план

- Схема `ab_game`, таблицы `users` / `events`.
- `logging_enabled: false` → noop.
- `user_id` = sha256(`channel:external_user_id`).

## Тесты

```bash
cd /home/roman/python/kotelok/ab_game
source .venv/bin/activate   # или .venv/bin/pytest
pytest tests/ -q
```

На этапе 1–3 (+ split конфигов): **14 passed**.  
Для прогона ядра достаточно `numpy`, `PyYAML`, `pytest`.

## Статус этапов

| # | Этап | Состояние |
|---|------|-----------|
| 1 | Каркас + `settings.yaml` / `secrets` | **готово** |
| 2 | Генератор биномиальных рядов | **готово** |
| 3 | Z-тест пропорций | **готово** |
| 4 | Scoring раунда/сессии | не начат |
| 5 | Plotly-график | не начат |
| 6 | AppService + Streamlit | не начат |
| 7 | Postgres logging | не начат |
| 8 | business_checks + pre_commit | не начат |

## Куда смотреть

- Требования: [`task.md`](task.md)
- Статус: [`README.md`](README.md)
- Шаблон: `/home/roman/python/kotelok/template`
- Эталон UI/логов: `/home/roman/python/wvs_bot`
