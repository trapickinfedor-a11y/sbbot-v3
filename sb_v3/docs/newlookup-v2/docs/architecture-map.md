# NewLookup — Архитектура и взаимосвязи

> Дата анализа: 2026-03-29
> Источник: статический анализ кода, grep по Python-файлам

---

## Компоненты

| Сервис | Порт | Тип | Описание |
|--------|------|-----|----------|
| `web_panel` | **:8000** | FastAPI | Admin-панель, 40+ роутеров, JWT auth, RBAC |
| `main_bot` | **:8080** (API) | aiogram + FastAPI | Основной Telegram-бот + внутренний HTTP API |
| `worker_bot` | **:8181** (API) | aiogram + FastAPI | Бот воркеров + внутренний HTTP API |
| `lookup_api` | **:8082** | FastAPI + SQLite | Отдельный поиск SSN/DL/CreditReport |
| `seller_bot` | — | aiogram | Бот продавцов (только DB) |
| `support_bot` | — | aiogram | Бот поддержки (DB + исходящие HTTP вызовы) |
| `marketer_bot` | — | aiogram | Бот маркетологов (исходящие HTTP вызовы) |
| `mirror_bot` | — | aiogram | Зеркальные боты (исходящие HTTP вызовы) |
| `worker_bot` | — | aiogram | Бот воркеров (только DB) |

### Базы данных

| БД | Путь | Engine | Кто использует |
|----|------|--------|----------------|
| **newlookup.db** | `./data/newlookup.db` (env: `DATABASE_URL=sqlite+aiosqlite:///./data/newlookup.db`) | SQLAlchemy async (aiosqlite) | main_bot, seller_bot, support_bot, marketer_bot, mirror_bot, worker_bot, web_panel |
| **lookup.db** | `/app/data/lookup.db` (env: `LOOKUP_DB_PATH`) | sqlite3 (sync) | lookup_api только |

**Замечание:** В `.env` задан `DATABASE_URL=sqlite+aiosqlite:///./data/newlookup.db`, при этом все боты и web_panel читают один и тот же файл. `shared/database/session.py` содержит ветвление sqlite vs postgresql для поддержки обеих СУБД.

---

## База данных newlookup.db

### Таблицы (из shared/database/models.py, 2804 строк)

