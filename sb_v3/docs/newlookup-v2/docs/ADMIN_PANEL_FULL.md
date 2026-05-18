# Админ-панель: полная структура и управление

## 1. Обзор

- **Стек:** FastAPI, Jinja2, PostgreSQL, SQLite (tasks)
- **Запуск:** `python web_panel/run.py` или uvicorn
- **URL:** `http://0.0.0.0:8000` (порт из `WEB_PANEL_PORT`)
- **Логин:** `ADMIN_USERNAME` / `ADMIN_PASSWORD` (по умолчанию admin / admin123)

---

## 2. Конфигурация (web_panel/config.py)

| Переменная | Описание | По умолчанию |
|-----------|----------|--------------|
| `WEB_PANEL_PORT` | Порт | 8000 |
| `WEB_PANEL_SECRET_KEY` | JWT secret | автогенерация |
| `ADMIN_USERNAME` | Логин первого админа | admin |
| `ADMIN_PASSWORD` | Пароль первого админа | admin123 |
| `DATABASE_URL` | PostgreSQL | postgresql+asyncpg://... |
| `TASKS_DATABASE_URL` | БД задач (SQLite) | data/tasks.db |
| `SUPPORT_BOT_TOKEN` | Токен Support бота | — |
| `MAIN_BOT_TOKEN` | Токен Main бота | — |
| `ORDERS_CHANNEL_ID` | ID канала заказов | 0 |
| `INSTRUCTIONS_TUTORIAL_URL` | URL туториалов | https://t.me/ONE_TUTORIAL |
| `NOCODB_BASE_URL`, `NOCODB_API_TOKEN`, `NOCODB_TABLE_ID` | NocoDB синхронизация | — |

---

## 3. Авторизация (web_panel/auth.py)

- **JWT** (HS256), срок жизни 24 часа
- **Роли:** `super_admin`, `owner`, `admin`, `finance`, `accountant`, `moderator`, `support`, `uploader`, `viewer`, `custom`
- **Dependencies:**
  - `get_current_user` — текущий админ из токена
  - `require_role("super_admin", ...)` — проверка роли
- **Первый админ:** создаётся из env при пустой таблице `admins`

---

## 4. Навигация (web_panel/templates/_nav.html)

**Хардкод.** Группы и пункты:

| Группа | Пункты | active_page |
|--------|--------|-------------|
| Аналитика | Обзор, Finance Hub, Аналитика, Отчёты | dashboard, finance, analytics, reports |
| Юзеры | Пользователи, Боты, Депозиты | users, bots, deposits |
| Команда | Воркеры, Worker CRM, Селлеры, Seller CRM, Маркетологи | workers, worker_crm, sellers, seller_crm, marketers |
| Заказы | Заказы, Disputes, Жалобы, Чат | orders, disputes, complaints, support |
| Каталог | Товары, Банки, Brute Bank, Аккаунты, eSIM, CC, Education, Another | products, banks, brute_bank, accounts, esim, cc, education, another-services |
| Настройки | Цены, Категории, Рассылки, Инструкции | service-prices, categories, broadcasts, instructions |
| Система | Audit для `support`/`moderator`/`finance`/`admin`/`super_admin`; Админы и Роли только для `super_admin` | audit, admins, admin_roles |
---

## 5. Страницы и роуты (web_panel/main.py)

| URL | Шаблон | active_page |
|-----|--------|-------------|
| `/` | index.html | — |
| `/dashboard` | dashboard.html | dashboard |
| `/analytics` | analytics.html | analytics |
| `/finance` | finance.html | finance |
| `/reports` | reports.html | reports |
| `/users` | users.html | users |
| `/bots` | bots.html | bots |
| `/deposits` | deposits.html | deposits |
| `/workers` | workers.html | workers |
| `/worker-crm` | worker_crm.html | worker_crm |
| `/sellers` | sellers.html | sellers |
| `/seller-moderation` | seller_moderation.html | seller_moderation |
| `/seller-crm` | seller_crm.html | seller_crm |
| `/marketers` | marketers.html | marketers |
| `/orders` | orders.html | orders |
| `/disputes` | disputes.html | disputes |
| `/complaints` | complaints.html | complaints |
| `/support` | support_chat.html | support |
| `/support-old` | support_tickets.html | support |
| `/products` | products.html | products |
| `/banks` | bank_items.html | banks |
| `/brute-bank` | brute_bank.html | brute_bank |
| `/accounts` | accounts.html | accounts |
| `/esim` | esim.html | esim |
| `/cc` | cc.html | cc |
| `/education` | education.html | education |
| `/another-services` | another_services.html | another-services |
| `/service-prices` | service_prices.html | service-prices |
| `/categories` | categories_new.html | categories |
| `/broadcasts` | broadcasts.html | broadcasts |
| `/instructions` | instructions.html | instructions |
| `/admins` | admins.html | admins |
| `/admin-roles` | admin_roles.html | admin_roles |
| `/audit` | audit.html | audit |
| `/checks` | checks.html | checks |
| `/health` | — | — |

