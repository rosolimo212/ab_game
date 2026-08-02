# ab_game — игра в A/B-тесты

Браузерное приложение (Streamlit): по графику двух временных рядов угадать, значим ли эффект, затем сразу сверить с **z-тестом**. За верные ответы — баллы; в конце сессии — доля верных с доверительным интервалом и p-value (мета-ирония).

Репозиторий: `/home/roman/python/kotelok/ab_game`  
Контекст для агентов: [`AGENTS.md`](AGENTS.md) · исходное ТЗ: [`task.md`](task.md)

## Статус

| # | Этап | Состояние |
|---|------|-----------|
| 1 | Каркас + yaml (settings / secrets) | **готово** |
| 2 | Генератор биномиальных рядов | **готово** |
| 3 | Z-тест двух пропорций | **готово** |
| 4 | Scoring | не начат |
| 5 | Plotly | не начат |
| 6 | Streamlit / сценарий | не начат |
| 7 | Postgres (`ab_game`) | не начат |
| 8 | business_checks + pre_commit | не начат |

После каждого этапа обновляются этот README и `AGENTS.md`.

## Стек

- Python 3.10+
- UI: Streamlit (ещё не подключён)
- Графики: Plotly (ещё не подключён)
- Логи: PostgreSQL, БД `communication`, схема `ab_game`
- Конфиг: два YAML — `settings.yaml` (в git) и `secrets.yaml` (не в git)

## Уже в коде

### Конфиг (`core/config.py`)

| Файл | В git? | Содержимое |
|------|--------|------------|
| `settings.yaml` | да | `app`, `game`, публичная часть `logging` / `testing` |
| `secrets.yaml` | **нет** | пароли, токены |
| `secrets.example.yaml` | да | шаблон для копирования в `secrets.yaml` |

`load_app_config(settings, secrets)` сливает файлы. При `logging_enabled=false` secrets можно не создавать.  
Схема логов: `ab_game`. Параметры игры: `base_p`, `noise`, `n_per_day`, `n_days` (14), `effect_probability` (0.5), `effect_relative_range` (0.2), `rounds_per_session` (20), `alpha` (0.05).

### Генератор (`core/generator.py`)

`generate_round(game_cfg, rng=None) -> RoundData`:

- ветка A с `true_p = base_p`;
- ветка B: с вероятностью 50% тот же `p`, иначе сдвиг `base_p * (1 + U(-0.2, +0.2))` (клип в [0, 1]);
- каждый день: шум на `p`, затем `Binomial(n_per_day, p_day)`.

### Z-тест (`core/stats.py`)

`two_proportion_z_test(...)` / `z_test_round(round_data, alpha)` — pooled z-тест по сумме дней.  
Вердикт `significant = p_value < alpha` — основа будущих баллов (не флаг `has_effect`).

## Правила игры (MVP, целиком)

- 20 раундов, 2 ветки, биномиальная доля ∈ [0, 1].
- Правильный ответ = согласие с z-тестом при α = 5%.
- Фидбек сразу; итог = доля верных + CI + p-value.
- График: метрика за день; hover — rate, числитель, знаменатель.

## Запуск тестов

```bash
cd /home/roman/python/kotelok/ab_game
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt   # или минимум: numpy PyYAML pytest
pytest tests/ -q
```

Сейчас: **14 passed** (config, generator, stats).

## Дальше

4. Scoring раунда и сессии  
5. Plotly  
6. AppService + Streamlit  
7. Postgres logging  
8. `business_checks.py` + `pre_commit_check.sh`