| Таблица | Модель | Основные пользователи |
|---------|--------|-----------------------|
| `mirror_bots` | MirrorBot | main_bot (R/W), web_panel (R/W), mirror_bot (R) |
| `bot_owner_stats` | BotOwnerStats | main_bot (R/W), web_panel (R) |
| `bot_owners` | BotOwner | main_bot (R/W), web_panel (R/W) |
| `bot_owner_withdrawals` | BotOwnerWithdrawal | main_bot (R/W), web_panel (R/W) |
| `users` | User | main_bot (R/W), mirror_bot (R), web_panel (R/W), seller_bot (R) |
| `orders` | Order | support_bot (R/W), web_panel (R/W), worker_bot (R), seller_bot (R) |
| `bulk_order_items` | BulkOrderItem | support_bot (R/W), web_panel (R/W) |
| `worker_orders` | WorkerOrder | worker_bot (R/W), support_bot (R/W), web_panel (R) |
| `workers` | Worker | worker_bot (R/W), web_panel (R/W) |
| `worker_stats` | WorkerStats | worker_bot (R/W), web_panel (R) |
| `worker_withdrawals` | WorkerWithdrawal | worker_bot (R/W), web_panel (R/W) |
| `worker_expense_reports` | WorkerExpenseReport | worker_bot (R/W), web_panel (R) |
| `transactions` | Transaction | web_panel (R/W), shared/ledger_service (R/W) |
| `products` | Product | seller_bot (R/W), support_bot (R/W), web_panel (R/W) |
| `product_catalog_services` | ProductCatalogService | web_panel (R/W) |
| `mirror_menu_categories` | MirrorMenuCategory | main_bot (R/W), web_panel (R/W) |
| `product_purchases` | ProductPurchase | seller_bot (R/W), web_panel (R/W) |
| `product_ratings` | ProductRating | seller_bot (R/W), web_panel (R) |
| `product_action_logs` | ProductActionLog | seller_bot (R/W), web_panel (R) |
| `referrals` | Referral | marketer_bot (R/W), web_panel (R) |
| `support_tickets` | SupportTicket | support_bot (R/W), web_panel (R/W) |
| `support_messages` | SupportMessage | support_bot (R/W), web_panel (R/W) |
| `support_ticket_messages` | SupportTicketMessage | support_bot (R/W), web_panel (R/W) |
| `complaints` | Complaint | web_panel (R/W), worker_bot (via notify) |
| `broadcasts` | Broadcast | web_panel (R/W), main_bot (R) |
| `broadcast_translations` | BroadcastTranslation | web_panel (R/W) |
| `ui_translations` | UiTranslation | seller_bot (R, via ui_translation_service) |
| `reports` | Report | web_panel (R/W) |
| `sellers` | Seller | seller_bot (R/W), support_bot (R/W), web_panel (R/W) |
| `seller_helpers` | SellerHelper | seller_bot (R/W), web_panel (R/W) |
| `seller_deposit_payments` | SellerDepositPayment | seller_bot (R/W), web_panel (R/W) |
| `seller_helper_audit_logs` | SellerHelperAuditLog | seller_bot (R/W), web_panel (R) |
| `seller_upload_batches` | SellerUploadBatch | seller_bot (R/W), web_panel (R/W) |
| `seller_upload_templates` | SellerUploadTemplate | seller_bot (R/W), web_panel (R/W) |
| `seller_banks` | SellerBank | seller_bot (R/W), web_panel (R/W) |
| `seller_orders` | SellerOrder | seller_bot (R/W), support_bot (R/W), web_panel (R/W) |
| `seller_withdrawals` | SellerWithdrawal | seller_bot (R/W), web_panel (R/W) |
| `seller_conversations` | SellerConversation | seller_bot (R/W), support_bot (R) |
| `seller_chats` | SellerChat | seller_bot (R/W) |
| (и другие таблицы в models.py) | — | — |

---

## Взаимосвязи

### HTTP API вызовы (сервис → сервис)

| Откуда | Куда | Метод | Endpoint | Библиотека | ENV переменная |
|--------|------|-------|----------|------------|----------------|
| `support_bot` | `main_bot:8080` | POST | `/api/notify-order-cancelled` | aiohttp | хардкод |
| `support_bot` | `main_bot:8080` | POST | `/api/notify-addinfo-completed` | aiohttp | хардкод |
| `support_bot` | `main_bot:8080` | POST | `/api/notify-bulk-item-completed` | aiohttp | хардкод |
| `support_bot` | `main_bot:8080` | POST | `/api/notify-bulk-order-completed` | aiohttp | хардкод |
| `support_bot` | `main_bot:8080` | POST | `/api/notify-single-order-completed` | aiohttp | хардкод |
| `web_panel` | `main_bot:8080` | POST | `/bot/toggle` | httpx | хардкод |
| `web_panel` | `main_bot:8080` | POST | `/api/notify-balance-update` | httpx | хардкод |
| `web_panel` | `worker_bot:8181` | POST | (order notifications) | aiohttp | `WORKER_BOT_API_URL` |
| `marketer_bot` | `main_bot:8080` | POST | `/bot/toggle` | httpx | `MAIN_BOT_API_URL_INTERNAL` |
| `mirror_bot` | `main_bot:8080` | POST | `/api/v1/coupons/activate` | httpx | `MAIN_BOT_API_URL` |
| `shared/order_notification_service` | `worker_bot:8181` | POST | (notifications) | aiohttp | `WORKER_BOT_API_URL` |

**Внутренняя аутентификация:** все HTTP-вызовы между сервисами используют `INTERNAL_API_TOKEN` через хелпер `build_internal_api_headers()` из `shared/security/internal_api.py`.

#### Эндпоинты main_bot (:8080)

