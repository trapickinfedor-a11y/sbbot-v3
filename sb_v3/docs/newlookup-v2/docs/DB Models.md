# DB Models — shared/database/models.py

[[MOC]] > DB Models

## Обзор файла

### shared/database/models.py
**Строк:** 2804

**Классы (20 в основном файле):**
- `Base(DeclarativeBase)`
- `MirrorBot(Base)`
- `BotOwnerStats(Base)`
- `BotOwner(Base)`
- `BotOwnerWithdrawal(Base)`
- `User(Base)`
- `Order(Base)`
- `BulkOrderItem(Base)`
- `WorkerOrder(Base)`
- `Worker(Base)`
- `WorkerStats(Base)`
- `WorkerWithdrawal(Base)`
- `WorkerExpenseReport(Base)`
- `Transaction(Base)`
- `Product(Base)`
- `ProductCatalogService(Base)`
- `MirrorMenuCategory(Base)`
- `ProductPurchase(Base)`
- `ProductRating(Base)`
- `ProductActionLog(Base)`

**TODO/заглушки:** 1 (`pass`)

---

## Основные модели (models.py)

### `Base(DeclarativeBase)`
Базовый класс SQLAlchemy для всех ORM-моделей.

---

### `MirrorBot(Base)`
Зеркальный пользовательский Telegram-бот.

**Поля:**
- `id` — PK
- `user_id` — Telegram ID владельца
- `bot_token` — токен бота
- `bot_username` — @username
- `is_active` — активен ли бот
- `language` — язык интерфейса
- `welcome_message` — приветственный текст
- `video_file_id` — Telegram file_id видео
- `archive_channel_id` — ID архивного канала
- `created_at`

---

### `BotOwnerStats(Base)`
Месячная статистика владельца бота.

**Поля:** `id`, `owner_user_id`, `month` (YYYY-MM), `total_spent`, `topups_count`

---

### `BotOwner(Base)`
Владелец бота (реферальная программа).

**Поля:** `id`, `user_id`, `username`, `balance`, `pending_balance`, `total_earned`, `created_at`

---

### `BotOwnerWithdrawal(Base)`
Заявка на вывод средств владельца бота.

**Поля:** `id`, `owner_user_id`, `amount`, `method`, `network`, `requisites`, `status` (pending/approved/rejected), `created_at`

---

### `User(Base)`
Покупатель / пользователь бота.

**Поля:**
- `id`, `telegram_id`, `username`, `first_name`, `last_name`
- `balance` — текущий баланс
- `is_banned`, `ban_reason`
- `referral_code`, `referrer_id`
- `language`
- `created_at`
- `coupon_id` — активный купон
- `trust_score` — рейтинг доверия покупателя

---

### `Order(Base)`
Заказ в системе поддержки/воркеров.

**Поля:**
- `id`, `user_id` (покупатель), `bot_id` (бот заказа)
- `service_name`, `category`, `state`
- `customer_data` — JSON с данными клиента
- `status` — pending / processing / completed / cancelled / nf
- `worker_id`
- `price`, `worker_payment`
- `is_bulk` — bulk-заказ
- `addinfo_waiting_hours`
- `worker_message_id`, `channel_message_id`
- `created_at`, `completed_at`

---

### `BulkOrderItem(Base)`
Элемент массового заказа.

**Поля:** `id`, `order_id`, `item_number`, `customer_data` (JSON), `status`, `result_text`, `worker_id`, `completed_at`

---

### `WorkerOrder(Base)`
Запись о том, что воркер взял заказ.

**Поля:** `id`, `order_id`, `worker_id`, `taken_at`, `completed_at`, `status`

---

### `Worker(Base)`
Воркер (исполнитель заказов).

**Поля:**
- `id`, `telegram_id`, `username`
- `is_active`
- `categories` — JSON-список разрешённых категорий
- `services` — JSON-список разрешённых сервисов
- `balance`, `pending_balance`, `total_earned`
- `violation_count`
- `score` — рейтинг
- `created_at`

---

### `WorkerStats(Base)`
Дневная статистика воркера.

**Поля:** `id`, `worker_id`, `date`, `completed_count`, `nf_count`, `cancelled_count`, `total_earned`

---

### `WorkerWithdrawal(Base)`
Заявка на вывод воркера.

