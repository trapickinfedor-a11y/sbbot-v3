# NewLookup Seller Hub — Полная архитектура Mini App v2

> Документ охватывает: систему пакетов/депозитов, модуль загрузки товаров, аналитику по периодам, управление помощниками, уведомления, мультиязычность. Включает промт для Cursor AI.

---

## Часть 1. Система пакетов и страховых депозитов

### 1.1 Концепция

Страховой депозит — это не оплата за доступ, а залог платформы, который гарантирует серьёзность намерений продавца и покрывает возможные диспуты. Депозит возвращается при корректном выходе из системы. Это принципиально отличает модель от подписки: продавец не "платит за фичи", а "замораживает залог под категорию".

Оптимальная структура — **3 пакета + апгрейд через доплату разницы**. Это даёт минимальный порог входа для новых продавцов, чёткую градацию по типам товаров и понятный путь роста.

### 1.2 Структура пакетов

| Пакет | `package_code` | Категории | Страховой депозит | Логика |
|-------|---------------|-----------|------------------|--------|
| **Starter** | `starter` | Banks, Brute Bank | $200 | Самые частые типы. Низкий порог входа. |
| **Extended** | `extended` | Banks, Brute, CC, Selfreg CC, NFC, OTP, Logs | $500 | Полный набор цифровых товаров. |
| **Full Access** | `full_access` | Все 12 типов + Enroll, Checks, Documents, Fullz | $1000 | Максимальный доступ. Для опытных продавцов. |

**Апгрейд:** продавец доплачивает только разницу. `upgrade_amount = target_package_deposit - current_deposit_paid`. Логика в `SellerDepositService.calculate_upgrade_amount(seller, target_package_code)`.

**Что видит продавец без нужного пакета:** кнопки категорий отображаются с иконкой замка 🔒 и суммой депозита. При нажатии — экран апгрейда с инструкцией по оплате. Скрывать категории полностью **не нужно** — это снижает конверсию в апгрейд.

### 1.3 Изменения в БД

```sql
-- Расширение поля package_code в seller_deposit_payments
-- Новые значения: 'starter', 'extended', 'full_access'
-- (вместо текущих 'bank', 'cc')

-- Новое поле в таблице sellers:
ALTER TABLE sellers ADD COLUMN deposit_package_code VARCHAR(32) DEFAULT NULL;
-- Значение обновляется при успешной оплате депозита
```

### 1.4 Изменения в SellerDepositService

```python
PACKAGES = {
    "starter": {
        "label": "Starter",
        "amount": Decimal("200.00"),
        "categories": ["bank", "brute"],
    },
    "extended": {
        "label": "Extended",
        "amount": Decimal("500.00"),
        "categories": ["bank", "brute", "cc", "selfreg_cc", "nfc", "otp", "logs"],
    },
    "full_access": {
        "label": "Full Access",
        "amount": Decimal("1000.00"),
        "categories": [
            "bank", "brute", "cc", "selfreg_cc", "nfc", "otp",
            "logs", "enroll", "checks", "documents", "fullz", "selfreg_ba"
        ],
    },
}

def calculate_upgrade_amount(seller: Seller, target_code: str) -> Decimal:
    current = PACKAGES.get(seller.deposit_package_code, {}).get("amount", Decimal("0"))
    target = PACKAGES[target_code]["amount"]
    return max(Decimal("0"), target - current)

def has_category_access(seller: Seller, category: str) -> bool:
    pkg = PACKAGES.get(seller.deposit_package_code)
    if not pkg:
        return False
    return category in pkg["categories"]
```

### 1.5 Где реализовать логику пакетов

**Только в seller_bot + backend.** Mini App получает информацию о пакете через `/api/seller-mini-app/me` (поле `deposit_package_code` и `allowed_categories: list[str]`). Сам Mini App не принимает платежи — он только показывает статус и перенаправляет в бот для апгрейда.

