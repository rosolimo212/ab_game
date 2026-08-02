# Деплой ab_game на VM (та же, что wvs_bot)

Публичный URL: **https://ab.kotelok.space**  
Сервер: `45.132.18.2`  
Приложение: `127.0.0.1:8503` (8501 — template-streamlit, 8502 — wvs_bot).  
Код на VM: `/root/python/ab_game`  
Python на проде: **3.8.10** (отдельный апгрейд интерпретатора не нужен).

Стиль графиков (`style/kotelok_plotly.py` + `style/big_kettler.png`) лежит **в этом репозитории** — отдельно копировать `../style` не надо.

---

## 0. Однократно: DNS (reg.ru)

Зона `kotelok.space`:

| Тип | Имя (хост) | Значение |
|-----|------------|----------|
| A   | `ab` | `45.132.18.2` |

Проверка:

```bash
dig +short ab.kotelok.space
# → 45.132.18.2
```

Порты 80/443 и Postgres на этой VM уже используются wvs_bot — заново открывать обычно не нужно. Наружу **не** открывать 8503.

---

## 1. Код и venv (после git pull)

```bash
cd /root/python/ab_game
git pull

python3 -m venv .venv          # если ещё нет; python3 = 3.8.10 — ок
source .venv/bin/activate
pip install -U pip setuptools wheel
pip install -r requirements.txt
```

Ожидаемо ставится `numpy` линейки **1.24–1.25** и `streamlit` **< 1.40** (см. `requirements.txt`).

Прод-настройки:

```bash
# secrets.yaml — не в git; образец в AGENTS.md / README
nano secrets.yaml

# в settings.yaml на сервере:
#   app.debug_mode: false
#   app.logging_enabled: true   # если пишем в Postgres
nano settings.yaml
```

Схема БД (один раз, если логов ещё не было):

```bash
psql -h localhost -U roman -d communication -f sql/001_init.sql
```

Права пользователя Postgres — как у wvs_bot (та же БД `communication`, схема `ab_game`).

Проверка без nginx:

```bash
source .venv/bin/activate
streamlit run ui/streamlit_app.py \
  --server.address 127.0.0.1 \
  --server.port 8503 \
  --server.headless true
# Ctrl+C после smoke-check
```

---

## 2. Streamlit config (опционально)

`deploy/` рассчитан на флаги в systemd. При желании можно положить
`.streamlit/config.toml` (файл в `.gitignore` через локальные привычки;
в репо не коммитим секреты):

```toml
[server]
address = "127.0.0.1"
port = 8503
headless = true
enableCORS = false

[browser]
serverAddress = "ab.kotelok.space"
gatherUsageStats = false
```

---

## 3. systemd

```bash
cp deploy/ab-game.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now ab-game
systemctl status ab-game
journalctl -u ab-game -f
```

Unit: `WorkingDirectory=/root/python/ab_game`, порт **8503**, только localhost.

---

## 4. Nginx + HTTPS

```bash
cp deploy/nginx-ab-game.conf /etc/nginx/sites-available/ab-game
ln -sf /etc/nginx/sites-available/ab-game /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# когда DNS уже указывает на VM:
certbot --nginx -d ab.kotelok.space
```

Открыть: **https://ab.kotelok.space**

---

## 5. Обновление (повседневный pull)

```bash
cd /root/python/ab_game
git pull
source .venv/bin/activate
pip install -r requirements.txt
systemctl restart ab-game
systemctl status ab-game
```

Тексты UI — в `data/dialog_messages.json` (после pull достаточно restart).

---

## Чеклист

1. `dig +short ab.kotelok.space` → `45.132.18.2`
2. `systemctl is-active ab-game` → `active`
3. `ss -lptn | grep 8503` → `127.0.0.1:8503`
4. `curl -sI https://ab.kotelok.space` → 200/302
5. На сервере `app.debug_mode: false`
6. Есть `style/big_kettler.png` после pull

---

## Типичные грабли

| Симптом | Что проверить |
|---------|----------------|
| `No matching distribution for numpy>=1.26` | Старый pin; нужен актуальный `requirements.txt` (`numpy>=1.24,<1.26`) |
| 502 Bad Gateway | `systemctl status ab-game`, слушает ли 8503 |
| Certbot fail | DNS ещё не дошёл / порт 80 |
| ImportError `kotelok_plotly` | нет каталога `style/` в репо (должен приходить с git pull) |
| WebSocket / белый экран | заголовки Upgrade/Connection в nginx (см. `deploy/nginx-ab-game.conf`) |
| Порт занят | не использовать 8501/8502 — только **8503** |