**Поля:** `id`, `worker_id`, `amount`, `requisites`, `status`, `created_at`

---

### `WorkerExpenseReport(Base)`
Отчёт о расходах воркера.

**Поля:** `id`, `worker_id`, `amount`, `category`, `description`, `receipt_file_id`, `status`, `created_at`

---

### `Transaction(Base)`
Финансовая транзакция (double-entry ledger).

**Поля:**
- `id`
- `account_type` — user / seller / worker / marketer / owner
- `account_id`
- `transaction_type` — credit / debit / hold / settle / dispute / etc.
- `amount`
- `status` — TRANSACTION_STATUS_ON_HOLD / completed / failed / disputed
- `idempotency_key`
- `order_id`
- `metadata` (JSON)
- `created_at`

---

### `Product(Base)`
Файловый товар каталога.

**Поля:**
- `id`, `category`, `service`, `state`, `name`, `description`
- `file_id` (Telegram), `file_path`
- `price`
- `is_active`
- `uploader_id` — воркер
- `purchase_count`
- `moderation_status` — pending / approved / rejected
- `created_at`

---

### `ProductCatalogService(Base)`
Сервис каталога (ESim, VPN, Education, etc.).

**Поля:** `id`, `code`, `label`, `category`, `is_active`, `sort_order`

---

### `MirrorMenuCategory(Base)`
Категория главного меню бота.

**Поля:**
- `id`, `key`
- `label_en`, `label_ru`, `label_zh`, `label_es`
- `emoji`
- `is_active`, `sort_order`
- `route_type`

---

### `ProductPurchase(Base)`
Факт покупки продукта.

**Поля:** `id`, `user_id`, `product_id`, `order_id`, `price_paid`, `created_at`

---

### `ProductRating(Base)`
Оценка продукта покупателем.

**Поля:** `id`, `product_id`, `user_id`, `rating` (1–5), `comment`, `created_at`

---

### `ProductActionLog(Base)`
Аудит-лог действий с продуктом.

**Поля:** `id`, `product_id`, `action`, `actor_id`, `actor_type`, `details` (JSON), `created_at`

---

## Модели Seller-системы (из session.py — 2300 строк)

Создаются через миграции в `shared/database/session.py`.

### `Seller(Base)`
**Поля:** `id`, `telegram_id`, `username`, `is_approved`, `is_banned`, `ban_reason`, `deposit_package`, `balance`, `pending_balance`, `total_earned`, `language`, `is_on_vacation`, `auto_payout_enabled`, `quiet_hours_start`, `quiet_hours_end`, `reputation_score`, `categories_access` (JSON)

### `SellerBank(Base)`
**Поля:** `id`, `seller_id`, `product_type`, `product_subtype`, `category`, `bank_type`, `bank_name`, `bank_code`, `price`, `base_price`, `markup_code`, `stock_count`, `sold_count`, `reserved_count`, `is_in_stock`, `is_published`, `moderation_status`, `support_mode`, `has_number_access`, `number_change_allowed`, `auto_unpublish`, `listing_duration_days`, `description`, `instruction`, `state`, `zip`, `country`

### `SellerCCItem(Base)`
**Поля:** `id`, `seller_id`, `category`, `cc_type`, `name`, `price`, `base_price`, `is_non_vbv`, `extra_data` (JSON), `moderation_status`, `is_in_stock`

### `SellerOrder(Base)`
**Поля:** `id`, `seller_id`, `bank_id`, `buyer_user_id`, `buyer_bot_id`, `status`, `price`, `seller_net`, `dispute_status`, `data_revealed`, `created_at`, `completed_at`, `guarantee_until`, `rating`, `rating_comment`

### `SellerOrderDispute(Base)`
**Поля:** `id`, `order_id`, `seller_id`, `reason`, `status`, `opened_at`, `resolved_at`, `resolution` (buyer/seller), `seller_response_text`, `admin_notes`, `appeal_requested`, `appeal_reason`, `appeal_reviewed_at`

### `SellerChat(Base)`
**Поля:** `id`, `conversation_id`, `sender_type` (seller/buyer), `text`, `file_id`, `file_type`, `created_at`, `is_read`

### `SellerConversation(Base)`
**Поля:** `id`, `seller_id`, `order_id`, `buyer_user_id`, `buyer_bot_id`, `status`, `unread_seller`, `unread_buyer`, `created_at`, `updated_at`

