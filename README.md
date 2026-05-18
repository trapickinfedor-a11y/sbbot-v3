# SBBot v3 — Project Root

**Product:** Multi-search Telegram bot v3 + REST API
**APIs:** usfull.pro (SSN/DL/CR) + Enformion (phone/address/email/batch)
**Дата:** 2026-05-18

---

## Структура проекта

```
sb_v3/
├── core/                          ← Python Telegram бот (3,672 строк)
│   ├── bot.py                     ← Main bot: handlers, keyboards, FSM
│   ├── usfull_engine.py           ← usfull.pro API client (SSN/DL/CR/Credit Score)
│   ├── sb_engine.py               ← Enformion API client (phone/address/batch)
│   ├── database.py                ← SQLite база (users, accounts, logs, api_keys)
│   ├── formatters.py              ← Результаты → текст/TXT/CSV/JSON экспорт
│   ├── payments.py                ← Payment manager (CryptoPay/Helekit/BTCPay)
│   ├── api.py                     ← REST API server (FastAPI, port 8081)
│   ├── admin_panel.py             ← Admin panel (FastAPI, port 3111)
│   ├── celery_worker.py           ← Celery background tasks
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── docker-compose.override.yml
│   ├── requirements.txt
│   ├── deploy.sh                  ← Deploy script
│   ├── .env.example               ← Environment variables template
│   └── tests/                     ← 125 unit tests (100% pass)
│       ├── conftest.py
│       ├── test_usfull_engine.py  (40 tests)
│       ├── test_sb_engine.py      (68 tests)
│       └── test_bot_helpers.py     (17 tests)
│
├── docs/
│   ├── README.md                  ← Этот файл
│   ├── PLAN.md                    ← Roadmap
│   ├── ALGORITHMS.md             ← Полный reference алгоритмов (10 секций)
│   ├── API_DOC.md                 ← REST API документация + SDK examples
│   ├── API_REFERENCE.md          ← 8 API endpoints с примерами
│   ├── ONE_CS_docs/              ← ONE CS credit scoring docs
│   ├── NEWLOOKUP_docs/            ← Telegram marketplace docs
│   ├── SBBot_v2_docs/            ← SearchBug Bot v2 docs
│   └── audit/                    ← Deployment & audit docs
```

---

## Быстрый старт

```bash
# 1. Копировать и заполнить .env
cp core/.env.example core/.env

# 2. Установить зависимости
pip install -r core/requirements.txt

# 3. Инициализировать БД
./deploy.sh migrate

# 4. Запустить бота
./deploy.sh start

# 5. Admin panel (port 3111)
./deploy.sh admin

# Docker (всё сразу)
./deploy.sh full
```

---

## Запуск

### Переменные окружения (.env)

```bash
# Обязательно
BOT_TOKEN=your_telegram_bot_token

# usfull.pro API
USFULL_API_KEY=your_usfull_api_key

# Enformion — через бота: /addaccount или db напрямую

# Платёжные
CRYPTOBOT_TOKEN=
HELEKET_API_KEY=
HELEKET_MERCHANT_ID=
BTCPAY_BASE_URL=
BTCPAY_API_KEY=
BTCPAY_STORE_ID=

# Админ-панель
ADMIN_USER_IDS=123456,789012     # опционально
ADMIN_SECRET=change-me

# EmailRep
EMAILREP_KEY=
```

---

## Admin Panel (FastAPI, порт 3111)

**Управление:** `/accounts`, `/users`, `/prices`, `/logs`, `/settings`
**API:** `/api/enf_status`, `/api/uf_status`, `/api/stats`
**Auth:** `?admin_id=YOUR_ID`

---

## REST API (FastAPI, порт 8081)

### Быстрый старт API

```bash
# Создать ключ в Telegram
/apikey create

# Использовать
curl -X GET "http://localhost:8081/v1/limits" \
  -H "X-API-Key: sk_your_key_here"
```

### Endpoints