```
POST /bot/toggle                      — включить/выключить mirror bot
GET  /bot/status/{bot_id}             — статус бота
POST /notify-bulk-item-completed      — уведомить покупателя (bulk позиция)
POST /notify-bulk-order-completed     — уведомить покупателя (bulk заказ)
POST /notify-single-order-completed   — уведомить покупателя (одиночный заказ)
POST /notify-addinfo-completed        — уведомить покупателя (addinfo)
POST /notify-balance-update           — уведомить о пополнении баланса
POST /notify-order-cancelled          — уведомить об отмене заказа
GET  /orders/my                       — заказы пользователя
POST /users/me/set-archive-channel    — задать архивный канал
POST /api/v1/coupons/activate         — активировать купон
```

### Telegram взаимодействия (бот ↔ бот через DB или API)

| Сценарий | Механизм |
|----------|----------|
| `main_bot` → покупатель (через mirror bot) | main_bot читает `mirror_bots` из DB, создаёт `Bot(token=mirror_bot.bot_token)`, отправляет сообщение от имени зеркального бота |
| `support_bot` → покупатель | support_bot вызывает `main_bot:8080` → main_bot доставляет через mirror bot |
| `web_panel` → покупатель | web_panel вызывает `main_bot:8080/api/notify-*` → main_bot доставляет |
| `marketer_bot` → main_bot | HTTP POST на `main_bot:8080/bot/toggle` для активации/деактивации mirror bot |
| `main_bot` использует `SUPPORT_BOT_TOKEN` | main_bot/app/api/notifications.py создаёт `Bot(token=support_bot_token)` — прямая отправка в support chat |

### Прямой импорт Python-модулей (не HTTP)

| Модуль-потребитель | Что импортирует |
|--------------------|-----------------|
| `support_bot` | `from web_panel.constants.categories import (...)` |
| `support_bot` | `from web_panel.auth import ROLE_ADMIN, ROLE_SUPER_ADMIN` |
| `support_bot/services/access_service.py` | `from web_panel.auth import (...)` |
| Все боты | `from shared.database.models import *` |
| Все боты | `from shared.database.session import async_session_maker, get_session` |
| Все боты | `from shared.services.*` (40+ сервисов) |
| Все боты | `from shared.config.env_utils import *` |
| Все боты | `from shared.middlewares.error_logging import GlobalErrorLoggingMiddleware` |
| `seller_bot` | `from shared.security.internal_api import *` |
| `main_bot`, `worker_bot` | `from shared.database.tasks_session import init_tasks_db` |

---

## Общие модули (shared/)

```
shared/
├── database/
│   ├── models.py          (2804 строк, 20+ моделей, единая схема)
│   ├── session.py         (async engine, sqlite/postgresql ветвление)
│   └── tasks_session.py   (отдельная сессия для задач)
├── services/              (49 сервисов)
│   ├── ledger_service.py  (1072 строки, escrow/транзакции)
│   ├── seller_*_service.py (10+ сервисов для seller flow)
│   ├── notification_service.py
│   ├── order_notification_service.py  (вызывает worker_bot:8181)
│   ├── btcpay_service.py
│   ├── nocodb_service.py
│   └── ...
├── config/
│   ├── env_utils.py       (validate_startup_env, parse_int_env)
│   └── settings.py        (Redis URL, Celery)
├── security/
│   └── internal_api.py    (INTERNAL_API_TOKEN, build_internal_api_headers)
├── middlewares/
│   └── error_logging.py   (GlobalErrorLoggingMiddleware)
├── utils/                 (seller_product_meta, telegram_auth и др.)
├── catalog.py / cc_catalog.py / catalog_banks.py
└── nocodb/
```

---

## Диаграмма потоков данных