### `SellerWithdrawal(Base)`
**Поля:** `id`, `seller_id`, `amount`, `requisites`, `status`, `created_at`

### `SellerDepositPayment(Base)`
**Поля:** `id`, `seller_id`, `package_code`, `amount`, `btcpay_invoice_id`, `status`, `created_at`

### `SellerHelper(Base)`
**Поля:** `id`, `seller_id`, `telegram_id`, `username`, `roles` (JSON: upload/support/finance), `status` (pending/active/blocked), `created_at`

### `SellerHelperAuditLog(Base)`
**Поля:** `id`, `seller_id`, `helper_id`, `action`, `details` (JSON), `created_at`

### `SellerUploadBatch(Base)`
**Поля:** `id`, `seller_id`, `product_type`, `bank_code`, `total_count`, `approved_count`, `rejected_count`, `pending_count`, `status`, `created_at`

### `SellerUploadTemplate(Base)`
**Поля:** `id`, `seller_id`, `name`, `product_type`, `template_data` (JSON), `created_at`

---

## Спец. инвентарь продавца

| Модель | Описание |
|---|---|
| `SellerNFCItem(Base)` | NFC-карты (физические): bank_name, country, state, zip, nfc_type, price, file_id |
| `SellerOTPItem(Base)` | OTP-доступы: bank_name, balance, has_fullz, sms_access, price |
| `SellerEnrollItem(Base)` | Enrollment-архивы: category, bank_name, balance, zip, price, file |
| `SellerSelfregCCItem(Base)` | Самореги CC: category, name, price, extra_data (JSON) |
| `SellerCheckItem(Base)` | Чеки: check_type, amount, price |
| `SellerDocumentItem(Base)` | Документы: doc_type, state, quality, has_hologram, has_selfie, description, price, sample_file_id |
| `SellerFullzItem(Base)` | Fullz: fullz_type, state, credit_score, age_range, gender, company_type, loan_size, report_group, quantity, price, data_file_id |
| `SellerLogsItem(Base)` | Логи: price, extra_data |
| `BruteBankGroup(Base)` | Группа брутов: bank_code, bank_name, attributes, category |
| `BruteBankItem(Base)` | Брут: group_id, seller_id, credentials, balance, price, status (pending/approved/rejected), is_single_account |

---

## Каталоги

| Модель | Поля |
|---|---|
| `AccountCategory(Base)` | id, code, name, description, is_active, sort_order |
| `AccountItem(Base)` | id, category_id, name, description, price, is_active, sort_order |
| `AccountInventory(Base)` | id, item_id, credentials, is_sold, sold_at, buyer_id |
| `ServicePrice(Base)` | id, service_name, category, price, is_active |
| `BankItem(Base)` | id, bank_code, bank_name, bank_type, category, is_active |
| `BankPosition(Base)` | id, bank_code, position |
| `CCCategory(Base)` | id, code, name, is_active, sort_order |
| `CCItem(Base)` | id, category_id, code, name, is_active, sort_order |
| `EducationCategory(Base)` | id, name, description, is_active, sort_order |
| `EducationSubscription(Base)` | id, category_id, name, duration_days, price, is_active |
| `EducationManual(Base)` | id, category_id, title, content, file_id, is_active |
| `AnotherServiceButton(Base)` | id, label, url, is_active, sort_order |

---

## Финансовые модели

| Модель | Поля |
|---|---|
| `PricingConfig(Base)` | id, key, value, description |
| `BulkDiscountTier(Base)` | id, category, min_quantity, discount_percent |
| `Coupon(Base)` | id, code, discount_type, discount_value, min_order, max_uses, used_count, is_active, expires_at |
| `CouponRedemption(Base)` | id, coupon_id, user_id, order_id, amount_saved, created_at |
| `UserCoupon(Base)` | id, user_id, coupon_id, assigned_at |
| `EscrowRelease(Base)` | id, order_id, released_at, amount |
| `ShoppingCart(Base)` | id, user_id, items (JSON), created_at, updated_at |

---

## Маркетинг

