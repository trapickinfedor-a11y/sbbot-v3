# SBBot v3 — Project Root

**Product:** Multi-search Telegram bot v3
**APIs:** usfull.pro (SSN/DL/CR) + Enformion (phone/address/email/batch)
**Дата:** 2026-05-17

---

## Структура проекта

```
sb_v3/
├── core/                          ← Python Telegram бот (3,672 строк)
│   ├── bot.py                     ← Main bot: handlers, keyboards, FSM
│   ├── usfull_engine.py           ← usfull.pro API client (SSN/DL/CR/Credit Score)
│   ├── sb_engine.py               ← Enformion API client (phone/address/batch)
│   ├── database.py                ← SQLite база (users, accounts, logs)
│   ├── formatters.py              ← Результаты → текст/TXT/CSV/JSON экспорт
│   ├── formatter.py               ← Legacy formatter
│   ├── matching.py                ← Match fullz, deduplication
│   ├── payments.py                ← Payment manager (CryptoPay/Cryptomus/Helekit/BTCPay)
│   ├── validators.py              ← Input validation
│   ├── api.py                    ← REST API endpoints
│   ├── celery_worker.py           ← Celery background tasks
│   ├── admin_panel.py             ← FastAPI admin panel (port 3111)
│   ├── schema.ts                  ← Drizzle schema
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── docker-compose.override.yml ← local overrides
│   ├── requirements.txt
│   └── tests/                     ← 125 unit tests
│       ├── conftest.py
│       ├── test_usfull_engine.py  (40 tests)
│       ├── test_sb_engine.py      (68 tests)
│       └── test_bot_helpers.py    (17 tests)
│
├── client/                         ← React админка
│   └── src/
│       ├── App.tsx
│       ├── pages/ (Home, ControlPlane*, ComponentShowcase)
│       ├── components/ (DashboardLayout, AIChatBox, Map)
│       └── components/ui/ (40+ shadcn/ui)
│
├── server/                         ← Express + tRPC backend
├── shared/                         ← Shared types
├── drizzle/                        ← DB migrations
├── user_attachment/               ← Real data samples
├── patches/                       ← Dependency patches
├── scripts/                       ← Utility scripts
├── deploy.sh                      ← Deploy script (start/stop/restart/admin/full)
│
└── docs/
    ├── ALGORITHMS.md              ← Полный reference алгоритмов (10 секций)
    ├── API_REFERENCE.md           ← 8 API endpoints с примерами
    ├── PLAN.md                    ← Roadmap
    ├── README.md                  ← Этот файл
    ├── ONE_CS_docs/              ← ONE CS credit scoring docs
    ├── NEWLOOKUP_docs/            ← Telegram marketplace docs
    ├── SBBot_v2_docs/            ← SearchBug Bot v2 docs
    └── audit/                    ← Deployment & audit docs
```

---

## Запуск

```bash
# 1. Копировать и заполнить .env
cp core/.env.example core/.env

# 2. Инициализировать БД
./deploy.sh migrate

# 3. Запустить бота
./deploy.sh start

# 4. Admin panel (port 3111)
./deploy.sh admin

# Docker (full pipeline)
./deploy.sh full   # migrate + start + status
```

**Переменные окружения (.env):**
- `BOT_TOKEN` — токен Telegram бота (обязательно)
- `USFULL_API_KEY` — API ключ usfull.pro
- `ADMIN_USER_IDS` — ID админов через запятую (опционально)
- `ADMIN_SECRET` — секрет админ-панели
- `CRYPTOBOT_TOKEN`, `HELEKET_API_KEY`, `BTCPAY_*` — платёжные провайдеры

---

## Admin Panel

FastAPI-панель на порту **3111** (`core/admin_panel.py`):
- `/?admin_id=N` — главная статистика
- `/accounts?admin_id=N` — управление аккаунтами Enformion + Usfull.pro
- `/users?admin_id=N` — пользователи, бан/разбан
- `/prices?admin_id=N` — цены поисков
- `/logs?admin_id=N` — админ-логи + webhook-события
- `/settings?admin_id=N` — все ключи settings
- `/api/enf_status` — статус пула Enformion
- `/api/uf_status` — статус пула Usfull.pro

---

## Тесты

```bash
cd core && python3 -m pytest tests/ -v
# 125 passed, 1 warning
```

- `tests/test_usfull_engine.py` — 40 тестов (DOB, HealthScore, CircuitBreaker, UsfullEngine)
- `tests/test_sb_engine.py` — 68 тестов (headers, galaxy search type, account parsing, response parsing, endpoint dispatch, HTTP error handling, EmailRep)
- `tests/test_bot_helpers.py` — 17 тестов (DOB normalization, extract_ssn_params, extract_person_for_ssf/dl)

---

## Развёртывание

- `deploy.sh` — start/stop/restart/status/logs/shell/migrate/test/admin/full
- `core/docker-compose.override.yml` — local overrides (ports, volumes, healthcheck)
- `core/Dockerfile` — multi-stage build

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
```

**Enformion circuit breaker:** открыт при >30% ошибок в окне 20 запросов.
**HealthScore.score()** = 80.5 после 1× `record_ok()` (формула: `(error_rate×50)+(latency_score)+(ok_bonus×0.5)−error_penalty`)

**Known bug:** `_normalize_dob("15.01.1985")` → `"19851501"` (DD.MM.YYYY читается как ISO MM.DD.YYYY).

---

## Быстрый старт

```bash
cd sb_v3/core
pip install -r requirements.txt
export BOT_TOKEN="your_bot_token"
python bot.py
```

---

## Три продукта в одном репозитории

| Продукт | Стек | Назначение |
|---------|------|-------------|
| **SB v3 (бот)** | Python/Telegram/SQLite | Telegram бот: usfull + Enformion |
| **SBBot v2 (документы)** | Python/Telegram | SearchBug phone/address batch lookup |
| **ONE CS docs** | TypeScript/React | Credit scoring engine docs + admin panel |
| **NewLookup (документы)** | Python/Telegram/Docker | Full marketplace docs |

---

## API Endpoints (usfull pro)

### usfull_engine.py
```
POST /api/search/             — SSN/DOB lookup
POST /api/dl/                 — Driver License lookup
POST /api/cr/                 — Credit Report lookup
GET  /api/get_balance/        — Balance check
POST /api/create_token/       — Create API key
```

### api.py (SB v3)
```
POST /api/v1/requests/single  — Single check
POST /api/v1/requests/bulk    — Bulk batch
GET  /api/v1/jobs/:id         — Job status
GET  /api/v1/usage/summary    — Usage + cost
```