```
Продавец в Mini App видит замок на категории
  → нажимает "Upgrade"
  → Mini App вызывает Telegram.openTelegramLink("https://t.me/seller_bot?start=upgrade_extended")
  → seller_bot обрабатывает deep link, показывает инструкцию + BTCPay invoice
  → после оплаты webhook обновляет seller.deposit_package_code
  → Mini App при следующем открытии видит новый доступ
```

---

## Часть 2. Модуль загрузки товаров в Mini App

### 2.1 Принцип навигации

Вместо плоского списка форм — **двухуровневая навигация**: сначала выбор категории (с индикатором доступа), затем тип загрузки внутри категории. Это соответствует логике покупателя в mirror_bot и снижает когнитивную нагрузку.

```
Uploads Tab
│
├── [доступно] 🏦 Banks & Brute
│   ├── Add Bank Account      → форма (wizard step-by-step)
│   ├── Add Brute Single      → форма
│   ├── Add Brute Bulk        → загрузка файла + парсинг
│   └── My Batches            → список с статусами модерации
│
├── [доступно] 💳 CC & Digital
│   ├── Add CC Single         → форма
│   ├── Add CC Bulk           → вставка строк / файл
│   ├── Add NFC               → форма + ZIP файл
│   ├── Add OTP               → форма
│   └── Add Selfreg CC        → форма
│
├── [🔒 Full Access] 📋 Specials
│   ├── Add Logs              → Universal Upload
│   ├── Add Checks            → форма + фото
│   ├── Add Enroll            → форма (выбор портала)
│   ├── Add Documents         → форма + sample
│   └── Add Fullz             → форма + файл данных
│
├── 📦 My Listings            → список + bulk reprice + toggle
└── 📐 Templates              → сохранённые шаблоны форм
```

### 2.2 UX форм загрузки

Каждая форма реализована как **многошаговый wizard** (не одна длинная страница). Шаги:

1. **Тип и категория** — выбор из доступных опций
2. **Основные данные** — название, банк, ключевые поля
3. **Финансовые параметры** — цена, баланс/диапазон
4. **Дополнительные поля** — специфичные для типа товара
5. **Превью и подтверждение** — карточка как её увидит покупатель

Прогресс-бар вверху показывает текущий шаг. Кнопка "Назад" на каждом шаге. Данные сохраняются в `localStorage` при переходе между шагами — не теряются при случайном закрытии.

### 2.3 Bulk загрузка

Для CC и Brute поддерживается два режима:
- **Paste mode**: вставить строки в textarea (формат `NUMBER|EXP|CVV|...`)
- **File mode**: загрузить `.txt` / `.csv` файл

После вставки/загрузки — предпросмотр первых 5 строк с парсингом. Кнопка "Confirm & Submit" отправляет на `/uploads/submit`.

### 2.4 Статусы модерации в Batches

| Статус | Цвет | Описание |
|--------|------|----------|
| `pending_moderation` | Amber | Ожидает проверки модератором |
| `approved` | Green | Одобрено, видно покупателям |
| `rejected` | Red | Отклонено. Показывается причина |
| `changes_requested` | Orange | Нужны правки. Кнопка "Edit & Resubmit" |

---

## Часть 3. Аналитика по периодам

### 3.1 Источники данных

Вся аналитика строится из транзакционных таблиц по полю `created_at` / `completed_at`. Отдельного data warehouse нет — агрегация происходит на уровне SQL при запросе.

```python
# Пример запроса для аналитики продавца по месяцам
SELECT
    DATE_TRUNC('month', o.created_at) AS period,
    COUNT(*)                          AS orders_count,
    SUM(o.seller_amount)              AS revenue,
    COUNT(CASE WHEN o.status = 'completed' THEN 1 END) AS completed,
    COUNT(CASE WHEN o.status = 'disputed'  THEN 1 END) AS disputes
FROM seller_orders o          -- объединение всех *_orders таблиц через UNION
WHERE o.seller_id = :seller_id
  AND o.created_at >= :date_from
  AND o.created_at <  :date_to
GROUP BY DATE_TRUNC('month', o.created_at)
ORDER BY period DESC;
```

### 3.2 Новый API эндпоинт для Mini App