| Модель | Поля |
|---|---|
| `Marketer(Base)` | id, telegram_id, username, balance, pending_balance, total_earned, referral_code, is_active |
| `MarketerStats(Base)` | id, marketer_id, date, registrations_count, revenue |
| `MarketerWithdrawal(Base)` | id, marketer_id, amount, requisites, status, created_at |
| `MarketerActivityLog(Base)` | id, marketer_id, action, details (JSON), created_at |
| `MarketerBotLink(Base)` | id, marketer_id, bot_id |
| `MarketerOwnBot(Base)` | id, marketer_id, bot_id, is_active |

---

## Администрирование

| Модель | Поля |
|---|---|
| `Admin(Base)` | id, username, password_hash, role, allowed_catalogs, is_active, created_at |
| `AdminRole(Base)` | id, name, permissions (JSON) |
| `AdminAuditLog(Base)` | id, admin_id, action, entity_type, entity_id, details (JSON), created_at |
| `AuditLog(Base)` | id, actor_type, actor_id, action, entity_type, entity_id, details (JSON), created_at |
| `UploaderCatalogPermission(Base)` | id, admin_id, catalog_code |

---

## Поддержка / тикеты

| Модель | Поля |
|---|---|
| `SupportTicket(Base)` | id, user_id, category, status, priority, subject, created_at, closed_at, csat_rating |
| `SupportTicketMessage(Base)` | id, ticket_id, sender_type, text, file_id, created_at, is_read |
| `SupportMessage(Base)` | id, ticket_id, file_path, created_at |
| `KnowledgeBaseArticle(Base)` | id, category, title, content, is_active, created_at |
| `Complaint(Base)` | id, user_id, worker_id, order_id, reason, description, status, created_at |

---

## Уведомления и рассылки

| Модель | Поля |
|---|---|
| `NotificationLog(Base)` | id, event_type, recipient_id, status, error_text, created_at |
| `Broadcast(Base)` | id, title, audience, status, scheduled_at, sent_count, created_at |
| `BroadcastTranslation(Base)` | id, broadcast_id, language, text, media_file_id, buttons (JSON) |

---

## Воркеры (доп.)

| Модель | Поля |
|---|---|
| `WorkerViolation(Base)` | id, worker_id, violation_type, details, created_at |

---

## Автоматизация

| Модель | Поля |
|---|---|
| `AutomationConfig(Base)` | id, is_enabled, daily_limit, provider |
| `AutomationProxy(Base)` | id, address, port, username, password, is_active |
| `AutomationApiKey(Base)` | id, provider, key_value, is_active, balance |
| `AutomationJob(Base)` | id, status, created_at, completed_at, result (JSON) |
| `AutomationFinanceEntry(Base)` | id, date, amount, type, description |

---

## Система настроек

| Модель | Поля |
|---|---|
| `SystemSetting(Base)` | id, key, value, description |
| `UiTranslation(Base)` | id, key, language, value |

---

## Task Models (shared/database/task_models.py)
**Строк:** 35
Отдельная SQLite БД для отложенных задач.

**Классы:**
- `TaskBase(DeclarativeBase)`
- `WorkerReminderTask(TaskBase)` — отложенное напоминание воркеру

**Поля WorkerReminderTask:** `id`, `order_id`, `worker_id`, `remind_at`, `is_done`, `created_at`

**TODO/заглушки:** 1

---

## Cross-imports (models.py используется в)

- `from shared.database.models import ...` — во ВСЕХ модулях
- [[Seller Bot]] — через все handler'ы и сервисы
- [[Support Bot]] — через все handler'ы и сервисы
- [[Web Panel]] — через web_panel.database → shared
- [[Shared Services]] — session.py создаёт таблицы

---

## Связи моделей

```
User ──────────────── Order (buyer_id)
                       │
              ─────────┴─────────
              │                 │
         WorkerOrder         BulkOrderItem
              │
           Worker ── WorkerStats / WorkerWithdrawal

User ─── SellerOrder ─ SellerBank ─── Seller
                 │
         SellerOrderDispute
         SellerConversation ─ SellerChat

MirrorBot ── User (bot_id)
MirrorBot ── BotOwner (owner_user_id)
MirrorBot ── Marketer (via MarketerBotLink)

Transaction ─── [User | Seller | Worker | Marketer | BotOwner]

SupportTicket ─── SupportTicketMessage
Broadcast ─── BroadcastTranslation
Coupon ─── CouponRedemption ── UserCoupon
```