| Метод | Endpoint | Описание |
|-------|----------|---------|
| GET | `/health` | Liveness |
| GET | `/v1/prices` | Прайс-лист (12 типов) |
| GET | `/v1/limits` | Лимиты ключа |
| GET | `/v1/tiers` | Тарифные планы |
| POST | `/v1/search` | Один поиск (валидация) |
| POST | `/v1/search/batch` | Батч до 20 запросов |

### Search Types (12 типов)

| Type | Цена | API | Валидация |
|------|-----:|-----|-----------|
| phone | $3.00 | Enformion | 7-15 цифр |
| address | $1.20 | Enformion | first_name + last_name |
| background | $3.50 | Enformion | first_name + last_name |
| phone_identify | $1.00 | Enformion | 7-15 цифр |
| phone_verify | $1.00 | Enformion | 7-15 цифр |
| address_verify | $0.80 | Enformion | first_name + last_name + address |
| email_verify | $0.60 | Enformion | email format |
| emailrep | $0.40 | EmailRep.io | email format |
| ssn_dob | $1.50 | Usfull.pro | first_name + last_name + dob/ssn |
| driver_license | $3.00 | Usfull.pro | first_name + last_name + state |
| credit_report | $6.00 | Usfull.pro | first_name + last_name + dob + ssn |
| credit_score | $4.00 | Usfull.pro | first_name + last_name + dob + ssn |

### API Tier Pricing

| Tier | $/мес | Запросов/день | Rate/min |
|------|-------:|---------------:|--------:|
| Starter | $29.99 | 100 | 10 |
| Pro | $99.99 | 500 | 30 |
| Enterprise | $299.99 | 2,000 | 60 |
| Unlimited | $999.99 | ∞ | 300 |

**Полная документация:** `docs/API_DOC.md`

---

## Команды бота

```
/start            — Начать
/admin            — Админ-панель (admin only)
/balance          — Баланс
/health           — Системный статус
/enfstatus        — Enformion pool статус
/addaccount       — Добавить Enformion аккаунт
/loadaccounts     — Загрузить аккаунты из БД
/reloadpool       — Перезагрузить пул
/setufkey         — Установить usfull API ключ
/setpayment       — Настройка платежей
/apikey           — Управление API ключами
/apikey create    — Создать ключ
/apikey tiers     — Тарифы API
/apikey revoke    — Отозвать ключ
/apikey upgrade   — Сменить tier
/api              — Статус API доступа
/shutdown         — Остановить бота (admin only)
/ban /unban       — Бан/разбан пользователя
```

---

## Тесты

```bash
cd core && python3 -m pytest tests/ -v

# 125 passed, 0 failed
# test_usfull_engine.py — 40 tests
# test_sb_engine.py    — 68 tests
# test_bot_helpers.py  — 17 tests
```

---

## Развёртывание

```bash
./deploy.sh start    # запустить
./deploy.sh stop     # остановить
./deploy.sh restart  # перезапустить
./deploy.sh status   # статус
./deploy.sh logs     # логи
./deploy.sh migrate  # миграция БД
./deploy.sh admin    # admin panel (3111)
./deploy.sh full     # migrate + start + status
```

---

## Архитектура

```
bot.py (Telegram handlers) → usfull_engine.py + sb_engine.py
                                   ↓              ↓
                              usfull.pro      Enformion
                                   ↓              ↓
                             database.py (SQLite, 16 tables)
                                   ↓
                              payments.py (CryptoBot/Heleket/BTCPay)
                                   ↓
                               api.py (FastAPI, :8081) ← REST API
```

**Enformion circuit breaker:** открыт при >30% ошибок в окне 20 запросов.

---

## Known Issues

- `_normalize_dob("15.01.1985")` → `"19851501"` (DD.MM.YYYY читается как ISO MM.DD.YYYY)
- Subscription plans (Basic $9.99, Pro $29.99, Enterprise $99.99) убыточны — рекомендуется per-search billing