```
GET /api/seller-mini-app/analytics/timeseries
  ?period=month          # day | week | month
  &date_from=2026-01-01  # ISO date
  &date_to=2026-03-31
  &metric=revenue        # revenue | orders | disputes | completion_rate
```

Ответ:
```json
{
  "period": "month",
  "date_from": "2026-01-01",
  "date_to": "2026-03-31",
  "series": [
    { "label": "January 2026",  "orders": 42, "revenue": 1840.50, "disputes": 2, "completion_rate": 95 },
    { "label": "February 2026", "orders": 58, "revenue": 2310.00, "disputes": 1, "completion_rate": 98 },
    { "label": "March 2026",    "orders": 71, "revenue": 3120.75, "disputes": 3, "completion_rate": 96 }
  ],
  "totals": { "orders": 171, "revenue": 7271.25, "disputes": 6 }
}
```

### 3.3 UI аналитики в Mini App

**Навигация по периодам:**
```
[← Prev]  [April 2026]  [Next →]   [Download CSV ↓]
          [7D] [30D] [3M] [6M] [Year]
```

Переключение между месяцами — стрелки влево/вправо. Быстрые пресеты: 7D, 30D, 3M, 6M, Year. Кнопка "Download CSV" вызывает `/analytics/export.csv?period=month&date_from=...&date_to=...`.

**Метрики на экране аналитики:**

| Метрика | Источник | Описание |
|---------|---------|----------|
| Revenue | `SUM(seller_amount)` по завершённым заказам | Выручка за период |
| Orders | `COUNT(*)` всех заказов | Количество заказов |
| Completed | `COUNT WHERE status='completed'` | Завершённые |
| Disputes | `COUNT WHERE status='disputed'` | Диспуты |
| Completion Rate | `completed / orders * 100` | % успешных |
| Avg Order Value | `revenue / completed` | Средний чек |
| Top Products | `GROUP BY product_type ORDER BY revenue DESC LIMIT 5` | Топ по выручке |
| Abandoned Carts | Из `buyer_cart_events` или `order_attempts` | Брошенные корзины |

**Воронка конверсии** (Views → Cart → Checkout → Paid) — только если платформа логирует события просмотра листингов. Если нет — убрать воронку из Mini App и показывать только заказы.

---

## Часть 4. Управление помощниками

### 4.1 Где реализовать

**В обоих местах, но с разными функциями:**

| Функция | seller_bot | Mini App |
|---------|-----------|----------|
| Пригласить помощника | ✅ (генерация invite link) | ✅ (кнопка → deep link в бот) |
| Просмотр списка | ✅ | ✅ |
| Смена роли | ✅ | ✅ |
| Удаление / бан | ✅ | ✅ |
| Аудит действий помощника | ✅ (полный лог) | ⬜ (только сводка) |

Mini App показывает список помощников с ролями и статусами. Для приглашения нового — кнопка открывает seller_bot через deep link `t.me/seller_bot?start=invite_helper`. Смена роли и удаление — через API прямо из Mini App.

### 4.2 Новые API эндпоинты

```
GET    /api/seller-mini-app/helpers              — список помощников
POST   /api/seller-mini-app/helpers/invite       — создать invite token
PATCH  /api/seller-mini-app/helpers/{id}/role    — сменить роль
DELETE /api/seller-mini-app/helpers/{id}         — удалить помощника
GET    /api/seller-mini-app/helpers/{id}/audit   — лог действий (последние 50)
```

### 4.3 Роли и права

| Роль | `upload_helper` | `support_helper` | `manager_helper` |
|------|----------------|-----------------|-----------------|
| Загрузка товаров | ✅ | ❌ | ✅ |
| Чаты с покупателями | ❌ | ✅ | ✅ |
| Просмотр заказов | ❌ | ✅ | ✅ |
| Просмотр финансов | ❌ | ❌ | ✅ (только просмотр) |
| Вывод средств | ❌ | ❌ | ❌ (только owner) |
| Управление листингами | ❌ | ❌ | ✅ |

### 4.4 Аудит для владельца

