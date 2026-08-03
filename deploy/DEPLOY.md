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

- [ ] **Порт:** не запускать на 8501 (`Port 8501 is already in use`). Только **8503**
- [ ] **systemd `217/USER`:** в `/etc/systemd/system/ab-game.service` должен быть существующий ОС-юзер  
      → ставь `User=root` (как wvs), пути `/opt/kotelok/ab_game`, порт **8503**  
      → затем `daemon-reload` + `restart` + `status` (см. §3)
- [ ] Smoke вручную на 8503 без ошибки порта:

```bash
cd /opt/kotelok/ab_game
.venv/bin/streamlit run ui/streamlit_app.py \
  --server.address 127.0.0.1 \
  --server.port 8503 \
  --server.headless true \
  --browser.gatherUsageStats false
# Ctrl+C после проверки
```

### Ещё предстоит

- [ ] DNS: A-запись `ab` → `45.132.18.2`; проверка `dig +short ab.kotelok.space`
- [ ] `settings.yaml` на сервере: `app.debug_mode: false`
- [ ] `secrets.yaml` (если нужны логи в PG): `logging_enabled` + host/user/password; схема `ab_game` через `sql/001_init.sql` при необходимости
- [ ] systemd: unit активен (`systemctl is-active ab-game` → `active`), автозапуск `enable`
- [ ] Nginx: сайт `ab-game` → proxy на `127.0.0.1:8503` (§4)
- [ ] HTTPS: `certbot --nginx -d ab.kotelok.space`
- [ ] Финальная проверка: `curl -sI https://ab.kotelok.space` и открытие в браузере

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
# один раз при логировании:
# psql -h localhost -U roman -d communication -f sql/001_init.sql
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

## 3. Nginx + HTTPS

```bash
cp /opt/kotelok/ab_game/deploy/nginx-ab-game.conf /etc/nginx/sites-available/ab-game
ln -sf /etc/nginx/sites-available/ab-game /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# когда DNS уже указывает на эту VM:
certbot --nginx -d ab.kotelok.space
```

Наружу открывать только 80/443; **8503** — только localhost.

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
| `Port 8501 is already in use` | Использовать **8503**, не 8501/8502 |
| `status=217/USER` | Несуществующий `User=` в unit → `User=root` |
| `No matching distribution for numpy>=1.26` | `git pull` + актуальный `requirements.txt` |
| 502 Bad Gateway | `systemctl status ab-game`, есть ли слушатель на 8503 |
| Certbot fail | DNS ещё не указывает на VM / порт 80 |
| ImportError `kotelok_plotly` | нет `style/` после pull |
| WebSocket / белый экран | Upgrade/Connection в nginx (см. `deploy/nginx-ab-game.conf`) |