---

## 6. API роутеры

| Prefix | Файл | Описание |
|--------|------|----------|
| `/api/auth` | auth.py | Логин, /me, refresh |
| `/api/workers` | workers.py | Воркеры |
| `/api/users` | users.py | Пользователи |
| `/api/bots` | bots.py | Боты |
| `/api/orders` | orders.py | Заказы |
| `/api/analytics` | analytics.py | Аналитика |
| `/api/reports` | reports.py | Отчёты |
| `/api/support-tickets` | support_tickets.py | Тикеты |
| `/api/complaints` | complaints.py | Жалобы |
| `/api/broadcasts` | broadcasts.py | Рассылки |
| `/api/dashboard` | dashboard.py | Дашборд |
| `/api/telegram` | telegram_sync.py | Синхронизация Telegram |
| `/api/files` | files.py | Файлы |
| `/api/products` | products.py | Товары |
| `/api/deposits` | deposits.py | Депозиты |
| `/api/bank-items` | bank_items.py | Банки (BankItem) |
| `/api/service-prices` | service_prices.py | Цены сервисов |
| `/api/sellers` | sellers.py | Селлеры |
| `/api/banks` | banks.py | Банки (SellerBank) |
| `/api/admins` | admins.py | Админы (super_admin) |
| `/api/audit` | audit.py | Аудит |
| `/api/checks` | checks.py | Проверки доставки |
| `/api/brute-bank` | brute_bank.py | Brute Bank |
| `/api/seller-moderation` | seller_moderation.py | Модерация селлеров |
| `/api/cc` | cc_catalog.py, cc.py | CC каталог |
| `/api/accounts` | accounts.py | Аккаунты |
| `/api/esim` | esim.py | eSIM |
| `/api/education` | education.py | Education |
| `/api/another-services` | another_services.py | Another Services |
| `/api/seller-crm` | seller_crm.py | Seller CRM, disputes, withdrawals |
| `/api/marketers` | marketers.py | Маркетологи |
| `/api/admin-roles` | admin_roles.py | Кастомные роли |
| `/api/export` | export.py | Экспорт |
| `/api/categories` | categories.py | Категории (Category/Service) |

---

## 7. Ключевые API эндпоинты

### Auth
- `POST /api/auth/login` — логин
- `GET /api/auth/me` — текущий пользователь
- `POST /api/auth/refresh` — обновление токена

### Admins (super_admin)
- `GET /api/admins` — список
- `POST /api/admins` — создать
- `GET /api/admins/{id}` — один
- `PUT /api/admins/{id}` — обновить
- `DELETE /api/admins/{id}` — удалить

### Admin Roles (super_admin)
- `GET /api/admin-roles` — список ролей
- `POST /api/admin-roles` — создать
- `PATCH /api/admin-roles/{id}` — обновить
- `DELETE /api/admin-roles/{id}` — удалить