Каждое действие помощника логируется в таблицу `seller_helper_audit`:
```sql
CREATE TABLE seller_helper_audit (
    id          SERIAL PRIMARY KEY,
    seller_id   INTEGER REFERENCES sellers(id),
    actor_id    INTEGER REFERENCES seller_actors(id),
    action      VARCHAR(64),   -- 'upload_submitted', 'message_sent', 'listing_toggled'
    entity_type VARCHAR(32),
    entity_id   INTEGER,
    meta        JSONB,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Часть 5. Уведомления

### 5.1 Архитектура

Telegram WebApp не поддерживает нативные push-уведомления когда приложение закрыто. Поэтому **все системные уведомления идут через seller_bot** (сообщения в чат). Mini App показывает уведомления только пока открыт — через polling или WebSocket.

```
Событие в системе (новый заказ, сообщение, диспут)
  │
  ├── seller_bot → отправляет сообщение продавцу в Telegram (всегда)
  │
  └── Mini App (если открыт) → показывает toast + обновляет badge
```

### 5.2 Типы уведомлений

| Событие | Telegram Bot | Mini App Badge | Toast |
|---------|-------------|---------------|-------|
| Новое сообщение от покупателя | ✅ | ✅ (Chats) | ✅ |
| Новый заказ | ✅ | ✅ (Orders) | ✅ |
| Заказ завершён | ✅ | — | ✅ |
| Диспут открыт | ✅ | ✅ (Orders, красный) | ✅ |
| Диспут решён | ✅ | — | ✅ |
| Товар одобрен модератором | ✅ | ✅ (Uploads) | ✅ |
| Товар отклонён | ✅ | ✅ (Uploads, красный) | ✅ |
| Запрос на изменения | ✅ | ✅ (Uploads, оранжевый) | ✅ |
| Вывод средств обработан | ✅ | — | ✅ |
| Депозит подтверждён | ✅ | — | ✅ |

### 5.3 Новый API эндпоинт

```
GET /api/seller-mini-app/notifications
  ?unread_only=true
  &limit=20

POST /api/seller-mini-app/notifications/read-all

Response:
{
  "items": [
    { "id": 1, "type": "new_message", "title": "New message from buyer",
      "body": "Chase Business — Is this still available?",
      "entity_type": "conversation", "entity_id": 42,
      "is_read": false, "created_at": "2026-03-23T10:00:00Z" }
  ],
  "unread_count": 3
}
```

---

## Часть 6. Мультиязычность

### 6.1 Стратегия

Mini App использует **i18n на фронтенде** (библиотека `i18next` или самописный контекст). Язык определяется из `Telegram.WebApp.initDataUnsafe.user.language_code` при инициализации. Если язык не поддерживается — fallback на EN.

Поддерживаемые языки: **EN, RU, ZH, ES** — те же, что в seller_bot.

### 6.2 Структура переводов

```
client/src/i18n/
├── en.json    # English (default)
├── ru.json    # Русский
├── zh.json    # 中文
└── es.json    # Español
```

Каждый файл содержит плоский объект с ключами:
```json
{
  "nav.chats": "Chats",
  "nav.orders": "Orders",
  "upload.step1.title": "Select product type",
  "deposit.starter.description": "Access to Banks and Brute Bank products",
  "instructions.title": "How to get started"
}
```

### 6.3 Инструкция для новых продавцов (Onboarding)

При первом открытии Mini App (поле `seller.onboarding_completed = false`) показывается **онбординг-экран** на языке пользователя:

```
Шаг 1: Добро пожаловать в Seller Hub
  → Краткое описание платформы, правила, ссылка на полные правила

Шаг 2: Выберите пакет доступа
  → Карточки трёх пакетов (Starter / Extended / Full Access)
  → Кнопка "Choose" → переход в seller_bot для оплаты депозита

Шаг 3: После оплаты
  → Инструкция по загрузке первого товара
  → Видео-гайд или GIF (опционально)
  → Кнопка "Start uploading"