```
┌─────────────────────────────────────────────────────────────────────┐
│                      TELEGRAM USERS                                  │
└──────────┬──────────────┬──────────────┬───────────────┬────────────┘
           │              │              │               │
           ▼              ▼              ▼               ▼
    ┌─────────────┐ ┌───────────┐ ┌──────────┐ ┌───────────────┐
    │  mirror_bot │ │seller_bot │ │ main_bot │ │  worker_bot   │
    │  (dynamic)  │ │           │ │  :8080   │ │    :8181      │
    └──────┬──────┘ └─────┬─────┘ └────┬─────┘ └──────┬────────┘
           │ httpx         │            │ aiogram        │
           │ POST coupons  │            │ (Bot API)      │
           │               │            │                │
           ▼               │            │                │
    ┌─────────────────────────────────────────────────────────────┐
    │                  shared/database/                            │
    │              newlookup.db  (SQLite)                          │
    │  models: users, orders, mirror_bots, sellers, workers, ...   │
    └──────────────────────────────┬──────────────────────────────┘
                                   │
           ┌───────────────────────┼──────────────────────────┐
           │                       │                          │
           ▼                       ▼                          ▼
    ┌─────────────┐         ┌─────────────┐          ┌──────────────┐
    │support_bot  │         │marketer_bot │          │  web_panel   │
    │             │         │             │          │    :8000     │
    └──────┬──────┘         └──────┬──────┘          └──────┬───────┘
           │ aiohttp                │ httpx                  │ httpx
           │ POST notify-*          │ POST /bot/toggle        │ POST /bot/toggle
           │                        │                        │ POST notify-balance
           └────────────────────────┴────────────────────────┘
                                    │
                                    ▼
                           ┌────────────────┐
                           │   main_bot     │
                           │   :8080        │
                           │  (HTTP API +   │
                           │   aiogram Bot) │
                           └────────────────┘
                                    │
                              Bot(token=mirror_bot.bot_token)
                                    │
                                    ▼
                           ┌────────────────┐
                           │  mirror_bots   │
                           │  (dynamic TG   │
                           │   Bot tokens   │
                           │   from DB)     │
                           └────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                         lookup_api  :8082                            │
│                     lookup.db (отдельная SQLite)                     │
│                     SSN / DL / CreditReport поиск                    │
│                     CORS: http://localhost:8000 (web_panel)          │
└─────────────────────────────────────────────────────────────────────┘

Условные обозначения:
  ─── DB read/write (SQLAlchemy async, shared/database/session.py)
  ──► HTTP вызов (aiohttp / httpx, auth: INTERNAL_API_TOKEN)
  ···► прямой Python import (один процесс или PYTHONPATH)
```

---

## Ключевые наблюдения и риски

### 1. Единая БД для всех ботов
Все 6 ботов + web_panel пишут в один файл `newlookup.db` через SQLAlchemy async. SQLite не поддерживает конкурентную запись без WAL-режима. В `shared/database/session.py` есть специальная обработка для SQLite (ветвление по `_is_sqlite`).

### 2. Хардкод Docker-имён хостов
`http://main_bot:8080` и `http://worker_bot:8181` — Docker-имена сервисов. При запуске вне Docker (локально) нужно переопределить через ENV:
- `MAIN_BOT_API_URL` / `MAIN_BOT_API_URL_INTERNAL` → `http://localhost:8080`
- `WORKER_BOT_API_URL` → `http://localhost:8181`

### 3. Две разные ENV переменные для main_bot API
- `mirror_bot` использует `MAIN_BOT_API_URL` (default: `http://localhost:8080/api/v1`)
- `marketer_bot` использует `MAIN_BOT_API_URL_INTERNAL` (default: `http://main_bot:8080`)
- При локальном запуске нужно выставить обе.

### 4. support_bot импортирует web_panel напрямую
`support_bot` делает `from web_panel.auth import ...` — это Python-импорт, не HTTP. Значит оба сервиса должны запускаться с общим `PYTHONPATH` (например, из корня проекта).

### 5. lookup_api изолирован
`lookup_api` использует отдельную БД (`lookup.db`), не имеет доступа к `newlookup.db`, взаимодействует только с `web_panel` через CORS.

### 6. main_bot управляет зеркальными ботами динамически
main_bot читает `mirror_bots` из БД, создаёт `Bot(token=...)` на лету. При включении/выключении зеркального бота web_panel/marketer_bot вызывают `POST /bot/toggle` на main_bot.
