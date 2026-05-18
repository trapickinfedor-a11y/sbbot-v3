# NewLookup — Все таблицы и зоны ответственности

> Автогенерировано из `shared/database/models.py` и архитектурного обзора проекта.

---

## Оглавление

1. [Архитектура и роли](#1-архитектура-и-роли)
2. [Карта сервисов](#2-карта-сервисов)
3. [Все таблицы основной БД](#3-все-таблицы-основной-бд)
   - [Ядро: боты и пользователи](#31-ядро-боты-и-пользователи)
   - [Заказы и выполнение](#32-заказы-и-выполнение)
   - [Воркеры](#33-воркеры)
   - [Финансы и транзакции](#34-финансы-и-транзакции)
   - [Товары и каталог](#35-товары-и-каталог)
   - [Seller-система](#36-seller-система)
   - [Seller-товары по типам](#37-seller-товары-по-типам)
   - [Маркетологи и рефералы](#38-маркетологи-и-рефералы)
   - [Поддержка и жалобы](#39-поддержка-и-жалобы)
   - [Рассылки и переводы](#310-рассылки-и-переводы)
   - [Купоны и скидки](#311-купоны-и-скидки)
   - [Корзина и вишлист](#312-корзина-и-вишлист)
   - [Education](#313-education)
   - [Аккаунты и подписки](#314-аккаунты-и-подписки)
   - [CC (кредитные карты)](#315-cc-кредитные-карты)
   - [Brute Bank](#316-brute-bank)
   - [Автоматизация](#317-автоматизация)
   - [Администрирование](#318-администрирование)
   - [Системные и служебные](#319-системные-и-служебные)
4. [Таблицы Lookup API (отдельная SQLite)](#4-таблицы-lookup-api-отдельная-sqlite)
5. [Матрица ответственности: сервис → таблицы](#5-матрица-ответственности-сервис--таблицы)
6. [Потоки данных](#6-потоки-данных)

---

## 1. Архитектура и роли

Система обслуживает 6 типов акторов через единую общую БД:

| Роль | Интерфейс | Описание |
|------|-----------|----------|
| **Buyer** (покупатель) | `mirror_bot` | Оформляет заказы, покупает товары, пополняет баланс |
| **Worker** (воркер) | `worker_bot` / `support_bot` | Выполняет lookup-заказы, получает оплату |
| **Seller** (продавец) | `seller_bot` | Загружает товары, управляет складом, выводит средства |
| **Bot Owner** (владелец бота) | `main_bot` | Управляет mirror-ботами, получает 7% с пополнений |
| **Marketer** (маркетолог) | `marketer_bot` | Привлекает трафик по промокодам, получает комиссию |
| **Admin** (администратор) | `web_panel` / `support_bot` | Управляет всей системой, модерирует, настраивает |

---

## 2. Карта сервисов

| Сервис | Стек | Порт | Назначение |
|--------|------|------|------------|
| **main_bot** | aiogram + FastAPI | — | Главный бот; управление mirror-ботами; API уведомлений покупателям |
| **mirror_bot** | aiogram (динамические экземпляры) | — | Клиентский интерфейс покупателей (множество ботов из БД) |
| **support_bot** | aiogram + FastAPI | 8181 | Внутренний бот: воркеры, саппорт, модерация; API уведомлений о заказах |
| **worker_bot** | aiogram (переиспользует support_bot) | — | Отдельный экземпляр для воркеров |
| **seller_bot** | aiogram | — | Telegram-интерфейс продавцов |
| **marketer_bot** | aiogram | — | Telegram-интерфейс маркетологов |
| **web_panel** | FastAPI + Jinja2 + APScheduler | 8000 | Админ-панель: CRM, аналитика, управление |
| **lookup_api** | FastAPI | — | Отдельный API для SSN/DL/CR поиска (своя SQLite) |
| **shared** | SQLAlchemy + сервисы | — | Общие модели, БД, бизнес-логика, утилиты |

---

## 3. Все таблицы основной БД

### 3.1 Ядро: боты и пользователи

| # | Таблица | Модель | Описание | Ключевые поля |
|---|---------|--------|----------|---------------|
| 1 | `mirror_bots` | MirrorBot | Экземпляры mirror-ботов | bot_token, bot_username, owner_user_id, bot_type, is_active |
| 2 | `bot_owners` | BotOwner | Владельцы ботов и их балансы | owner_user_id, balance, total_earned, total_withdrawn |
| 3 | `bot_owner_stats` | BotOwnerStats | Ежедневная статистика владельца бота | mirror_bot_id, date, spent, topped_up, owner_income |
| 4 | `bot_owner_withdrawals` | BotOwnerWithdrawal | Заявки на вывод владельцев ботов | owner_user_id, amount, payment_method, requisites, status |
| 5 | `users` | User | Покупатели (привязаны к mirror_bot) | user_id, mirror_bot_id, balance, language, trust_score, referrer_id, marketer_id, referral_link, is_banned |

### 3.2 Заказы и выполнение

| # | Таблица | Модель | Описание | Ключевые поля |
|---|---------|--------|----------|---------------|
| 6 | `orders` | Order | Lookup-заказы покупателей | user_id, mirror_bot_id, category, service_name, input_data, price, status, worker_id, is_bulk |
| 7 | `bulk_order_items` | BulkOrderItem | Элементы bulk-заказа (до 20 шт) | order_id, item_number, input_data, status, result_data |
| 8 | `worker_orders` | WorkerOrder | Зеркало заказа для воркера | order_id, worker_id, customer_id, status, intermediate_status, hidden_input |

### 3.3 Воркеры

| # | Таблица | Модель | Описание | Ключевые поля |
|---|---------|--------|----------|---------------|
| 9 | `workers` | Worker | Исполнители заказов | telegram_id, categories, services, balance, is_active, violation_count, fixed_price, commission_percent, worker_score |
| 10 | `worker_stats` | WorkerStats | Ежедневная статистика воркера | worker_id, date, category, orders_done, orders_nf, earnings |
| 11 | `worker_withdrawals` | WorkerWithdrawal | Заявки на вывод средств воркеров | worker_id, amount, requisites, status, funds_reserved |
| 12 | `worker_expense_reports` | WorkerExpenseReport | Отчёты воркеров о расходах | worker_id, amount, category (proxy/cards/other), status |
| 13 | `worker_violations` | WorkerViolation | Нарушения воркеров (утечка контактов и др.) | worker_id, order_id, violation_type, original_text, filtered_text |

### 3.4 Финансы и транзакции

| # | Таблица | Модель | Описание | Ключевые поля |
|---|---------|--------|----------|---------------|
| 14 | `transactions` | Transaction | Единый финансовый леджер | user_id, account_type, account_id, type, amount, currency, status, idempotency_key |
| 15 | `escrow_releases` | EscrowRelease | Журнал выплат эскроу продавцам | seller_order_id, seller_id, amount, released_by |

### 3.5 Товары и каталог

| # | Таблица | Модель | Описание | Ключевые поля |
|---|---------|--------|----------|---------------|
| 16 | `products` | Product | Товары (документы, fullz) | seller_id, category, service, state, price, file_path, moderation_status |
| 17 | `product_catalog_services` | ProductCatalogService | Каталог сервисов по категориям | category_key, menu_group, code, name |
| 18 | `mirror_menu_categories` | MirrorMenuCategory | Категории меню mirror-бота (мультиязычные) | code, route_key, label_en/ru/zh/es, row_index, position |
| 19 | `product_purchases` | ProductPurchase | Покупки товаров | product_id, user_id, order_id, delivered_at, guarantee_until |
| 20 | `product_ratings` | ProductRating | Оценки товаров (like/dislike) | purchase_id, user_id, rating |
| 21 | `product_action_logs` | ProductActionLog | Лог действий с товарами | product_id, actor_type, action, details |
| 22 | `product_moderation_logs` | ProductModerationLog | История модерации товаров | product_id, moderator_id, action, previous_status, new_status |
| 23 | `service_prices` | ServicePrice | Цены всех сервисов | key, category, price, bulk_price, is_active |
| 24 | `pricing_config` | PricingConfig | Глобальные настройки цен и таймеров | key, value_type, value_number/text/json |
| 25 | `bank_items` | BankItem | Динамический каталог банков (админка) | bank_code, name, category, section, price, position |
| 26 | `bank_positions` | BankPosition | Порядок отображения банков (legacy) | bank_id, category, position |
| 27 | `another_service_buttons` | AnotherServiceButton | Кнопки раздела "Another Services" | text_en/ru/zh/es, url, button_type, position |

### 3.6 Seller-система

| # | Таблица | Модель | Описание | Ключевые поля |
|---|---------|--------|----------|---------------|
| 28 | `sellers` | Seller | Продавцы | telegram_id, seller_type, access_status, markup_percent, deposit_balance, withdrawable_balance, seller_score |
| 29 | `seller_helpers` | SellerHelper | Помощники продавцов | seller_id, telegram_id, role (upload/support/manager_helper), status |
| 30 | `seller_helper_audit_logs` | SellerHelperAuditLog | Аудит действий помощников | seller_id, helper_id, action, object_type |
| 31 | `seller_deposit_payments` | SellerDepositPayment | Платежи депозита продавцов | seller_id, package_code, amount, provider, status |
| 32 | `seller_upload_batches` | SellerUploadBatch | Партии загрузки товаров | seller_id, item_type, upload_mode, moderation_status, total_items |
| 33 | `seller_upload_templates` | SellerUploadTemplate | Шаблоны загрузки | seller_id, item_type, title, payload |
| 34 | `seller_banks` | SellerBank | Банковские позиции от продавцов | seller_id, bank_name, bank_code, category, seller_price, buyer_price, stock_count, moderation_status |
| 35 | `seller_orders` | SellerOrder | Заказы на товары продавцов | seller_id, seller_bank_id, buyer_user_id, status, price_for_buyer, price_for_seller, escrow_released |
| 36 | `seller_withdrawals` | SellerWithdrawal | Заявки на вывод средств продавцов | seller_id, amount, requisites, status, funds_reserved |
| 37 | `seller_conversations` | SellerConversation | Чаты продавец-покупатель | seller_id, buyer_user_id, mirror_bot_id, assigned_helper_id |
| 38 | `seller_chats` | SellerChat | Сообщения в чатах | seller_conversation_id, seller_order_id, sender_type, message_text |
| 39 | `seller_order_disputes` | SellerOrderDispute | Споры по заказам продавцов | order_id, opened_by, reason, status, buyer_evidence, seller_evidence |

### 3.7 Seller-товары по типам

| # | Таблица | Модель | Тип товара | Описание |
|---|---------|--------|------------|----------|
| 40 | `seller_cc_items` | SellerCCItem | CC | Кредитные карты от продавцов |
| 41 | `seller_cc_orders` | SellerCCOrder | CC | Заказы CC |
| 42 | `seller_nfc_items` | SellerNFCItem | NFC | NFC-токены (Apple Pay / Google Pay) |
| 43 | `seller_nfc_orders` | SellerNFCOrder | NFC | Заказы NFC |
| 44 | `seller_otp_items` | SellerOTPItem | OTP | OTP-карты с SMS-доступом |
| 45 | `seller_otp_orders` | SellerOTPOrder | OTP | Заказы OTP |
| 46 | `seller_enroll_items` | SellerEnrollItem | Enroll | Enroll-аккаунты с порталами |
| 47 | `seller_enroll_orders` | SellerEnrollOrder | Enroll | Заказы Enroll |
| 48 | `seller_selfreg_ba_items` | SellerSelfregBAItem | Selfreg BA | Self-registered банковские аккаунты |
| 49 | `seller_selfreg_ba_orders` | SellerSelfregBAOrder | Selfreg BA | Заказы Selfreg BA |
| 50 | `seller_selfreg_cc_items` | SellerSelfregCCItem | Selfreg CC | Self-registered кредитные карты |
| 51 | `seller_selfreg_cc_orders` | SellerSelfregCCOrder | Selfreg CC | Заказы Selfreg CC |
| 52 | `seller_check_items` | SellerCheckItem | Checks | Чеки (personal/business/cashier) |
| 53 | `seller_check_orders` | SellerCheckOrder | Checks | Заказы чеков |
| 54 | `seller_logs_items` | SellerLogsItem | Logs | Банковские логи |
| 55 | `seller_logs_orders` | SellerLogsOrder | Logs | Заказы логов |
| 56 | `seller_document_items` | SellerDocumentItem | Docs | Документы (DL, паспорт, бизнес) |
| 57 | `seller_fullz_items` | SellerFullzItem | Fullz | Fullz-датасеты (personal/business) |

### 3.8 Маркетологи и рефералы

| # | Таблица | Модель | Описание | Ключевые поля |
|---|---------|--------|----------|---------------|
| 58 | `marketers` | Marketer | Маркетологи (реферальные партнёры) | telegram_id, promo_code, reward_percent, user_bonus_percent, balance |
| 59 | `marketer_stats` | MarketerStats | Ежедневная статистика маркетолога | marketer_id, date, registrations, first_topups, earned |
| 60 | `marketer_withdrawals` | MarketerWithdrawal | Заявки на вывод маркетологов | marketer_id, amount, requisites, status |
| 61 | `marketer_activity_logs` | MarketerActivityLog | Лог действий маркетологов | marketer_id, action, amount, details |
| 62 | `marketer_bot_links` | MarketerBotLink | Связь маркетолог ↔ mirror-бот | marketer_id, mirror_bot_id, is_active |
| 63 | `marketer_own_bots` | MarketerOwnBot | Собственные боты маркетологов | marketer_id, bot_token, bot_username, total_users, total_earned |
| 64 | `referrals` | Referral | Реферальные связи покупателей | referrer_id, referred_id, earned_total |

### 3.9 Поддержка и жалобы

| # | Таблица | Модель | Описание | Ключевые поля |
|---|---------|--------|----------|---------------|
| 65 | `support_tickets` | SupportTicket | Тикеты поддержки | user_id, mirror_bot_id, category, status, priority, assigned_to, sla_breach, csat_score |
| 66 | `support_messages` | SupportMessage | Сообщения в тикетах | ticket_id, sender_type, sender_id, message_text |
| 67 | `support_ticket_messages` | SupportTicketMessage | Расширенные сообщения (с internal notes) | ticket_id, sender_type, message, is_internal |
| 68 | `complaints` | Complaint | Жалобы покупателей на воркеров | worker_id, user_id, order_id, reason, status |
| 69 | `reports` | Report | Обращения пользователей (жалобы, партнёрство) | user_id, mirror_bot_id, report_type, subject, status |

### 3.10 Рассылки и переводы

| # | Таблица | Модель | Описание | Ключевые поля |
|---|---------|--------|----------|---------------|
| 70 | `broadcasts` | Broadcast | Массовые рассылки | mirror_bot_id, audience, message_text, status, total_users, sent_count |
| 71 | `broadcast_translations` | BroadcastTranslation | Переводы рассылок | broadcast_id, language, message_text |
| 72 | `ui_translations` | UiTranslation | Переводы UI-строк | key, language, text_value, namespace |

### 3.11 Купоны и скидки

| # | Таблица | Модель | Описание | Ключевые поля |
|---|---------|--------|----------|---------------|
| 73 | `coupons` | Coupon | Купоны на скидки | code, discount_type, discount_value, max_total_uses, is_active |
| 74 | `user_coupons` | UserCoupon | Активированные купоны пользователей | user_id, coupon_id, is_used |
| 75 | `coupon_redemptions` | CouponRedemption | Применения купонов (аналитика) | coupon_id, user_id, order_id, original_amount, discount_amount |
| 76 | `bulk_discount_tiers` | BulkDiscountTier | Скидки за количество | category, min_qty, discount_percent |

### 3.12 Корзина и вишлист

| # | Таблица | Модель | Описание | Ключевые поля |
|---|---------|--------|----------|---------------|
| 77 | `wishlist_items` | WishlistItem | Список желаний покупателя | user_id, product_type, product_id, price_at_add |
| 78 | `shopping_carts` | ShoppingCart | Корзина покупателя | user_id, status (active/abandoned/checked_out) |
| 79 | `cart_items` | CartItem | Элементы корзины | cart_id, product_type, product_id, price |

### 3.13 Education

| # | Таблица | Модель | Описание | Ключевые поля |
|---|---------|--------|----------|---------------|
| 80 | `education_categories` | EducationCategory | Категории обучения | code, name, item_type (subscription/manual) |
| 81 | `education_subscriptions` | EducationSubscription | Подписки на время | code, price, duration_days |
| 82 | `education_manuals` | EducationManual | Мануалы (файлы) | code, price, file_path |
| 83 | `manual_deliveries` | ManualDelivery | Лог выдачи мануалов (watermark tracing) | user_id, manual_id, delivered_at |

### 3.14 Аккаунты и подписки

| # | Таблица | Модель | Описание | Ключевые поля |
|---|---------|--------|----------|---------------|
| 84 | `account_categories` | AccountCategory | Категории каталога (BA, Lookup, AI, Proxy, **esim_sms**, **esim_data**, **gv**) | code, name, category_type |
| 85 | `account_items` | AccountItem | Позиции каталога; mirror_bot **eSIM** (SMS/Data/Google Voice) читает только `category_code` ∈ `esim_sms`, `esim_data`, `gv` | code, category_code, price, duration_months |
| 86 | `account_inventory` | AccountInventory | Загруженные единицы для мгновенной выдачи (в т.ч. eSIM/GV при наличии остатков) | item_id, credentials, is_sold, sold_to_user_id |

### 3.15 CC (кредитные карты)

| # | Таблица | Модель | Описание | Ключевые поля |
|---|---------|--------|----------|---------------|
| 87 | `cc_categories` | CCCategory | Категории CC (управляются админкой) | code, name, position |
| 88 | `cc_items` | CCItem | Товары CC (на заказ) | cc_code, name, category_code, price |

### 3.16 Brute Bank

| # | Таблица | Модель | Описание | Ключевые поля |
|---|---------|--------|----------|---------------|
| 89 | `brute_bank_items` | BruteBankItem | Брут-аккаунты от продавцов | seller_id, bank_code, category, credentials, price, moderation_status, status |
| 90 | `brute_bank_groups` | BruteBankGroup | Группы Brute Bank (витрина) | bank_code, bank_name, category, position |
| 91 | `brute_bank_orders` | BruteBankOrder | Покупки brute-аккаунтов | brute_bank_item_id, seller_id, buyer_user_id, price_for_buyer, price_for_seller |

### 3.17 Автоматизация

| # | Таблица | Модель | Описание | Ключевые поля |
|---|---------|--------|----------|---------------|
| 92 | `automation_proxies` | AutomationProxy | Прокси для автоматизации | name, host, port, proxy_type, is_active |
| 93 | `automation_api_keys` | AutomationApiKey | API-ключи внешних сервисов | provider, name, key_value, balance |
| 94 | `automation_configs` | AutomationConfig | Конфигурация automation-движка | service_code, is_enabled, worker_count, active_proxy_id |
| 95 | `automation_jobs` | AutomationJob | Задачи автоматизации (lookup_credit) | order_id, service_code, status, input_payload, result_payload, attempts |
| 96 | `automation_finance_entries` | AutomationFinanceEntry | Финансы автоматизации (доходы/расходы) | job_id, entry_type, source_type, amount |

### 3.18 Администрирование

| # | Таблица | Модель | Описание | Ключевые поля |
|---|---------|--------|----------|---------------|
| 97 | `admins` | Admin | Администраторы web-панели | username, password_hash, role, role_id, telegram_id |
| 98 | `admin_roles` | AdminRole | Кастомные роли с правами | name, permissions (JSON), is_system |
| 99 | `uploader_catalog_permissions` | UploaderCatalogPermission | Права загрузчиков по каталогам | uploader_id, catalog_code |
| 100 | `admin_audit_logs` | AdminAuditLog | Аудит действий админов | admin_id, action, entity_type, entity_id, ip_address |
| 101 | `audit_logs` | AuditLog | Универсальный аудит-стрим | source, event_type, actor_type, actor_id, target_type, target_id |

### 3.19 Системные и служебные

| # | Таблица | Модель | Описание | Ключевые поля |
|---|---------|--------|----------|---------------|
| 102 | `system_settings` | SystemSetting | Динамические системные настройки | key, value, description |
| 103 | `notification_logs` | NotificationLog | Лог попыток отправки уведомлений | event_type, channel, recipient_id, status, retry_count |
| 104 | `kb_articles` | KnowledgeBaseArticle | База знаний (Answer Bot, помощь) | title, body, keywords, category, audience |

---

## 4. Таблицы Lookup API (отдельная SQLite)

Lookup API работает на собственной SQLite БД, не связанной с основной PostgreSQL.

| # | Таблица | Описание | Ключевые поля |
|---|---------|----------|---------------|
| 1 | `api_keys` | API-аккаунты | username, password_hash, api_key, balance |
| 2 | `billing_log` | Биллинг | api_key_id, entry_type, amount, service |
| 3 | `persons` | SSN-записи | firstname, lastname, ssn, dob, address |
| 4 | `persons_fts` | FTS5-индекс для persons | (полнотекстовый поиск) |
| 5 | `licenses` | Водительские удостоверения | (связаны с persons) |
| 6 | `cr_records` | Кредитные отчёты (TransUnion, Experian и др.) | (связаны с persons) |

---

## 5. Матрица ответственности: сервис → таблицы

### main_bot

| Действие | Таблицы |
|----------|---------|
| Управление mirror-ботами | `mirror_bots` (CRUD) |
| Кабинет владельца | `bot_owners`, `bot_owner_stats`, `bot_owner_withdrawals` |
| API уведомлений покупателям | `users`, `orders` (чтение) |

### mirror_bot

| Действие | Таблицы |
|----------|---------|
| Регистрация и профиль | `users`, `referrals` |
| Заказы | `orders`, `bulk_order_items`, `transactions` |
| Купоны | `coupons`, `user_coupons`, `coupon_redemptions` |
| Товары | `products`, `product_purchases`, `product_ratings`, `reports` |
| Seller-покупки | `seller_banks`, `seller_orders`, `seller_cc_items`, `seller_conversations`, `seller_chats` |
| Brute | `brute_bank_items`, `brute_bank_groups`, `brute_bank_orders` |
| NFC/OTP/Enroll/Checks | `seller_nfc_items/orders`, `seller_otp_items/orders`, `seller_enroll_items/orders`, `seller_check_items/orders`, `seller_selfreg_*` |
| Поддержка | `support_tickets`, `support_messages` |
| Корзина и вишлист | `wishlist_items`, `shopping_carts`, `cart_items` |
| Education | `education_categories`, `education_subscriptions`, `education_manuals`, `manual_deliveries` |
| Аккаунты | `account_categories`, `account_items`, `account_inventory` |
| Автоматизация | `automation_jobs`, `automation_configs`, `automation_finance_entries` |
| Каталог и цены | `service_prices`, `pricing_config`, `bank_items`, `cc_categories`, `cc_items`, `mirror_menu_categories` |
| Другое | `another_service_buttons`, `system_settings` |

### support_bot

| Действие | Таблицы |
|----------|---------|
| Управление заказами | `orders`, `bulk_order_items`, `worker_orders` |
| Воркеры | `workers`, `worker_stats`, `worker_violations` |
| Пользователи | `users` |
| Seller-модерация | `seller_orders`, `seller_banks`, `seller_chats`, `seller_order_disputes`, `seller_cc_items`, `seller_nfc_items`, `seller_otp_items`, `seller_check_items`, `seller_document_items`, `seller_fullz_items` |
| Товары | `products`, `account_categories`, `account_items`, `account_inventory` |
| Поддержка | `support_tickets`, `support_ticket_messages` |
| Рассылки | `broadcasts`, `broadcast_translations` |
| Админы | `admins` |
| KB | `kb_articles` |

### worker_bot

| Действие | Таблицы |
|----------|---------|
| Дашборд заказов | `worker_orders`, `orders`, `bulk_order_items` |
| Профиль и статистика | `workers`, `worker_stats` |
| Жалобы | `complaints` |
| Выводы | `worker_withdrawals` |
| Расходы | `worker_expense_reports` |

### seller_bot

| Действие | Таблицы |
|----------|---------|
| Профиль | `sellers`, `seller_helpers`, `seller_helper_audit_logs` |
| Склад и загрузка | `seller_banks`, `seller_upload_batches`, `seller_upload_templates` |
| Все типы товаров | `seller_cc_items`, `seller_nfc_items`, `seller_otp_items`, `seller_enroll_items`, `seller_selfreg_ba_items`, `seller_selfreg_cc_items`, `seller_check_items`, `seller_logs_items`, `seller_document_items`, `seller_fullz_items` |
| Заказы | `seller_orders`, `seller_cc_orders`, `seller_nfc_orders`, `seller_otp_orders`, `seller_enroll_orders`, `seller_selfreg_ba_orders`, `seller_selfreg_cc_orders`, `seller_check_orders`, `seller_logs_orders` |
| Чат | `seller_conversations`, `seller_chats` |
| Выводы | `seller_withdrawals` |
| Депозит | `seller_deposit_payments` |

### marketer_bot

| Действие | Таблицы |
|----------|---------|
| Профиль | `marketers` |
| Статистика | `marketer_stats`, `marketer_activity_logs` |
| Выводы | `marketer_withdrawals` |
| Боты | `marketer_bot_links`, `marketer_own_bots` |

### web_panel

| Действие | Таблицы |
|----------|---------|
| Пользователи | `users`, `orders`, `transactions` |
| Воркеры | `workers`, `worker_stats`, `worker_withdrawals`, `worker_expense_reports`, `worker_violations` |
| Продавцы | `sellers`, `seller_banks`, `seller_orders`, `seller_withdrawals`, `seller_order_disputes`, все `seller_*_items` |
| Маркетологи | `marketers`, `marketer_withdrawals`, `marketer_stats`, `marketer_activity_logs` |
| Боты | `mirror_bots`, `bot_owners`, `bot_owner_stats` |
| Товары | `products`, `product_catalog_services`, `product_moderation_logs` |
| Каталог | `bank_items`, `bank_positions`, `cc_categories`, `cc_items`, `brute_bank_groups` |
| Цены | `service_prices`, `pricing_config` |
| Купоны | `coupons`, `bulk_discount_tiers` |
| Поддержка | `support_tickets` |
| Рассылки | `broadcasts`, `broadcast_translations`, `ui_translations` |
| Аккаунты | `account_categories`, `account_items`, `account_inventory` |
| Education | `education_categories`, `education_subscriptions`, `education_manuals` |
| Автоматизация | `automation_proxies`, `automation_api_keys`, `automation_configs`, `automation_jobs`, `automation_finance_entries` |
| Админы | `admins`, `admin_roles`, `uploader_catalog_permissions`, `admin_audit_logs`, `audit_logs` |
| Уведомления | `notification_logs` |
| Настройки | `system_settings`, `another_service_buttons`, `mirror_menu_categories` |
| KB | `kb_articles` |

### shared (сервисы)

| Сервис | Таблицы |
|--------|---------|
| Ledger (ledger_projection_service) | `transactions` |
| Seller finance (seller_finance_service) | `sellers`, `seller_orders`, `escrow_releases` |
| Seller disputes (seller_dispute_service) | `seller_order_disputes`, `seller_orders` |
| Worker earnings (worker_earnings_service) | `workers`, `orders`, `bulk_order_items` |
| Coupons (coupon_service) | `coupons`, `coupon_redemptions`, `user_coupons`, `orders` |
| Bulk discounts (bulk_discount_service) | `bulk_discount_tiers` |
| Upload pipeline (seller_upload_pipeline_service) | `seller_upload_batches`, `brute_bank_items`, все `seller_*_items` |
| Notifications | `notification_logs` |

### lookup_api

| Действие | Таблицы (собственная SQLite) |
|----------|------------------------------|
| Аутентификация | `api_keys` |
| Биллинг | `billing_log` |
| Поиск | `persons`, `persons_fts`, `licenses`, `cr_records` |

---

## 6. Потоки данных

### Buyer Flow (покупка lookup)

```
Покупатель → mirror_bot
  → создание User + Order в общей БД
  → support_bot получает уведомление (API :8181)
  → воркер берёт заказ (worker_orders)
  → результат → main_bot API → уведомление в mirror_bot
```

### Seller Flow (покупка товара продавца)

```
Покупатель → mirror_bot → seller_orders / seller_cc_orders / brute_bank_orders
  → support_bot модерирует
  → seller_bot уведомляет продавца
  → продавец работает с заказом + чат (seller_chats)
  → escrow → seller.withdrawable_balance
```

### Marketer Flow

```
Маркетолог → marketer_bot → promo_code
  → покупатель регистрируется с промокодом → users.marketer_id
  → при пополнении → marketer.balance += reward_percent%
  → marketer_stats фиксирует ежедневно
```

### Admin Flow

```
Администратор → web_panel
  → управление всеми сущностями через CRUD
  → модерация товаров, заказов, выводов
  → фоновые задачи (APScheduler)
  → аудит → admin_audit_logs / audit_logs
```

### Automation Flow

```
Заказ lookup_credit → automation_jobs (queued)
  → automation engine (proxy + API keys)
  → результат → order.result_data
  → finance → automation_finance_entries
```

---

**Итого: 104 таблицы в основной БД + 6 таблиц в Lookup API SQLite = 110 таблиц.**

---

## 7. Пошаговый план обновления системы

### Этап 0: Подготовка и стабилизация (перед любыми изменениями)

| # | Задача | Файлы | Статус |
|---|--------|-------|--------|
| 0.1 | Сделать полный бэкап БД (`pg_dump`) и кодовой базы | — | [ ] |
| 0.2 | Убедиться что `docker compose up -d` поднимает все сервисы без ошибок | `docker-compose.yml`, `.env.example` | [ ] |
| 0.3 | Пройти Smoke Checklist из `LAUNCH_RUNBOOK.md` | `docs/LAUNCH_RUNBOOK.md` | [ ] |
| 0.4 | Зафиксировать текущее состояние: первый git commit | все файлы | [ ] |
| 0.5 | Добавить `start_bots.sh` запуск `worker_bot` и `lookup_api` | `start_bots.sh` | [ ] |

---

### Этап 1: Исправление критических багов и silent failures

**Цель:** Устранить места, где ошибки проглатываются молча (`except: pass`), что приводит к потере данных или денег.

| # | Задача | Файлы | Приоритет |
|---|--------|-------|-----------|
| 1.1 | Seller withdrawal: добавить логирование при неудачном rollback статуса | `seller_bot/handlers/withdrawal.py` | Высокий |
| 1.2 | Seller upload template: обработать ошибку сохранения шаблона | `seller_bot/handlers/upload_fsm.py` | Высокий |
| 1.3 | Dispute notification: добавить retry/fallback при уведомлении админа | `mirror_bot/handlers/seller_specials.py` | Высокий |
| 1.4 | Order service: логировать ошибки при начислении реферальных комиссий | `mirror_bot/services/order_service.py` | Высокий |
| 1.5 | Product audit: логировать ошибки вместо `pass` | `mirror_bot/handlers/products.py`, `support_bot/handlers/upload_product.py` | Средний |
| 1.6 | Cart messages: добавить логирование при ошибках редактирования | `mirror_bot/handlers/cart.py` | Низкий |

---

### Этап 2: Доработка ядра заказов и воркеров

**Цель:** Стабильная работа основного buyer → worker flow.

| # | Задача | Таблицы | Файлы |
|---|--------|---------|-------|
| 2.1 | Проверить и протестировать полный цикл: создание заказа → уведомление support_bot → взятие воркером → выполнение → уведомление покупателя | `orders`, `worker_orders`, `bulk_order_items`, `workers` | `mirror_bot/handlers/lookup/`, `support_bot/handlers/orders.py`, `worker_bot/` |
| 2.2 | Проверить bulk-заказы (до 20 элементов): создание, поэлементное выполнение, частичный NF | `bulk_order_items` | `mirror_bot/handlers/lookup/`, `support_bot/handlers/bulk_orders.py` |
| 2.3 | Проверить intermediate_status воркера (searching, processing, problem) и паузу таймера | `worker_orders` | `worker_bot/handlers/dashboard.py` |
| 2.4 | Проверить worker_violations: фильтрация контактов в результатах | `worker_violations` | `shared/services/` |
| 2.5 | Протестировать worker_stats: ежедневная статистика корректно считается | `worker_stats` | `shared/services/worker_earnings_service.py` |
| 2.6 | Протестировать worker withdrawals и expense reports через worker_bot | `worker_withdrawals`, `worker_expense_reports` | `worker_bot/`, `web_panel/api/workers.py` |

---

### Этап 3: Seller-система (товары, модерация, escrow)

**Цель:** Полный цикл: загрузка товара → модерация → покупка → escrow → выплата.

| # | Задача | Таблицы | Файлы |
|---|--------|---------|-------|
| 3.1 | **Seller Banks (log):** загрузка → модерация → покупка → чат → escrow release | `seller_banks`, `seller_orders`, `seller_chats`, `escrow_releases` | `seller_bot/`, `support_bot/handlers/seller_orders.py`, `mirror_bot/handlers/banks.py` |
| 3.2 | **Seller CC:** загрузка → модерация → покупка | `seller_cc_items`, `seller_cc_orders` | `seller_bot/handlers/`, `mirror_bot/handlers/seller_specials.py` |
| 3.3 | **Seller NFC:** загрузка → модерация → покупка | `seller_nfc_items`, `seller_nfc_orders` | аналогично |
| 3.4 | **Seller OTP:** загрузка → модерация → покупка | `seller_otp_items`, `seller_otp_orders` | аналогично |
| 3.5 | **Seller Enroll:** загрузка → модерация → покупка | `seller_enroll_items`, `seller_enroll_orders` | аналогично |
| 3.6 | **Seller Selfreg BA:** загрузка → модерация → покупка | `seller_selfreg_ba_items`, `seller_selfreg_ba_orders` | аналогично |
| 3.7 | **Seller Selfreg CC:** загрузка → модерация → покупка (заменить placeholder MerchantItem) | `seller_selfreg_cc_items`, `seller_selfreg_cc_orders` | `mirror_bot/handlers/seller_specials.py` |
| 3.8 | **Seller Checks:** загрузка → модерация → покупка | `seller_check_items`, `seller_check_orders` | аналогично |
| 3.9 | **Seller Logs:** загрузка → модерация → покупка | `seller_logs_items`, `seller_logs_orders` | аналогично |
| 3.10 | **Seller Documents:** загрузка → модерация | `seller_document_items` | `seller_bot/handlers/` |
| 3.11 | **Seller Fullz:** загрузка → модерация | `seller_fullz_items` | `seller_bot/handlers/` |
| 3.12 | **Brute Bank:** полная реализация buyer-side (убрать "SOON") | `brute_bank_items`, `brute_bank_groups`, `brute_bank_orders` | `mirror_bot/handlers/banks.py` |
| 3.13 | **Seller Helpers:** проверить flow помощников (upload_helper, support_helper, manager_helper) | `seller_helpers`, `seller_helper_audit_logs` | `seller_bot/handlers/` |
| 3.14 | **Seller Disputes:** полный цикл dispute → evidence → resolution | `seller_order_disputes` | `mirror_bot/handlers/seller_specials.py`, `web_panel/` |
| 3.15 | **Seller Withdrawals:** проверить полный цикл через seller_bot + web_panel | `seller_withdrawals` | `seller_bot/handlers/withdrawal.py`, `web_panel/api/seller_crm.py` |
| 3.16 | **Upload Batches:** проверить bulk upload + per-item moderation | `seller_upload_batches` | `seller_bot/`, `support_bot/`, `web_panel/` |

---

### Этап 4: Финансовая система (леджер, купоны, скидки)

**Цель:** Корректный учёт всех денежных операций.

| # | Задача | Таблицы | Файлы |
|---|--------|---------|-------|
| 4.1 | Проверить единый леджер: deposit, purchase, withdrawal, commission, refund, payout_worker | `transactions` | `shared/services/ledger_projection_service.py` |
| 4.2 | Проверить idempotency_key — нет дублирования транзакций | `transactions` | `shared/services/` |
| 4.3 | Проверить escrow: pending_balance → withdrawable_balance при auto_complete | `sellers`, `escrow_releases` | `shared/services/seller_finance_service.py` |
| 4.4 | Купоны: создание → активация → применение → лимиты (max_uses, per_user, categories) | `coupons`, `user_coupons`, `coupon_redemptions` | `shared/services/coupon_service.py`, `mirror_bot/` |
| 4.5 | Bulk discounts: корректное применение скидок за количество | `bulk_discount_tiers` | `shared/services/bulk_discount_service.py` |
| 4.6 | Реферальные начисления: referrer получает % при пополнении referred | `referrals`, `transactions` | `mirror_bot/services/order_service.py` |
| 4.7 | Bot owner income: 7% с пополнений пользователей | `bot_owner_stats`, `bot_owners` | `main_bot/` |

---

### Этап 5: Маркетологи

**Цель:** Полный цикл маркетолога: промокод → привлечение → начисления → вывод.

| # | Задача | Таблицы | Файлы |
|---|--------|---------|-------|
| 5.1 | Регистрация маркетолога, генерация promo_code | `marketers` | `marketer_bot/handlers/` |
| 5.2 | Привязка пользователя по промокоду (users.marketer_id) | `users`, `marketers` | `mirror_bot/handlers/start.py` |
| 5.3 | Начисление reward_percent при пополнении привлечённого пользователя | `marketers`, `marketer_stats`, `marketer_activity_logs` | `shared/services/` |
| 5.4 | Marketer bot links: аналитика по нескольким ботам | `marketer_bot_links` | `marketer_bot/handlers/` |
| 5.5 | Marketer own bots: регистрация собственного бота-клона | `marketer_own_bots` | `marketer_bot/handlers/` |
| 5.6 | Marketer withdrawals: заявка → approve/reject через web_panel | `marketer_withdrawals` | `marketer_bot/handlers/withdrawal.py`, `web_panel/api/marketers.py` |

---

### Этап 6: Поддержка и тикеты

**Цель:** Полный цикл поддержки с SLA и CSAT.

| # | Задача | Таблицы | Файлы |
|---|--------|---------|-------|
| 6.1 | Создание тикета покупателем (категории: payment, product, general, partnership) | `support_tickets`, `support_messages` | `mirror_bot/handlers/support.py` |
| 6.2 | Обработка тикета в support_bot (assigned_to, internal notes) | `support_tickets`, `support_ticket_messages` | `support_bot/handlers/` |
| 6.3 | SLA: first_response_at, sla_breach, escalated_at | `support_tickets` | `shared/services/` |
| 6.4 | CSAT: запрос оценки после закрытия (csat_score 1-3) | `support_tickets` | `mirror_bot/`, `support_bot/` |
| 6.5 | Жалобы на воркеров: создание → рассмотрение → резолюция | `complaints` | `mirror_bot/`, `support_bot/`, `web_panel/` |
| 6.6 | Reports: обращения пользователей через web_panel | `reports` | `mirror_bot/handlers/`, `web_panel/` |
| 6.7 | Knowledge Base: статьи для Answer Bot и помощи | `kb_articles` | `support_bot/`, `web_panel/` |

---

### Этап 7: Каталог и новые разделы

**Цель:** Доработка каталогов и реализация "Coming Soon" разделов.

| # | Задача | Таблицы | Файлы |
|---|--------|---------|-------|
| 7.1 | **Drawing Documents (High-Quality):** полная реализация | `products`, `orders` | `mirror_bot/handlers/documents.py`, `prices.py` |
| 7.2 | **Robot Drawing:** полная реализация | `products`, `orders` | `mirror_bot/handlers/documents.py` |
| 7.3 | **Education:** подписки + мануалы buyer flow | `education_categories`, `education_subscriptions`, `education_manuals`, `manual_deliveries` | `mirror_bot/handlers/`, `web_panel/` |
| 7.4 | **Accounts inventory:** мгновенная выдача из загруженного стока | `account_inventory` | `mirror_bot/handlers/accounts.py`, `support_bot/` |
| 7.5 | **CC каталог:** buyer-side покупка CC на заказ | `cc_categories`, `cc_items` | `mirror_bot/handlers/` |
| 7.6 | **Another Services:** динамические кнопки из БД | `another_service_buttons` | `mirror_bot/handlers/`, `web_panel/` |
| 7.7 | **Mirror Menu Categories:** динамическое меню из БД вместо хардкода | `mirror_menu_categories` | `mirror_bot/keyboards/reply.py` |
| 7.8 | **Product Catalog Services:** динамический каталог сервисов | `product_catalog_services` | `mirror_bot/`, `web_panel/` |

---

### Этап 8: Автоматизация (lookup_credit)

**Цель:** Автоматическое выполнение credit report заказов без участия воркера.

| # | Задача | Таблицы | Файлы |
|---|--------|---------|-------|
| 8.1 | Automation engine: очередь → прокси → выполнение → результат | `automation_jobs`, `automation_configs`, `automation_proxies` | `mirror_bot/handlers/cr_automation.py`, `shared/services/` |
| 8.2 | API keys rotation: ротация ключей при исчерпании лимита | `automation_api_keys` | `web_panel/`, `shared/services/` |
| 8.3 | SSN flow: запрос SSN у покупателя при необходимости | `automation_jobs` (needs_ssn) | `mirror_bot/handlers/cr_automation.py` |
| 8.4 | Finance tracking: доходы vs расходы автоматизации | `automation_finance_entries` | `web_panel/` |
| 8.5 | Admin dashboard: мониторинг очереди, ошибок, прокси | `automation_jobs`, `automation_proxies` | `web_panel/` |

---

### Этап 9: Web Panel (админка)

**Цель:** Полнофункциональная админ-панель для всех разделов.

| # | Задача | Таблицы | Файлы |
|---|--------|---------|-------|
| 9.1 | Перенести навигацию из хардкода в БД (или гибрид) | — | `web_panel/templates/_nav.html`, `web_panel/api/` |
| 9.2 | Перенести CATEGORIES_DATA из констант в БД | `product_catalog_services` | `web_panel/constants/categories.py` |
| 9.3 | Расширить систему выплат: Cryptomus auto-payout | `seller_withdrawals`, `marketer_withdrawals` | `shared/services/payout_service.py`, `web_panel/` |
| 9.4 | Admin roles: проверить RBAC для всех разделов | `admins`, `admin_roles`, `uploader_catalog_permissions` | `web_panel/` |
| 9.5 | Audit logs: убедиться что все действия логируются | `admin_audit_logs`, `audit_logs` | `web_panel/` |
| 9.6 | Notification logs: UI для просмотра и retry | `notification_logs` | `web_panel/` |
| 9.7 | UI Translations: управление переводами из панели | `ui_translations` | `web_panel/` |
| 9.8 | Broadcasts: создание → перевод → отправка → статистика | `broadcasts`, `broadcast_translations` | `web_panel/`, `support_bot/` |

---

### Этап 10: Корзина, вишлист и UX-улучшения

**Цель:** Улучшение покупательского опыта.

| # | Задача | Таблицы | Файлы |
|---|--------|---------|-------|
| 10.1 | Корзина: добавление → просмотр → checkout (несколько товаров за раз) | `shopping_carts`, `cart_items` | `mirror_bot/handlers/cart.py` |
| 10.2 | Вишлист: добавление → уведомление о снижении цены | `wishlist_items` | `mirror_bot/handlers/wishlist.py` |
| 10.3 | Abandoned cart notifications | `shopping_carts` (abandoned_notified) | `shared/services/` |
| 10.4 | Welcome bonus и onboarding tour | `users`, `coupons` | `mirror_bot/handlers/start.py` |
| 10.5 | Notification preferences: настройка уведомлений покупателем | `users` (notif_*) | `mirror_bot/handlers/profile.py` |

---

### Этап 11: Lookup API

**Цель:** Отдельный API для SSN/DL/CR поиска.

| # | Задача | Таблицы (SQLite) | Файлы |
|---|--------|------------------|-------|
| 11.1 | API endpoints: SSN lookup, DL lookup, CR lookup | `persons`, `licenses`, `cr_records` | `lookup_api/` |
| 11.2 | API keys и биллинг: создание ключей, списание за запросы | `api_keys`, `billing_log` | `lookup_api/` |
| 11.3 | FTS поиск: полнотекстовый поиск по persons | `persons_fts` | `lookup_api/` |
| 11.4 | Импорт данных: загрузка баз из CSV/JSON | `persons`, `licenses`, `cr_records` | `lookup_api/importer.py` |
| 11.5 | Интеграция с mirror_bot: автоматическое выполнение lookup-заказов | `orders` (основная БД) | `mirror_bot/`, `lookup_api/` |

---

### Этап 12: Инфраструктура и production hardening

**Цель:** Готовность к production.

| # | Задача | Файлы |
|---|--------|-------|
| 12.1 | Health checks для всех сервисов в docker-compose | `docker-compose.yml` |
| 12.2 | Мониторинг: Prometheus metrics + Grafana dashboards | `docker-compose.yml`, `shared/` |
| 12.3 | Логирование: структурированные логи (JSON) во всех сервисах | все сервисы |
| 12.4 | Бэкапы: автоматический pg_dump + offsite copy | `scripts/` |
| 12.5 | TLS: reverse proxy (nginx/caddy) для web_panel и API | `docker-compose.yml`, `nginx.conf` |
| 12.6 | Rate limiting: защита от спама в ботах | `mirror_bot/`, `support_bot/` |
| 12.7 | CI/CD: GitHub Actions для тестов и деплоя | `.github/workflows/` |
| 12.8 | Тесты: unit + integration для критических flows | `tests/` |
| 12.9 | Документация env vars по каждому сервису | `docs/` |
| 12.10 | Alembic миграции вместо ad-hoc скриптов | `shared/database/` |

---

### Сводная таблица этапов

| Этап | Название | Задач | Приоритет | Зависимости |
|------|----------|-------|-----------|-------------|
| **0** | Подготовка и стабилизация | 5 | Критический | — |
| **1** | Исправление silent failures | 6 | Критический | Этап 0 |
| **2** | Ядро заказов и воркеров | 6 | Критический | Этап 1 |
| **3** | Seller-система | 16 | Высокий | Этап 2 |
| **4** | Финансовая система | 7 | Высокий | Этап 2 |
| **5** | Маркетологи | 6 | Средний | Этап 4 |
| **6** | Поддержка и тикеты | 7 | Средний | Этап 2 |
| **7** | Каталог и новые разделы | 8 | Средний | Этап 3 |
| **8** | Автоматизация (lookup_credit) | 5 | Средний | Этап 2 |
| **9** | Web Panel (админка) | 8 | Средний | Этапы 3–6 |
| **10** | Корзина, вишлист, UX | 5 | Низкий | Этап 7 |
| **11** | Lookup API | 5 | Низкий | Этап 2 |
| **12** | Инфраструктура и production | 10 | Низкий (но перед go-live) | Все этапы |

---

### Рекомендуемый порядок выполнения

```
Этап 0 → Этап 1 → Этап 2
                      ├──→ Этап 3 (seller) ──→ Этап 7 (каталог)
                      ├──→ Этап 4 (финансы) ──→ Этап 5 (маркетологи)
                      ├──→ Этап 6 (поддержка)
                      ├──→ Этап 8 (автоматизация)
                      └──→ Этап 11 (lookup API)
                                    │
                      Этапы 3–8 ──→ Этап 9 (web panel)
                                    │
                      Этап 9 ────→ Этап 10 (UX)
                                    │
                      Все ────────→ Этап 12 (production)
```
