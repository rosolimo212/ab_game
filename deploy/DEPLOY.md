# Деплой ab_game на VM (та же, что wvs_bot)

| | |
|--|--|
| URL | **https://ab.kotelok.space** |
| Сервер | `45.132.18.2` |
| Код | `/opt/kotelok/ab_game` |
| Streamlit | только `127.0.0.1:**8503**` |
| Python | **3.8.10** (апгрейд не нужен) |

Порты рядом: **8501** = template-streamlit, **8502** = wvs_bot → ab_game их не трогает.  
`User=` в systemd — это **linux-пользователь ОС**, не роль Postgres.

Стиль графиков (`style/`) уже в git — отдельно копировать не надо.

---

## Чек-лист (состояние на 2026-08-03)

Отмечай по мере прохождения. Детали команд — в секциях ниже.

### Уже сделано (инфра и код)

- [x] Домен `kotelok.space` на reg.ru, VM `45.132.18.2`
- [x] На VM уже есть: nginx/80·443, Postgres, wvs_bot, открытые нужные порты
- [x] Код лежит в `/opt/kotelok/ab_game`
- [x] Python 3.8.10 принят как прод; зависимости подогнаны (`numpy<1.26`, `streamlit<1.40`)
- [x] `.venv` создан, `pip install -r requirements.txt` проходит (после обновлённого requirements)
- [x] Понято: `User=` в unit ≠ пользователь Postgres

### Исправить сейчас (блокеры)

- [ ] **Порт:** не запускать на 8501. Только **8503**
- [ ] **Схема Postgres:** ошибка `relation "ab_game.users" does not exist` → один раз выполнить init SQL (§1б)
- [ ] **systemd `217/USER`:** `User=root`, пути к коду, порт **8503** → `daemon-reload` + `restart` (§2)
- [ ] Smoke на 8503 (§1)

### Ещё предстоит

- [ ] DNS: A-запись `ab` → `45.132.18.2`
- [ ] `secrets.yaml` + схема: `sql/001_init.sql`; если БД уже была без round_parameters → `sql/002_round_parameters.sql`
- [ ] Nginx site + certbot (§3)
- [ ] Финал: `https://ab.kotelok.space` открывается без traceback

### Готово, когда

1. `dig +short ab.kotelok.space` → `45.132.18.2`
2. `systemctl is-active ab-game` → `active`
3. `ss -lptn | grep 8503` → слушает `127.0.0.1:8503`
4. `curl -sI https://ab.kotelok.space` → 200/302
5. На сервере `debug_mode: false`, графики с логотипом Kotelok

---

## 1. Код и venv

```bash
cd /opt/kotelok/ab_game
git pull
python3 -m venv .venv          # если ещё нет
source .venv/bin/activate
pip install -U pip setuptools wheel
pip install -r requirements.txt
```

Прод-настройки:

```bash
nano secrets.yaml    # образец в AGENTS.md / README
nano settings.yaml   # debug_mode: false; logging_enabled по желанию
```

### 1б. Схема Postgres `ab_game` (обязательно, если logging_enabled)

Иначе в браузере: `relation "ab_game.users" does not exist`.

```bash
# подставь реальный путь к проекту на VM:
cd /root/python/ab_game    # у тебя сейчас так (или /opt/kotelok/ab_game)
psql -h localhost -U roman -d communication -f sql/001_init.sql
psql -h localhost -U roman -d communication -c '\dt ab_game.*'
systemctl restart ab-game
```

---

## 2. systemd (исправление unit)

Скопировать актуальный unit из репо **или** записать вручную:

```bash
cp /opt/kotelok/ab_game/deploy/ab-game.service /etc/systemd/system/
# в файле обязательно:
#   User=root
#   WorkingDirectory=/opt/kotelok/ab_game
#   ExecStart=.../opt/kotelok/ab_game/.venv/bin/streamlit ... --server.port=8503

systemctl daemon-reload
systemctl enable --now ab-game
systemctl status ab-game
journalctl -u ab-game -n 50 --no-pager
```

`User=root` — linux-root, **не** роль в Postgres.

---

## 3. Nginx + HTTPS (конкретно по шагам)

1. Убедись, что Streamlit уже слушает **8503** (`ss -lptn | grep 8503`).
2. Скопируй конфиг и включи сайт:

```bash
# путь к репо подставь свой
cp /root/python/ab_game/deploy/nginx-ab-game.conf /etc/nginx/sites-available/ab-game
# или: cp /opt/kotelok/ab_game/deploy/nginx-ab-game.conf ...

ln -sf /etc/nginx/sites-available/ab-game /etc/nginx/sites-enabled/ab-game
nginx -t
systemctl reload nginx
```

3. В этом файле ничего про User нет. Важно только:
   - `server_name ab.kotelok.space;`
   - `proxy_pass http://127.0.0.1:8503;`
4. DNS уже должен отдавать IP этой VM (`dig +short ab.kotelok.space`).
5. Сертификат:

```bash
certbot --nginx -d ab.kotelok.space
```

6. Проверка: `curl -sI https://ab.kotelok.space`

---

## 4. Повседневное обновление

```bash
cd /opt/kotelok/ab_game
git pull
source .venv/bin/activate
pip install -r requirements.txt
systemctl restart ab-game
systemctl status ab-game
```

---

## Типичные грабли

| Симптом | Что делать |
|---------|------------|
| `relation "ab_game.round_parameters"` | `psql … -f sql/002_round_parameters.sql` |
| `relation "ab_game.users" does not exist` | §1б: `psql ... -f sql/001_init.sql` |
| `Port 8501 is already in use` | Использовать **8503**, не 8501/8502 |
| `status=217/USER` | Несуществующий `User=` в unit → `User=root` |
| `No matching distribution for numpy>=1.26` | `git pull` + актуальный `requirements.txt` |
| 502 Bad Gateway | `systemctl status ab-game`, есть ли слушатель на 8503 |
| Certbot fail | DNS ещё не указывает на VM / порт 80 |
| ImportError `kotelok_plotly` | нет `style/` после pull |
| WebSocket / белый экран | Upgrade/Connection в nginx (см. `deploy/nginx-ab-game.conf`) |