```

---

## Часть 7. Полная карта вкладок Mini App v2

| Вкладка | Иконка | Доступ | Ключевые функции |
|---------|--------|--------|-----------------|
| **Chats** | 💬 | Все (кроме upload_helper) | Список чатов, inline chat, поиск, файлы |
| **Orders** | 📦 | Все | Фильтры, детали заказа, диспуты |
| **Uploads** | ⬆️ | can_upload | Категории → wizard-формы, batches, listings, templates |
| **Analytics** | 📊 | Owner + manager | Месяц/день/период, KPI, топ товары, CSV export |
| **Finance** | 💰 | Owner | Баланс, вывод, история транзакций, CSV |
| **Team** | 👥 | Owner | Список помощников, роли, аудит, приглашение |
| **Settings** | ⚙️ | Все | Vacation, auto-payout, quiet hours, язык, онбординг, пакет |

Итого **7 вкладок** (добавляется Team вместо объединения с Settings).

---

## Часть 8. Промт для Cursor AI

Ниже — готовый промт для работы с кодовой базой в Cursor. Скопируй его в `.cursorrules` или используй как системный промт в Cursor Chat.

---

```
You are a senior full-stack engineer working on the NewLookup Seller Hub system.
The codebase consists of:
  - seller_bot/ — aiogram 3.x Telegram bot for sellers
  - mirror_bot/ — aiogram 3.x Telegram bot for buyers
  - support_bot/ — moderation and admin bot
  - web_panel/ — FastAPI admin panel
  - shared/ — SQLAlchemy models, services, database
  - seller_mini_app_v2/ — React 19 + TypeScript + Tailwind 4 Telegram Mini App

## Architecture Rules

### Deposit & Access System
- Sellers must pay a security deposit to unlock product upload categories
- Three packages: starter ($200, banks+brute), extended ($500, +cc/nfc/otp/logs), full_access ($1000, all types)
- Access check: always use `SellerDepositService.has_category_access(seller, category)` — never hardcode category lists
- Upgrades: seller pays only the difference via `calculate_upgrade_amount(seller, target_package_code)`
- Payment flow: BTCPay invoice → webhook → `sync_invoice_status()` → update `seller.deposit_package_code`
- Mini App NEVER processes payments — it redirects to seller_bot via Telegram deep link

### Upload Module
- Every product type has its own FSM in seller_bot/handlers/
- Mini App uploads go through `/api/seller-mini-app/uploads/submit` with `item_type` field
- Supported item_types in Mini App: bank, brute_single, brute_bulk, cc_single, cc_bulk, nfc, otp, selfreg_cc
- Full Access types (logs, checks, enroll, documents, fullz) — seller_bot only, not in Mini App
- After submit: moderation_status = "pending_moderation", seller sees it in Batches tab
- Bulk brute/cc: parse file server-side via `/uploads/parse-file`, preview first 5 rows, then `/uploads/submit`

### Analytics
- All analytics are computed from transactional tables (seller_orders, seller_*_orders) by created_at
- No separate analytics tables — aggregate with SQL DATE_TRUNC('month'/'day', created_at)
- New endpoint needed: GET /api/seller-mini-app/analytics/timeseries?period=month&date_from=&date_to=
- Seller sees only their own data (filter by seller_id from auth)
- CSV export: GET /api/seller-mini-app/analytics/export.csv with same params

### Authentication
- Production: X-Telegram-Init-Data header → verify HMAC-SHA256 with BOT_TOKEN
- Development: X-Dev-Seller-Telegram-Id header (only when DEBUG=True)
- Auth dependency: `get_seller_from_telegram(request, db)` → returns Seller ORM object
- Role check: use seller_actor.can_upload(), can_manage_finance(), can_chat() methods

### Helpers (Team)
- Roles: upload_helper (upload only), support_helper (chat+orders), manager_helper (all except finance/withdraw)
- Owner invites via deep link: t.me/seller_bot?start=invite_helper_{token}
- All helper actions are logged to seller_helper_audit table
- Mini App shows helper list + role management + audit summary