### Seller CRM
- `GET /api/seller-crm/orders` — Kanban заказов
- `PATCH /api/seller-crm/orders/{order_type}/{id}` — статус заказа
- `GET /api/seller-crm/disputes` — очередь seller disputes
- `POST /api/seller-crm/disputes/{id}/resolve` — решение спора
- `POST /api/seller-crm/disputes/{id}/appeal` — запрос апелляции
- `GET /api/seller-crm/withdrawals` — основной seller payout flow
- `POST /api/seller-crm/withdrawals/{id}/approve` — одобрить
- `POST /api/seller-crm/withdrawals/{id}/reject` — отклонить
- `GET /api/seller-crm/withdrawal-tasks` — compatibility alias над тем же flow
- `GET /api/seller-crm/withdrawals` — legacy main-DB flow (`SellerWithdrawal`), держать только для совместимости/миграции
- `POST /api/seller-crm/withdrawals` — legacy create path
- `POST /api/seller-crm/withdrawals/{id}/approve` — legacy approve path
- `POST /api/seller-crm/withdrawals/{id}/reject` — legacy reject path

### Marketers
- `GET /api/marketers` — список
- `GET /api/marketers/withdrawals` — заявки на вывод
- `POST /api/marketers/withdrawals/{id}/approve` — одобрить
- `POST /api/marketers/withdrawals/{id}/reject` — отклонить

### Categories
- `GET /api/categories` — список категорий
- `POST /api/categories` — создать
- `PUT /api/categories/{id}` — обновить
- `DELETE /api/categories/{id}` — удалить
- `POST /api/categories/{id}/toggle` — вкл/выкл

---

## 8. Шаблоны (web_panel/templates)

| Базовый | Описание |
|---------|----------|
| `_base.html` | Базовый layout |
| `_nav.html` | Навигация (include) |

| Страница | Описание |
|----------|----------|
| index.html | Логин |
| dashboard.html | Обзор |
| analytics.html | Аналитика |
| reports.html | Отчёты |
| users.html | Пользователи |
| bots.html | Боты |
| deposits.html | Депозиты |
| workers.html | Воркеры |
| sellers.html | Селлеры |
| seller_moderation.html | Модерация |
| seller_crm.html | Kanban + disputes + заявки на вывод |
| finance.html | Finance Hub |
| disputes.html | Standalone disputes queue |
| marketers.html | Маркетологи |
| orders.html | Заказы |
| complaints.html | Жалобы |
| support_chat.html | Чат |
| support_tickets.html | Тикеты |
| products.html | Товары |
| bank_items.html | Банки |
| brute_bank.html | Brute Bank |
| accounts.html | Аккаунты |
| esim.html | eSIM |
| cc.html | CC |
| education.html | Education |
| another_services.html | Another |
| service_prices.html | Цены |
| categories.html | Категории (старая) |
| categories_new.html | Категории (новая) |
| broadcasts.html | Рассылки |
| instructions.html | Инструкции |
| admins.html | Админы |
| admin_roles.html | Роли |
| audit.html | Аудит |
| checks.html | Проверки |
| services.html | Сервисы |

---

## 9. БД и модели

### Основная (PostgreSQL)
- `admins`, `admin_audit_logs`, `admin_roles`
- `users`, `orders`, `transactions`, `sellers`, `seller_withdrawals`, `seller_orders`, `seller_banks`, `seller_cc_items`, `seller_upload_batches`, `seller_upload_templates`, `seller_order_disputes`, `seller_chats`
- `marketers`, `marketer_withdrawals`, `marketer_stats`
- `workers`, `mirror_bots`, `bank_items`, `service_prices`
- `broadcasts`, `complaints`, `support_tickets`
- `categories`, `services`
- `cc_categories`, `cc_items`, `education_categories`, `education_items`
- и др.

### БД задач (SQLite, data/tasks.db)
- нефинансовые reminder/background tables

---

## 10. Lifespan (main.py)

1. `init_db()` — PostgreSQL
2. `init_tasks_db()` — SQLite tasks
3. Scheduler: `_check_scheduled_broadcasts` каждую минуту

---

## 11. Константы

- `web_panel/constants/categories.py` — `CATEGORIES_DATA`, `SERVICE_TO_CATEGORY_MAPPING` (хардкод для отчётов/маппинга)

---

## 12. Что можно менять вручную

- **Навигация:** `_nav.html` — группы, пункты, порядок
- **Роуты:** `main.py` — `@app.get(...)`, `templates.TemplateResponse`
- **API:** `web_panel/api/*.py` — эндпоинты
- **Конфиг:** `config.py`, `.env`
- **Роли:** `admins.py` — ROLES