### Notifications
- System notifications always go through seller_bot (Telegram messages)
- Mini App polls GET /api/seller-mini-app/notifications?unread_only=true every 30 seconds
- Notification types: new_message, new_order, order_completed, dispute_opened, dispute_resolved,
  item_approved, item_rejected, changes_requested, withdrawal_processed, deposit_confirmed
- Badge counts update on each poll cycle

### i18n
- Detect language from Telegram.WebApp.initDataUnsafe.user.language_code
- Supported: en, ru, zh, es — fallback to en
- Translation files in client/src/i18n/{lang}.json
- Use useTranslation() hook everywhere — no hardcoded UI strings

### Database Conventions
- All models in shared/database/models.py
- Use SQLAlchemy 2.x async sessions
- Seller-scoped queries always filter by seller_id — never return cross-seller data
- Timestamps: always use TIMESTAMPTZ, store in UTC

### API Conventions
- Base path: /api/seller-mini-app/
- All endpoints require seller auth (use Depends(get_seller_from_telegram))
- Error responses: {"detail": "human readable message"} with appropriate HTTP status
- Pagination: ?page=1&per_page=20, response includes total_count
- Date params: ISO 8601 format (YYYY-MM-DD)

### Code Style
- Python: async/await everywhere, type hints on all functions, Pydantic v2 models for request/response
- TypeScript: strict mode, no any, use Zod for runtime validation of API responses
- React: functional components only, custom hooks for data fetching, no class components
- CSS: Tailwind utilities only, custom classes only for complex glass effects in index.css

## Current File Structure (key files)
shared/
  database/models.py          — all ORM models
  services/
    seller_deposit_service.py — deposit packages, access checks, upgrade logic
    btcpay_service.py         — BTCPay invoice creation and webhook handling

seller_bot/
  handlers/
    start.py                  — registration, deposit flow, deep links
    stock.py                  — bank/enroll upload FSM
    brute_bank.py             — brute bank upload FSM
    cc_stock.py               — CC upload FSM
    special_products.py       — NFC, OTP, Enroll, Selfreg CC FSM
    helpers.py                — helper roles, invite system
  services/
    seller_deposit_service.py — same as shared, imported

web_panel/
  api/
    seller_mini_app.py        — all Mini App API endpoints
    seller_deposits.py        — deposit payment management
    analytics_advanced.py     — timeseries analytics (adapt for seller scope)

seller_mini_app_v2/
  client/src/
    lib/api.ts                — typed API client
    lib/telegram.ts           — Telegram WebApp SDK wrapper
    contexts/AppContext.tsx   — global state
    components/tabs/          — tab components (ChatsTab, OrdersTab, etc.)

## When implementing new features:
1. Start with the shared/ model changes (add columns, new tables)
2. Add/update the service method in shared/services/
3. Add the API endpoint in web_panel/api/seller_mini_app.py
4. Update the TypeScript interface in seller_mini_app_v2/client/src/lib/api.ts
5. Implement the UI component in the appropriate tab
6. Update AppContext if new global state is needed
7. Add translations to all 4 i18n files
```

---

## Часть 9. Приоритизация реализации

Ниже — рекомендуемый порядок разработки от наиболее критичного к дополнительному.

| Приоритет | Задача | Затрагивает |
|-----------|--------|-------------|
| 🔴 P0 | Система 3 пакетов + апгрейд | shared/services, seller_bot, Mini App Settings |
| 🔴 P0 | Wizard-формы загрузки (Bank, Brute, CC) | Mini App Uploads, API |
| 🔴 P0 | Аналитика по месяцам + CSV export | API timeseries, Mini App Analytics |
| 🟠 P1 | Управление помощниками (Team tab) | shared/models, API, Mini App |
| 🟠 P1 | Уведомления (polling + badges) | API notifications, Mini App |
| 🟠 P1 | Онбординг-экран для новых продавцов | Mini App |
| 🟡 P2 | i18n (RU, ZH, ES переводы) | Mini App |
| 🟡 P2 | NFC, OTP, Selfreg CC формы | Mini App Uploads |
| 🟢 P3 | Аудит действий помощников | shared/models, API, Mini App Team |
| 🟢 P3 | Market comparison в Listings | API, Mini App |
