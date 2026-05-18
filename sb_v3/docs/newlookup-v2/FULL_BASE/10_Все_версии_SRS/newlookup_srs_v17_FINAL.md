# Newlookup — Техническое Задание v17.0 (Максимальная Детализация)

**Версия:** 17.0  
**Дата:** 13.03.2026  
**Статус:** Финальная  
**Объём:** 3085 строк, 127 КБ — полное описание всех компонентов до каждой кнопки

> **Что новое в v17:** Расширены права `support` (редактирование цен, просмотр пополнений, лог изменений → владельцу) и `moderator` (рассылки во всех ботах). Обновлены спецификации товаров 14.1–14.5: убраны `balance` и `online_access` из Selfreg BA, добавлен динамический счётчик аренды номера, конфигуратор счетов в Mini App для Logs BA, полная логика массового импорта CC Dumps с ручной пометкой non_vbv/with_fullz/zip_only. Добавлены 3 варианта дизайна Admin Panel. Убрана программа лояльности.

---

## Оглавление

1. [Введение и философия](#1)
2. [Архитектура системы](#2)
3. [Ролевая модель (RBAC)](#3)
4. [База данных — полная схема](#4)
5. [Mirror Bot — Клиентский бот](#5)
6. [Seller Bot — Бот продавца](#6)
7. [Seller Mini App — Веб-приложение продавца](#7)
8. [Marketer Bot — Бот маркетолога](#8)
9. [Support Bot — Бот поддержки](#9)
10. [Worker Bot — Бот воркера](#10)
11. [Main Bot — Бот владельца](#11)
12. [Admin Panel — Веб-панель управления](#12)
13. [Модуль Автоматизации Пробива](#13)
14. [Финансовая модель и монетизация](#14)
15. [Рекламная платформа и управление каналами](#15)
16. [Публичный сайт и SEO](#16)
17. [Управление командой продавца](#17)
18. [Детальные спецификации товаров](#18)
19. [Безопасность — Zero Trust](#19)
20. [Приоритеты разработки](#20)
21. [Глоссарий](#21)

---

## 1. Введение и Философия {#1}

### 1.1. Назначение системы

Newlookup — это многоуровневый Telegram-маркетплейс цифровых данных с поддержкой нескольких независимых ботов-зеркал, продавцов, маркетологов и автоматизированного пробива. Система построена на принципе **разделения ответственности**: каждый участник (покупатель, продавец, маркетолог, воркер, поддержка, владелец) взаимодействует через свой специализированный интерфейс.

### 1.2. Ключевые принципы

| Принцип | Описание |
| :--- | :--- |
| **Мгновенность** | Покупатель получает товар в течение секунд после оплаты (In Stocks) или видит точный статус ожидания (Per Order). |
| **Масштабируемость** | Один экземпляр системы поддерживает неограниченное количество Mirror Bot-зеркал. |
| **Прозрачность** | Каждая финансовая операция имеет `trace_id` и полный аудит-лог. |
| **Безопасность** | Zero Trust архитектура — ни один компонент не доверяет другому по умолчанию. |
| **Многоязычность** | Интерфейс на 4 языках: EN, RU, ES, ZH. Язык определяется автоматически по `language_code` Telegram. |

### 1.3. Участники системы

| Роль | Интерфейс | Описание |
| :--- | :--- | :--- |
| **Покупатель** | Mirror Bot | Покупает товары и услуги. |
| **Продавец** | Seller Bot + Seller Mini App | Загружает и продаёт товары. |
| **Маркетолог** | Marketer Bot | Привлекает покупателей через боты-прокси. |
| **Воркер** | Worker Bot + CRM | Выполняет заказы Per Order вручную. |
| **Поддержка** | Support Bot | Обрабатывает тикеты, споры, выводы средств. |
| **Владелец** | Main Bot | Управляет всей системой. |
| **Администратор** | Admin Panel | Настраивает каталог, цены, рассылки. |

---

## 2. Архитектура Системы {#2}

### 2.1. Компоненты

```
┌─────────────────────────────────────────────────────────────────┐
│                        TELEGRAM LAYER                           │
│  Mirror Bot(s) │ Seller Bot │ Marketer Bot │ Support Bot        │
│  Worker Bot    │ Main Bot                                        │
└────────────────────────────┬────────────────────────────────────┘
                             │ aiogram 3.x
┌────────────────────────────▼────────────────────────────────────┐
│                        APPLICATION LAYER                        │
│  FastAPI (Admin Panel API)  │  FastAPI (Automation Service)     │
│  Celery Workers             │  Redis (Queue + Cache)            │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                         DATA LAYER                              │
│  PostgreSQL (основная БД)   │  S3-совместимое хранилище         │
│  Redis (сессии, кэш)        │  (файлы товаров, QR-коды)         │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2. Технологический стек

| Компонент | Технология | Обоснование |
| :--- | :--- | :--- |
| **Боты** | Python 3.11 + aiogram 3.x | Лучший async-фреймворк для Telegram. |
| **Web API** | FastAPI + Pydantic v2 | Высокая производительность, автодокументация. |
| **БД** | PostgreSQL 16 | ACID-транзакции, JSON-поля, надёжность. |
| **ORM** | SQLAlchemy 2.0 async | Async-поддержка, типизация. |
| **Очередь задач** | Celery + Redis | Асинхронное выполнение автоматизаций. |
| **Кэш/сессии** | Redis 7 | Хранение FSM-состояний, кэш. |
| **Фронтенд Admin** | React + TailwindCSS + shadcn/ui | Плотный тёмный дашборд. |
| **Фронтенд Mini App** | React + TailwindCSS | Telegram Mini App. |
| **Публичный сайт** | Astro + TailwindCSS | Максимальная скорость, SEO. |
| **Хранилище файлов** | MinIO (self-hosted S3) | Безопасное хранение данных товаров. |
| **Реверс-прокси** | Nginx | SSL, балансировка нагрузки. |
| **Контейнеризация** | Docker + Docker Compose | Единая среда развёртывания. |
| **Мониторинг** | Prometheus + Grafana | Метрики производительности. |

### 2.3. Переменные окружения

```env
# Telegram Bot Tokens
MIRROR_BOT_TOKEN=...
SELLER_BOT_TOKEN=...
MARKETER_BOT_TOKEN=...
SUPPORT_BOT_TOKEN=...
WORKER_BOT_TOKEN=...
MAIN_BOT_TOKEN=...

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/newlookup

# Redis
REDIS_URL=redis://redis:6379/0

# S3 Storage
S3_ENDPOINT=http://minio:9000
S3_BUCKET=newlookup-products
S3_ACCESS_KEY=...
S3_SECRET_KEY=...

# Payment Gateways
BTCPAY_URL=https://btcpay.yourdomain.com
BTCPAY_API_KEY=...
BTCPAY_STORE_ID=...
HELECAT_API_KEY=...

# Automation APIs
NUMVERIFY_API_KEY=...
SMARTY_AUTH_ID=...
SMARTY_AUTH_TOKEN=...
EMAILREP_API_KEY=...
CS_BOT_HOST=193.221.200.87
CS_BOT_PATH=/opt/credit_score_bot

# Admin Panel
ADMIN_JWT_SECRET=...
ADMIN_JWT_EXPIRE_MINUTES=60

# Proxy (for workers)
WEBSHARE_API_KEY=...
```

---

### 3.2. Матрица доступа к Admin Panel (v17)

**Ключевые изменения:** Роли `support` и `moderator` получили расширенные права для большей автономности. `support` теперь управляет ценами и видит финансовые потоки, а `moderator` — отвечает за коммуникацию с пользователями через рассылки.

| Раздел Admin Panel | `support` | `moderator` | `finance` | `admin` | `auditor` | `owner` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Дашборд (общий просмотр) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Финансы (просмотр)** | **✓** | — | ✓ | ✓ | ✓ | ✓ |
| Каталог (редактирование) | — | — | — | ✓ | — | ✓ |
| **Цены (редактирование)** | **✓** | — | — | ✓ | — | ✓ |
| Купоны | — | — | — | ✓ | — | ✓ |
| **Рассылки** | — | **✓** | — | ✓ | — | ✓ |
| Модерация товаров | — | ✓ | — | ✓ | — | ✓ |
| Выводы средств | — | — | ✓ | — | — | ✓ |
| Споры | — | ✓ | — | ✓ | — | ✓ |
| Аудит-логи | — | — | — | — | ✓ | ✓ |
| Автоматизации | — | — | — | ✓ | — | ✓ |
| Пользователи (бан/разбан) | — | ✓ | — | ✓ | — | ✓ |

---

### 3.3. Детализация новой логики доступов

#### 3.3.1. Логика для роли `support`

1.  **Редактирование цен:**
    *   **Интерфейс:** В разделе "Управление каталогом" или в отдельном разделе "Цены" у роли `support` появляется возможность редактировать поле цены для каждого товара.
    *   **Аудит:** Любое изменение цены (`product.price`) сотрудником с ролью `support` должно создавать запись в таблице `audit_logs`.
        *   `actor_id`: ID сотрудника.
        *   `action`: `'product_price_update'`.
        *   `target_type`: `'product'`.
        *   `target_id`: ID продукта.
        *   `details`: `{'old_price': 150.00, 'new_price': 145.00}`.
    *   **Уведомление владельцу:** Сразу после изменения цены система должна отправлять уведомление в **Main Bot** (личному боту владельца) с полной информацией об изменении: `"User @support_john changed price for product #123 (Chase Bank) from $150 to $145."`. 

2.  **Просмотр пополнений:**
    *   **Интерфейс:** В Admin Panel появляется новый раздел **"Финансы"**, доступный для `support` в режиме read-only.
    *   **Содержание:** Раздел содержит две вкладки:
        1.  **"Пополнения через платежные системы":** Таблица с данными из `deposits` (статус `completed`). Поля: `Дата`, `Пользователь`, `Сумма`, `Метод` (btcpay/helecat), `Invoice ID`.
        2.  **"Движения по внутреннему балансу":** Таблица с данными из `transactions`. Поля: `Дата`, `Пользователь`, `Тип операции` (deposit, purchase, refund), `Сумма`, `Баланс до`, `Баланс после`.
    *   **Обновление:** Данные в таблицах должны обновляться в реальном времени (используя WebSocket).

#### 3.3.2. Логика для роли `moderator`

1.  **Создание рассылок:**
    *   **Интерфейс:** Роль `moderator` получает полный доступ к разделу **"Рассылки"** в Admin Panel.
    *   **Функционал:** Модератор может:
        *   Создавать текстовые сообщения, прикреплять медиа (фото/видео).
        *   Выбирать целевую аудиторию: `all`, `buyers`, `sellers`, `marketers` или кастомный сегмент из CRM (например, "покупатели, потратившие > $1000").
        *   Использовать опцию "Закрепить сообщение" (`pin_message`).
        *   Запускать рассылку немедленно или откладывать на определенное время.
    *   **Ограничения:** Модератор не может удалять рассылки, созданные `admin` или `owner`. Он может только просматривать их статистику (отправлено, доставлено, ошибки).
---

## 4. База Данных — Полная Схема {#4}

### 4.1. Таблицы и их назначение

| Таблица | Назначение |
| :--- | :--- |
| `users` | Покупатели (зарегистрированные через Mirror Bot). |
| `sellers` | Продавцы (зарегистрированные через Seller Bot). |
| `marketers` | Маркетологи. |
| `workers` | Воркеры. |
| `staff` | Сотрудники поддержки (support, moderator, finance, admin, auditor). |
| `mirror_bots` | Зарегистрированные экземпляры Mirror Bot. |
| `marketer_bot_links` | Привязка ботов-прокси к маркетологам. |
| `menu_categories` | Категории главного меню Mirror Bot. |
| `menu_items` | Пункты меню внутри категорий. |
| `products` | Все товары (In Stocks). |
| `product_files` | Файлы, прикреплённые к товарам. |
| `brute_bank_groups` | Группы Brute Bank (банк + атрибуты). |
| `brute_bank_items` | Отдельные строки Brute Bank. |
| `orders` | Все заказы покупателей. |
| `order_items` | Позиции в заказе. |
| `disputes` | Споры по заказам. |
| `reviews` | Оценки товаров и воркеров. |
| `tickets` | Тикеты поддержки. |
| `ticket_messages` | Сообщения внутри тикета. |
| `deposits` | Пополнения баланса. |
| `withdrawal_requests` | Заявки на вывод средств. |
| `transactions` | Все финансовые транзакции. |
| `coupons` | Купоны. |
| `coupon_uses` | История использования купонов. |
| `referrals` | Реферальные связи. |
| `loyalty_levels` | Уровни программы лояльности. |
| `service_prices` | Цены на все услуги. |
| `broadcast_messages` | Рассылки. |
| `ad_channels` | Рекламные каналы. |
| `ad_campaigns` | Рекламные кампании. |
| `automation_tasks` | Задачи Модуля Автоматизации. |
| `automation_accounts` | Аккаунты SearchBug. |
| `automation_proxies` | Прокси для воркеров. |
| `seller_teams` | Команды продавцов (помощники). |
| `audit_logs` | Неизменяемый лог всех действий сотрудников. |
| `pinned_orders` | Закреплённые сообщения о выполненных заказах. |
| `esim_tariffs` | Тарифы eSIM. |
| `preorders` | Предзаказы (Accounts: Proxy, AI). |

### 4.2. Ключевые модели

**`users`**

| Поле | Тип | Описание |
| :--- | :--- | :--- |
| `id` | UUID | Первичный ключ. |
| `telegram_id` | BIGINT UNIQUE | Telegram ID пользователя. |
| `username` | VARCHAR(64) | @username (может быть NULL). |
| `first_name` | VARCHAR(128) | Имя. |
| `language_code` | VARCHAR(8) | Язык интерфейса (en/ru/es/zh). |
| `mirror_bot_id` | UUID FK | Через какой Mirror Bot зарегистрировался. |
| `referrer_id` | UUID FK NULL | Кто пригласил (другой пользователь). |
| `marketer_id` | UUID FK NULL | Через какого маркетолога пришёл. |
| `balance` | DECIMAL(12,2) | Текущий баланс в USD. |
| `total_spent` | DECIMAL(12,2) | Суммарно потрачено (для программы лояльности). |
| `loyalty_level` | ENUM | bronze / silver / gold / platinum. |
| `is_banned` | BOOLEAN | Заблокирован ли пользователь. |
| `ban_reason` | TEXT NULL | Причина бана. |
| `created_at` | TIMESTAMPTZ | Дата регистрации. |
| `last_active_at` | TIMESTAMPTZ | Последняя активность. |

**`sellers`**

| Поле | Тип | Описание |
| :--- | :--- | :--- |
| `id` | UUID | Первичный ключ. |
| `telegram_id` | BIGINT UNIQUE | Telegram ID продавца. |
| `username` | VARCHAR(64) | @username. |
| `shop_name` | VARCHAR(128) | Название магазина. |
| `balance` | DECIMAL(12,2) | Текущий баланс. |
| `hold_balance` | DECIMAL(12,2) | Средства на холде (72ч после продажи). |
| `total_earned` | DECIMAL(12,2) | Суммарно заработано. |
| `deposit_paid` | BOOLEAN | Оплачен ли вступительный взнос $600. |
| `deposit_paid_at` | TIMESTAMPTZ NULL | Дата оплаты взноса. |
| `is_verified` | BOOLEAN | Прошёл ли модерацию. |
| `is_banned` | BOOLEAN | Заблокирован ли. |
| `commission_rate` | DECIMAL(5,4) | Индивидуальная комиссия (по умолчанию из `service_prices`). |
| `created_at` | TIMESTAMPTZ | Дата регистрации. |

**`orders`**

| Поле | Тип | Описание |
| :--- | :--- | :--- |
| `id` | UUID | Первичный ключ. |
| `trace_id` | VARCHAR(32) UNIQUE | Сквозной идентификатор для аудита. |
| `user_id` | UUID FK | Покупатель. |
| `seller_id` | UUID FK NULL | Продавец (NULL для Per Order). |
| `worker_id` | UUID FK NULL | Воркер (для Per Order). |
| `order_type` | ENUM | `in_stocks` / `per_order`. |
| `status` | ENUM | `pending` / `processing` / `completed` / `disputed` / `refunded`. |
| `total_amount` | DECIMAL(12,2) | Сумма заказа. |
| `commission_amount` | DECIMAL(12,2) | Комиссия системы. |
| `seller_amount` | DECIMAL(12,2) | Сумма продавцу. |
| `coupon_id` | UUID FK NULL | Применённый купон. |
| `discount_amount` | DECIMAL(12,2) | Размер скидки. |
| `pinned_message_id` | BIGINT NULL | ID закреплённого сообщения в Telegram. |
| `created_at` | TIMESTAMPTZ | Дата создания. |
| `completed_at` | TIMESTAMPTZ NULL | Дата выполнения. |

**`withdrawal_requests`**

| Поле | Тип | Описание |
| :--- | :--- | :--- |
| `id` | UUID | Первичный ключ. |
| `trace_id` | VARCHAR(32) UNIQUE | Сквозной идентификатор. |
| `requester_type` | ENUM | `seller` / `worker` / `marketer` / `owner`. |
| `requester_id` | UUID | ID запрашивающего. |
| `amount` | DECIMAL(12,2) | Сумма вывода. |
| `method` | ENUM | `btc` / `xmr` / `usdt_trc20`. |
| `address` | VARCHAR(256) | Адрес кошелька. |
| `status` | ENUM | `pending` / `approved` / `rejected` / `completed`. |
| `processed_by` | UUID FK NULL | Кто обработал (из `staff`). |
| `rejection_reason` | TEXT NULL | Причина отклонения. |
| `created_at` | TIMESTAMPTZ | Дата создания. |
| `processed_at` | TIMESTAMPTZ NULL | Дата обработки. |

**`coupons`**

| Поле | Тип | Описание |
| :--- | :--- | :--- |
| `id` | UUID | Первичный ключ. |
| `code` | VARCHAR(32) UNIQUE | Код купона (например, `SALE2026`). |
| `discount_type` | ENUM | `fixed` / `percent`. |
| `discount_value` | DECIMAL(10,2) | Размер скидки. |
| `min_order_amount` | DECIMAL(10,2) | Минимальная сумма заказа. |
| `max_uses` | INTEGER NULL | Лимит использований (NULL = безлимит). |
| `uses_count` | INTEGER | Текущее количество использований. |
| `is_one_per_user` | BOOLEAN | Один раз на пользователя. |
| `scope_type` | ENUM | `all` / `category` / `product`. |
| `scope_id` | UUID NULL | ID категории или товара. |
| `valid_from` | TIMESTAMPTZ | Начало действия. |
| `valid_until` | TIMESTAMPTZ NULL | Конец действия (NULL = бессрочно). |
| `is_active` | BOOLEAN | Активен ли купон. |
| `created_at` | TIMESTAMPTZ | Дата создания. |

**`automation_tasks`**

| Поле | Тип | Описание |
| :--- | :--- | :--- |
| `id` | UUID | Первичный ключ. |
| `order_id` | UUID FK | Связанный заказ. |
| `service_type` | ENUM | `credit_score` / `phone` / `address` / `email` / `people_search`. |
| `execution_type` | ENUM | `auto` / `manual`. |
| `status` | ENUM | `queued` / `processing` / `completed` / `failed` / `manual`. |
| `input_data` | JSONB | Входные данные для пробива. |
| `result_data` | JSONB NULL | Результат пробива. |
| `result_txt_url` | VARCHAR(512) NULL | URL файла .txt с результатом. |
| `result_csv_url` | VARCHAR(512) NULL | URL файла .csv с результатом. |
| `worker_id` | UUID FK NULL | Воркер (для ручного пути). |
| `account_id` | UUID FK NULL | Аккаунт SearchBug (для ручного пути). |
| `proxy_id` | UUID FK NULL | Прокси (для ручного пути). |
| `error_message` | TEXT NULL | Сообщение об ошибке. |
| `created_at` | TIMESTAMPTZ | Дата создания. |
| `completed_at` | TIMESTAMPTZ NULL | Дата завершения. |

---
## 5. Mirror Bot — Клиентский Бот {#5}

### 5.1. Регистрация и онбординг

**Триггер:** Пользователь нажимает `/start` (или переходит по реферальной ссылке `?start=ref_XXXXX` или по ссылке маркетолога `?start=mkt_XXXXX`).

**Флоу регистрации:**

```
/start
  ↓
Проверка: пользователь уже зарегистрирован?
  ├── Да → Показать главное меню
  └── Нет → Приветственное сообщение
              ↓
            Запрос языка (4 кнопки: 🇺🇸 English / 🇷🇺 Русский / 🇪🇸 Español / 🇨🇳 中文)
              ↓
            Принять правила (кнопка "✅ Принять и продолжить")
              ↓
            Создать запись в users
              ↓
            Записать referrer_id / marketer_id (если есть в параметрах /start)
              ↓
            Показать главное меню
```

**Приветственное сообщение (EN):**
```
👋 Welcome to Newlookup!

The largest marketplace for digital data.

Please select your language:
```

**Кнопки выбора языка:**
```
[ 🇺🇸 English ]  [ 🇷🇺 Русский ]
[ 🇪🇸 Español ]  [ 🇨🇳 中文    ]
```

**Сообщение с правилами (EN):**
```
📋 Terms of Service

By using this service you agree to our terms.
All purchases are final. No refunds except for disputes.
Misuse of the service will result in a permanent ban.

[ ✅ Accept & Continue ]
```

### 5.2. Главное меню

**Структура главного меню** (управляется через Admin Panel, порядок и состав настраиваются):

| Кнопка | Callback | Описание |
| :--- | :--- | :--- |
| 🔍 Search | `menu_search` | Поиск по каталогу. |
| 📊 Credit Reports | `menu_credit_reports` | Раздел Per Order: кредитные отчёты. |
| 🏦 Banks | `menu_banks` | Раздел In Stocks: банковские данные. |
| 💳 Cards | `menu_cards` | Раздел In Stocks: кредитные карты. |
| 📱 eSIM | `menu_esim` | Раздел: eSIM тарифы. |
| 🖥️ Accounts | `menu_accounts` | Раздел: Proxy, AI аккаунты (предзаказ). |
| 👤 Profile | `menu_profile` | Профиль пользователя. |
| 📦 My Orders | `menu_orders` | История заказов. |
| 💬 Support | `menu_support` | Поддержка. |

**Сообщение главного меню:**
```
🏪 Newlookup Marketplace

Balance: $0.00
Orders: 0

Select a category:
```

**Кнопки (2 в ряд, последняя строка — 3 кнопки):**
```
[ 🔍 Search        ]  [ 📊 Credit Reports ]
[ 🏦 Banks         ]  [ 💳 Cards          ]
[ 📱 eSIM          ]  [ 🖥️ Accounts       ]
[ 👤 Profile  ]  [ 📦 My Orders ]  [ 💬 Support ]
```

### 5.3. Профиль пользователя

**Сообщение профиля:**
```
👤 Your Profile

🆔 ID: 123456789
👤 Username: @johndoe
💰 Balance: $25.00
📦 Total orders: 12
💵 Total spent: $540.00
🔗 Referral link: t.me/NewlookupBot?start=ref_ABCDEF

[➕ Top Up Balance]  [🎟️ Apply Coupon]
[👥 Referrals]       [🌐 Language]
[🔙 Back]
```

**Кнопки профиля:**

| Кнопка | Callback | Действие |
| :--- | :--- | :--- |
| ➕ Top Up Balance | `profile_topup` | Открыть меню пополнения. |
| 🎟️ Apply Coupon | `profile_coupon` | Ввести код купона. |
| 👥 Referrals | `profile_referrals` | Статистика рефералов. |
| 🌐 Language | `profile_language` | Сменить язык интерфейса. |
| 🔙 Back | `menu_main` | Вернуться в главное меню. |

### 5.4. Пополнение баланса

**Сообщение выбора метода оплаты:**
```
💳 Top Up Balance

Select payment method:

[ ₿ Bitcoin (BTC) ]
[ 🔵 USDT TRC-20  ]
[ 🟣 Monero (XMR) ]
[ 🔙 Back         ]
```

**После выбора метода (пример BTC):**
```
₿ Bitcoin Payment

Send exactly:
0.00042 BTC

To address:
bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh

⏳ Waiting for payment...
Order expires in: 30:00

[🔄 Check Payment]  [❌ Cancel]
```

**Логика проверки:**
- Система автоматически проверяет оплату каждые 30 секунд через BTCPay API.
- При подтверждении оплаты — баланс пополняется мгновенно.
- Пользователю отправляется уведомление: `✅ Balance topped up: +$50.00. New balance: $75.00`.
- Реферер получает 4% автоматически: `💰 Referral bonus: +$2.00`.
- Маркетолог получает 8.5% автоматически.

### 5.5. Применение купона

**Флоу:**
```
Пользователь нажимает [🎟️ Apply Coupon]
  ↓
Бот: "Enter coupon code:"
  ↓
Пользователь вводит код
  ↓
Проверки:
  ├── Код не существует → "❌ Invalid coupon code."
  ├── Купон истёк → "❌ This coupon has expired."
  ├── Лимит использований исчерпан → "❌ This coupon is no longer available."
  ├── Уже использован (one_per_user=true) → "❌ You have already used this coupon."
  └── Всё ок → "✅ Coupon applied! You'll get X% off on your next order."
```

**Купон сохраняется в сессии пользователя** и применяется при следующем заказе автоматически.

### 5.6. Статистика рефералов

**Сообщение:**
```
👥 Your Referrals

Total referred: 5 users
Active (made deposit): 3 users
Total earned: $12.40

Your referral link:
t.me/NewlookupBot?start=ref_ABCDEF

[📋 Copy Link]  [🔙 Back]
```

### 5.7. Раздел Banks (In Stocks)

**Структура раздела Banks:**

```
Banks
  ├── Selfreg BA (Саморегистрированные аккаунты)
  ├── Logs BA (Логи банков)
  ├── Brute Bank (Данные AN:RN+INST)
  └── Enroll (Доступ к банковским порталам)
```

**Сообщение раздела Banks:**
```
🏦 Banks

Select subcategory:

[ 📝 Selfreg BA  ]  [ 📋 Logs BA    ]
[ 💥 Brute Bank  ]  [ 🔐 Enroll     ]
[ 🔙 Back        ]
```

#### 5.7.1. Selfreg BA — список товаров

**Сообщение списка:**
```
📝 Selfreg BA

Available: 24 items

Filters: [All Banks ▼] [All States ▼] [Sort: Price ▼]

━━━━━━━━━━━━━━━━━━━━
🏦 Chase Bank
💳 Checking | Balance: $2,450.00
📱 Phone: ✅ Renewable
📧 Email: ✅ Access
📍 State: CA
💰 Price: $150.00
[🛒 Buy Now]

━━━━━━━━━━━━━━━━━━━━
🏦 Bank of America
💳 Savings | Balance: $8,200.00
📱 Phone: ✅ Changeable
📧 Email: ✅ Changeable
📍 State: NY
💰 Price: $320.00
[🛒 Buy Now]

━━━━━━━━━━━━━━━━━━━━
[ ◀ Prev ]  Page 1/3  [ Next ▶ ]
[ 🔙 Back to Banks ]
```

**Фильтры (inline-кнопки):**

| Фильтр | Варианты |
| :--- | :--- |
| Bank | All Banks / Chase / Bank of America / Wells Fargo / ... |
| State | All States / CA / NY / TX / FL / ... |
| Sort | Price ↑ / Price ↓ / Balance ↑ / Balance ↓ / Newest |

#### 5.7.2. Карточка товара Selfreg BA

**После нажатия [🛒 Buy Now]:**
```
📝 Selfreg BA — Chase Bank

🏦 Bank: Chase Bank
💳 Account type: Checking
💰 Balance: $2,450.00
🌐 Online access: ✅ Yes
📱 Phone access: ✅ Yes
  └ Renewable: ✅ Yes
📧 Email access: ✅ Yes
  └ Changeable: ✅ Yes
📍 State: CA
📅 Registration date: 2024-08-15
⭐ Seller rating: 4.8/5 (124 reviews)

💰 Price: $150.00
🎟️ Coupon discount: -$4.50 (3%)
💳 Final price: $145.50

[✅ Confirm Purchase]  [🔙 Back]
```

**После нажатия [✅ Confirm Purchase]:**
```
Проверка баланса:
  ├── Баланс достаточен → Списать средства → Отправить данные товара → Закрепить сообщение
  └── Баланс недостаточен → "❌ Insufficient balance. Your balance: $25.00. Required: $145.50. [➕ Top Up]"
```

**Сообщение с данными товара (после успешной покупки):**
```
✅ Purchase Successful!

Order #ORD-2026-001234

🏦 Chase Bank — Checking
━━━━━━━━━━━━━━━━━━━━
[Данные аккаунта из зашифрованного файла]
━━━━━━━━━━━━━━━━━━━━

📅 Purchased: 12.03.2026 15:30

[⭐ Rate Purchase]  [⚠️ Open Dispute]
```

**Закреплённое сообщение (pin_message):**
```
📦 Order #ORD-2026-001234 — Completed
Chase Bank | Selfreg BA | $145.50
12.03.2026 15:30

[📄 View Details]  [⭐ Rate]  [⚠️ Dispute]
```

### 5.8. Раздел Cards (In Stocks)

**Структура:**
```
Cards
  ├── Selfreg CC (Саморегистрированные карты)
  └── CC (Карты от продавцов: with_fullz / zip_only / non_vbv)
```

**Сообщение раздела:**
```
💳 Cards

[ 📝 Selfreg CC  ]  [ 💳 CC (Dumps) ]
[ 🔙 Back        ]
```

#### 5.8.1. CC (Dumps) — выбор типа

```
💳 CC — Select Type

[ 🔐 With Fullz  ]  [ 📮 ZIP Only   ]
[ ⚡ Non-VBV     ]  [ 🔙 Back       ]
```

#### 5.8.2. CC — список карт

**Сообщение:**
```
💳 CC — With Fullz

Available: 156 cards

Filters: [All Banks ▼] [All Countries ▼]

━━━━━━━━━━━━━━━━━━━━
💳 VISA Classic
🏦 Chase Bank
🌍 US | State: CA
💰 Price: $25.00
[🛒 Buy]

━━━━━━━━━━━━━━━━━━━━
💳 Mastercard Gold
🏦 Citi Bank
🌍 US | State: NY
💰 Price: $35.00
[🛒 Buy]

[ ◀ Prev ]  Page 1/8  [ Next ▶ ]
[ 🔙 Back ]
```

### 5.9. Раздел Credit Reports (Per Order)

**Сообщение:**
```
📊 Credit Reports

Select service:

[ 📈 Credit Score     ]
[ 📋 Full Credit Report ]
[ 🔙 Back             ]
```

#### 5.9.1. Credit Score — флоу заказа

```
Пользователь выбирает [📈 Credit Score]
  ↓
Бот: "Enter the following information:"
  ↓
FSM шаг 1: "First Name:"
FSM шаг 2: "Last Name:"
FSM шаг 3: "Date of Birth (MM/DD/YYYY):"
FSM шаг 4: "SSN (XXX-XX-XXXX):"
FSM шаг 5: "Address:"
FSM шаг 6: "City:"
FSM шаг 7: "State (2 letters):"
FSM шаг 8: "ZIP Code:"
  ↓
Подтверждение:
"Please confirm the data:
Name: John Smith
DOB: 06/15/1985
SSN: ***-**-1234
Address: 123 Main St, New York, NY 10001

Price: $35.00
[✅ Confirm]  [✏️ Edit]  [❌ Cancel]"
  ↓
После подтверждения:
"⏳ Order #ORD-2026-001235 — Processing
Type: Credit Score
Expected time: ~5 minutes
Status updates automatically."
  ↓
Когда результат готов:
"✅ Order #ORD-2026-001235 — Completed
Credit Score: 742 (Good)
[📄 Download Full Report .txt]  [📊 Download .csv]
[⭐ Rate]  [⚠️ Dispute]"
```

### 5.10. Раздел eSIM

**Сообщение:**
```
📱 eSIM

Select a plan:

━━━━━━━━━━━━━━━━━━━━
🇺🇸 USA — 10GB / 30 days
📶 Unlimited calls & SMS
💰 Price: $25.00
[🛒 Buy]

━━━━━━━━━━━━━━━━━━━━
🌍 Global — 5GB / 15 days
📶 Data only
💰 Price: $18.00
[🛒 Buy]

[ 🔙 Back ]
```

**После покупки eSIM:**
```
✅ eSIM Purchased!

Order #ORD-2026-001236

Your eSIM will be delivered within 24 hours.
An administrator will send you the activation QR code.

[⚠️ Open Dispute]  [💬 Contact Support]
```

### 5.11. Раздел Accounts (Предзаказ)

**Сообщение:**
```
🖥️ Accounts

[ 🔒 Proxy Accounts ]  [ 🤖 AI Accounts ]
[ 🔙 Back           ]
```

**После выбора типа:**
```
🔒 Proxy Accounts — Pre-order

This is a pre-order service.
Your account will be delivered within 24-48 hours.

Select type:
[ 🌐 Residential ]  [ 🏢 Datacenter ]
[ 📱 Mobile      ]  [ 🔙 Back       ]
```

**После выбора:**
```
🌐 Residential Proxy Account

Provider: Brightdata
Duration: 1 month
Traffic: 10GB
Price: $45.00

[✅ Place Pre-order]  [🔙 Back]
```

### 5.12. Мои заказы

**Сообщение:**
```
📦 My Orders

Total: 12 orders

[ All ] [ In Stocks ] [ Per Order ] [ Disputed ]

━━━━━━━━━━━━━━━━━━━━
✅ #ORD-2026-001234
Chase Bank | Selfreg BA
$145.50 | 12.03.2026
[📄 Details]

━━━━━━━━━━━━━━━━━━━━
✅ #ORD-2026-001230
Credit Score
$35.00 | 10.03.2026
[📄 Details]

━━━━━━━━━━━━━━━━━━━━
⚠️ #ORD-2026-001225
CC With Fullz
$25.00 | 08.03.2026 | DISPUTED
[📄 Details]

[ ◀ Prev ]  Page 1/2  [ Next ▶ ]
[ 🔙 Back ]
```

### 5.13. Открытие спора

**Флоу:**
```
Пользователь нажимает [⚠️ Open Dispute] или [⚠️ Dispute] в закреплённом сообщении
  ↓
"Are you sure you want to open a dispute for order #ORD-2026-001234?
This will notify our moderation team.
[✅ Yes, Open Dispute]  [❌ Cancel]"
  ↓
FSM: "Describe the problem:"
  ↓
Пользователь вводит описание
  ↓
"✅ Dispute opened. Ticket #TKT-001234 created.
Our moderator will review your case within 24 hours.
[💬 View Ticket]  [🔙 Main Menu]"
  ↓
Уведомление в Support Bot роли Moderator:
"⚠️ New Dispute
Order: #ORD-2026-001234
Buyer: @johndoe
Seller: @seller_shop
Amount: $145.50
Reason: [текст пользователя]
[👁️ View Details]  [✅ Resolve for Buyer]  [❌ Resolve for Seller]"
```

### 5.14. Рейтинг и отзывы

**Флоу после выполнения заказа:**
```
"⭐ Rate your purchase

Order: Chase Bank | Selfreg BA
How would you rate this product?

[ ⭐ 1 ]  [ ⭐⭐ 2 ]  [ ⭐⭐⭐ 3 ]
[ ⭐⭐⭐⭐ 4 ]  [ ⭐⭐⭐⭐⭐ 5 ]
[ Skip ]"
  ↓
После выбора оценки:
"Leave a comment (optional):"
  ↓
"✅ Thank you for your review!"
```

**Лайк/Дизлайк (альтернативный быстрый рейтинг):**
```
[ 👍 Like ]  [ 👎 Dislike ]
```

### 5.15. Поддержка

**Сообщение:**
```
💬 Support

[ 📝 Create Ticket ]  [ 📋 My Tickets ]
[ 🔙 Back          ]
```

**Создание тикета:**
```
FSM шаг 1: "Describe your issue:"
  ↓
Пользователь вводит текст
  ↓
"✅ Ticket #TKT-001235 created.
We'll respond within 24 hours.
[💬 View Ticket]  [🔙 Main Menu]"
```

**Тикет перенаправляется в Support Bot** роли `support`.

---

## 6. Seller Bot — Бот Продавца {#6}

### 6.1. Регистрация продавца

**Флоу:**
```
/start
  ↓
Проверка: продавец уже зарегистрирован?
  ├── Да + deposit_paid=true → Главное меню продавца
  ├── Да + deposit_paid=false → Сообщение об оплате депозита
  └── Нет → Регистрация
              ↓
            "Welcome to Newlookup Seller Bot!
            To become a seller, you need to pay a one-time registration fee of $600.
            This fee ensures quality and trust in our marketplace.
            [💳 Pay $600 Registration Fee]  [❌ Cancel]"
              ↓
            Генерация платёжного адреса (BTC/USDT/XMR)
              ↓
            После оплаты → Заявка на модерацию в Support Bot
              ↓
            Модератор одобряет → Продавец получает уведомление
              ↓
            Главное меню продавца
```

### 6.2. Главное меню продавца

**Сообщение:**
```
🏪 Seller Dashboard

Shop: My Shop Name
Balance: $1,250.00 | Hold: $320.00
Total sales: 47 | Rating: 4.9/5

[ 📦 My Products  ]  [ ➕ Add Product ]
[ 📊 Statistics   ]  [ 💰 Withdraw    ]
[ 👥 My Team      ]  [ ⚙️ Settings    ]
[ 💬 Chat         ]  [ 🔙 Main Menu   ]
```

### 6.3. Добавление товара — выбор категории

**Сообщение:**
```
➕ Add Product

Select product category:

[ 📝 Selfreg BA   ]  [ 💳 Selfreg CC  ]
[ 📋 Logs BA      ]  [ 💥 Brute Bank  ]
[ 💳 CC Dumps     ]  [ 📱 eSIM        ]
[ 🖥️ Accounts    ]  [ 🔐 Enroll      ]
[ 🔙 Back         ]
```

### 6.4. FSM-конфигуратор: Selfreg BA (14 шагов)

```
Шаг 1/14: "Enter bank name:"
  → Пользователь вводит: "Chase Bank"

Шаг 2/14: "Select account type:"
  [ Checking ] [ Savings ] [ ✏️ Enter custom type ]
  → Если "Enter custom type": "Enter account type:" → вводит текст → уходит на модерацию

Шаг 3/14: "Enter account balance (USD):"
  → Пользователь вводит: "2450.00"
  → Валидация: число > 0

Шаг 4/14: "Is there online access?"
  [ ✅ Yes ] [ ❌ No ]

Шаг 5/14: "Is there phone access?"
  [ ✅ Yes ] [ ❌ No ]

Шаг 6/14 (если шаг 5 = Yes): "Can the phone number be renewed?"
  [ ✅ Yes ] [ ❌ No ]

Шаг 6/14 (если шаг 5 = No): "Can the phone number be changed?"
  [ ✅ Yes ] [ ❌ No ]

Шаг 7/14: "Is there email access?"
  [ ✅ Yes ] [ ❌ No ]

Шаг 8/14 (если шаг 7 = No): "Can the email be changed?"
  [ ✅ Yes ] [ ❌ No ]

Шаг 9/14: "Is email change allowed in account settings?"
  [ ✅ Yes ] [ ❌ No ]

Шаг 10/14: "Enter state (e.g. CA, NY, TX):"
  → Пользователь вводит: "CA"

Шаг 11/14: "Enter account registration date (MM/DD/YYYY):"
  → Пользователь вводит: "08/15/2024"
  → Валидация: корректная дата

Шаг 12/14: "Auto-delete / reminder after how many days? (0 = disabled):"
  → Пользователь вводит: "30"

Шаг 13/14: "Enter price (USD):"
  → Пользователь вводит: "150.00"

Шаг 14/14: "Upload product file (txt/pdf/zip) or skip:"
  [ 📎 Upload File ] [ ⏭️ Skip ]

Подтверждение:
"Review your product:

🏦 Chase Bank
💳 Checking | Balance: $2,450.00
🌐 Online: ✅ | 📱 Phone: ✅ Renewable
📧 Email: ✅ | Changeable: ✅
📍 CA | 📅 08/15/2024
⏰ Auto-delete: 30 days
💰 Price: $150.00

[✅ Publish]  [✏️ Edit]  [❌ Cancel]"

После [✅ Publish]:
→ Товар уходит на модерацию в Support Bot
→ "✅ Product submitted for review. You'll be notified when it's approved."
```

### 6.5. FSM-конфигуратор: Selfreg CC (17 шагов)

```
Шаг 1/17: "Enter bank/issuer name:"
Шаг 2/17: "Enter card name (e.g. Chase Sapphire):"
Шаг 3/17: "Enter credit limit (USD):"
Шаг 4/17: "Does this account have a Virtual Card (VCC)?"
  [ ✅ Yes ] [ ❌ No ]
Шаг 5/17 (если шаг 4 = Yes): "Enter VCC limit (USD):"
Шаг 6/17: "Enter state:"
Шаг 7/17: "Enter ZIP code:"
Шаг 8/17: "Enter billing address:"
Шаг 9/17: "Enter registration date (MM/DD/YYYY):"
Шаг 10/17: "Is there phone access?"
  [ ✅ Yes ] [ ❌ No ]
Шаг 11/17 (если шаг 10 = Yes): "Can the phone be renewed?"
  [ ✅ Yes ] [ ❌ No ]
Шаг 11/17 (если шаг 10 = No): "Can the phone be changed?"
  [ ✅ Yes ] [ ❌ No ]
Шаг 12/17: "Is there email access?"
  [ ✅ Yes ] [ ❌ No ]
Шаг 13/17 (если шаг 12 = No): "Can the email be changed?"
  [ ✅ Yes ] [ ❌ No ]
Шаг 14/17: "Is email change allowed in account settings?"
  [ ✅ Yes ] [ ❌ No ]
Шаг 15/17: "Auto-delete / reminder after how many days? (0 = disabled):"
Шаг 16/17: "Enter price (USD):"
Шаг 17/17: "Upload product file or skip:"
  [ 📎 Upload File ] [ ⏭️ Skip ]
```

### 6.6. FSM-конфигуратор: Logs BA

```
Шаг 1: "Enter the banks in this log (one per line):
Format: BankName | AccountType | Balance
Example:
Chase | Checking | $4,064.18
Chase | CC | $17,159.00
[✅ Done entering banks]"

Шаг 2: "Total balance (auto-calculated: $21,223.18). Confirm or enter manually:"
  [ ✅ Use Auto ($21,223.18) ] [ ✏️ Enter Manually ]

Шаг 3: "Select email type:"
  [ gmail ] [ aol ] [ yahoo ] [ outlook ] [ live ] [ spectrum ] [ other ]

Шаг 4: "Is the email valid?"
  [ ✅ Valid ] [ ❌ Not Valid ]

Шаг 5: "Is there CVV?"
  [ ✅ Yes ] [ ❌ No ]

Шаг 6: "Is Balance Transfer available?"
  [ ✅ Yes ] [ ❌ No ]

Шаг 7: "Are there promo offers?"
  [ ✅ Yes ] [ ❌ No ]

Шаг 8: "Is Zelle enrolled?"
  [ ✅ Yes ] [ ❌ No ]

Шаг 9: "Is Wire Transfer available?"
  [ ✅ Yes ] [ ❌ No ]

Шаг 10: "Is SafePass unlocked?"
  [ ✅ Yes ] [ ❌ No ]

Шаг 11: "Is there an investment account?"
  [ ✅ Yes ] [ ❌ No ]

Шаг 12: "Is there a credit line?"
  [ ✅ Yes ] [ ❌ No ]

Шаг 13: "Are there cookies?"
  [ ✅ Yes ] [ ❌ No ]

Шаг 14: "Is there a screenshot?"
  [ ✅ Yes ] [ ❌ No ]

Шаг 15: "Enter price (USD):"

Шаг 16: "Upload log file:"
  [ 📎 Upload File ] [ ⏭️ Skip ]

Автоматически генерируемая карточка:
"🏦 Chase
💳 Checking - $4,064.18
💳 CC avb - $17,159.00
‼️ there is CVV
📨 Mail: aol valid
🪙 Price: $700"
```

### 6.7. FSM-конфигуратор: Brute Bank

```
Шаг 1: "Select bank group or create new:"
  [ Список существующих групп ] [ ➕ Create New Group ]

Если "Create New Group":
  Шаг 1a: "Enter bank name:"
  Шаг 1b: "Select attributes (multiple choice):"
    [ AN ] [ RN ] [ NAME ] [ ADDRESS ] [ CITY ] [ ZIP ] [ ONLINE ACCESS ]
  Шаг 1c: "Select integrations (multiple choice):"
    [ YODLEE ] [ FINICITY ] [ PLAID ] [ MX ] [ AKOYA ] [ ➕ Add custom ]
  Шаг 1d: "Enter price per item (USD):"

Шаг 2: "Upload .txt file (one account per line):"
  [ 📎 Upload File ]

После загрузки:
"✅ File processed.
Lines: 250
Valid: 247
Invalid: 3 (shown below)

[✅ Publish 247 items]  [❌ Cancel]"
```

### 6.8. FSM-конфигуратор: CC Dumps

```
Шаг 1: "Select card type:"
  [ 🔐 With Fullz ] [ 📮 ZIP Only ] [ ⚡ Non-VBV ]

Шаг 2: "Upload .txt file:"
  Format reminder shown based on selected type:
  - With Fullz: card;exp_month;exp_year;cvv;zip;name;address;ssn;dob;phone
  - ZIP Only: card;exp_month;exp_year;cvv;zip
  - Non-VBV: card;exp_month;exp_year;cvv

  [ 📎 Upload File ]

Шаг 3: "Enter price per card (USD):"

После загрузки:
"✅ BIN check complete.
Total cards: 500
Valid format: 498
BIN verified: 485
Invalid: 15

[✅ Publish 485 cards]  [❌ Cancel]"
```

### 6.9. Статистика продавца

**Сообщение:**
```
📊 Statistics

Period: [ Today ] [ Week ] [ Month ] [ All Time ]

💰 Revenue: $3,450.00
📦 Orders: 47
⭐ Rating: 4.9/5 (38 reviews)
🔄 Active products: 24
📈 Conversion: 12.4%

Top products:
1. Chase Selfreg BA — 12 sales
2. Logs BA (Chase+BoA) — 8 sales
3. CC With Fullz — 7 sales

[📊 Full Analytics in Mini App]
[🔙 Back]
```

### 6.10. Вывод средств

**Сообщение:**
```
💰 Withdraw Funds

Available: $1,250.00
On hold: $320.00 (available in 48h)

Select method:
[ ₿ Bitcoin (BTC)  ]
[ 🔵 USDT TRC-20   ]
[ 🟣 Monero (XMR)  ]
[ 🔙 Back          ]
```

**После выбора метода:**
```
₿ Withdraw via Bitcoin

Enter amount (min $50.00):
```

**После ввода суммы:**
```
Enter your BTC address:
```

**Подтверждение:**
```
Confirm withdrawal:

Amount: $500.00
Method: Bitcoin
Address: bc1q...

[✅ Confirm]  [❌ Cancel]
```

**После подтверждения:**
```
✅ Withdrawal request #WDR-001234 submitted.
Amount: $500.00
Method: Bitcoin
Status: Pending review

You'll be notified when it's processed.
```

### 6.11. Управление командой

**Сообщение:**
```
👥 My Team

Members: 2

━━━━━━━━━━━━━━━━━━━━
👤 @uploader_john
Role: UPLOADER
Categories: Selfreg BA, Logs BA
Actions: 47 uploads
[✏️ Edit]  [🗑️ Remove]

━━━━━━━━━━━━━━━━━━━━
👤 @support_mary
Role: SUPPORT
Tickets handled: 12
[✏️ Edit]  [🗑️ Remove]

[➕ Add Member]  [🔙 Back]
```

**Добавление члена команды:**
```
"Enter Telegram ID or @username of the new team member:"
  ↓
"Select role:"
  [ 📦 UPLOADER ] [ 💬 SUPPORT ]
  ↓
Если UPLOADER:
"Select allowed categories (multiple choice):"
  [ Selfreg BA ] [ Selfreg CC ] [ Logs BA ] [ Brute Bank ] [ CC ] [ eSIM ] [ Accounts ] [ Enroll ]
  [ ✅ Done ]
  ↓
"✅ @username added to your team as UPLOADER."
```

---
## 7. Seller Mini App — Веб-приложение Продавца {#7}

### 7.1. Запуск Mini App

Продавец нажимает кнопку **[📊 Open Mini App]** в Seller Bot. Открывается Telegram Mini App с полноценным веб-интерфейсом.

### 7.2. Раздел: Дашборд

**Метрики (карточки вверху):**

| Карточка | Данные |
| :--- | :--- |
| Revenue Today | $450.00 (+12% vs yesterday) |
| Revenue Month | $3,450.00 (+8% vs last month) |
| Active Products | 24 |
| Pending Orders | 2 |

**График выручки:** Линейный график за последние 30 дней.

**Топ товаров:** Таблица с колонками: Товар / Продаж / Выручка / Конверсия.

### 7.3. Раздел: Товары

**Таблица товаров:**

| Колонка | Описание |
| :--- | :--- |
| Название | Банк + тип товара. |
| Категория | Selfreg BA / Logs BA / и т.д. |
| Цена | В USD. |
| Статус | Active / Pending / Rejected / Sold. |
| Продаж | Количество. |
| Создан | Дата. |
| Действия | Редактировать / Удалить / Деактивировать. |

**Фильтры:** По категории, статусу, дате.

**Кнопка:** [➕ Add Product] — открывает форму добавления (аналог FSM из Seller Bot, но в веб-интерфейсе).

### 7.4. Раздел: Заказы

**Таблица заказов:**

| Колонка | Описание |
| :--- | :--- |
| ID | Номер заказа. |
| Покупатель | @username. |
| Товар | Название. |
| Сумма | В USD. |
| Комиссия | Комиссия системы. |
| Статус | Completed / Disputed / Refunded. |
| Дата | Дата и время. |

**Детали заказа (при клике):** Полная информация + история статусов.

### 7.5. Раздел: Финансы

**Блоки:**

- **Баланс:** Доступно / На холде / Всего заработано.
- **История транзакций:** Таблица с фильтрами по типу (продажа / вывод / комиссия) и периоду.
- **Заявки на вывод:** Список с статусами.
- **Кнопка:** [💰 Request Withdrawal] — форма вывода.

### 7.6. Раздел: Аналитика

- **Воронка продаж:** Просмотры → Клики → Покупки.
- **Когортный анализ:** Повторные покупки по неделям.
- **Топ категорий:** Круговая диаграмма.
- **Средний чек:** По категориям.
- **Экспорт:** [📥 Export CSV].

### 7.7. Раздел: Настройки

- Название магазина.
- Описание магазина.
- Уведомления (включить/выключить по типам).
- Управление командой (аналог раздела в Seller Bot).

---

## 8. Marketer Bot — Бот Маркетолога {#8}

### 8.1. Регистрация маркетолога

**Флоу:**
```
/start
  ↓
Проверка: маркетолог уже зарегистрирован?
  ├── Да → Главное меню
  └── Нет → "Welcome to Newlookup Affiliate Program!
             Earn 8.5% from every deposit of users you bring.
             [✅ Register as Marketer]"
              ↓
            Создать запись в marketers
              ↓
            Главное меню маркетолога
```

### 8.2. Главное меню маркетолога

**Сообщение:**
```
📣 Marketer Dashboard

Balance: $340.00
Total earned: $1,240.00
Total referrals: 48
Active users: 31

[ 🤖 My Bots      ]  [ 📊 Statistics  ]
[ 💰 Withdraw     ]  [ ➕ Create Bot  ]
[ ⚙️ Settings     ]  [ 🔙 Main Menu   ]
```

### 8.3. Управление ботами-прокси

**Концепция:** Маркетолог создаёт собственный Telegram-бот (через @BotFather), получает токен и привязывает его к системе. Этот бот становится зеркалом Mirror Bot — пользователи, пришедшие через него, автоматически привязываются к маркетологу.

**Сообщение раздела "My Bots":**
```
🤖 My Bots

Active bots: 2

━━━━━━━━━━━━━━━━━━━━
🤖 @MyShopBot
Status: ✅ Active
Users: 234
Revenue generated: $4,560.00
Commission earned: $387.60
[⚙️ Settings]  [🔗 Invite Link]  [🗑️ Remove]

━━━━━━━━━━━━━━━━━━━━
🤖 @DataMarketBot
Status: ✅ Active
Users: 89
Revenue generated: $1,230.00
Commission earned: $104.55
[⚙️ Settings]  [🔗 Invite Link]  [🗑️ Remove]

[➕ Add New Bot]  [🔙 Back]
```

**Добавление нового бота:**
```
"To add a new bot:
1. Create a bot via @BotFather
2. Copy the bot token
3. Paste it below

Enter bot token:"
  ↓
Валидация токена (запрос к Telegram API)
  ↓
"✅ Bot @YourBotName connected successfully!
Your bot is now a mirror of Newlookup.
Users who register through your bot will be linked to you.

Share the bot's link `t.me/YourBotName` to invite users."
```

**Настройки бота:**
```
⚙️ Bot Settings — @MyShopBot

Bot name: My Shop Bot
Welcome message: [Edit]
Custom menu items: [Edit]
Status: [ ✅ Active / ❌ Pause ]

[💾 Save]  [🔙 Back]
```

### 8.4. Статистика маркетолога

**Сообщение:**
```
📊 Statistics

Period: [ Today ] [ Week ] [ Month ] [ All Time ]

👥 New registrations: 12
💰 Deposits by referrals: $1,450.00
💵 Your commission (8.5%): $123.25
📈 ARPU: $46.77
🔄 Conversion (reg → deposit): 64.6%

Top bots:
1. @MyShopBot — $387.60 earned
2. @DataMarketBot — $104.55 earned

[🔙 Back]
```

### 8.5. Антифрод система

**Правила:**

| Правило | Порог | Действие |
| :--- | :--- | :--- |
| Слишком много пополнений сразу | >30% рефералов пополняют в первые 24ч | Временная заморозка, уведомление Admin. |
| Аффилированные аккаунты | >90% рефералов с одного IP | Бан маркетолога, заморозка выплат. |
| Подозрительные паттерны | ИИ-анализ поведения | Флаг для ручной проверки. |

### 8.6. Вывод средств маркетолога

Аналогичен выводу продавца (разделы BTC/USDT/XMR, минимум $50, заявка в Support Bot роли Finance).

---

## 9. Support Bot — Бот Поддержки {#9}

### 9.1. Главное меню Support Bot

**Сообщение (зависит от роли):**

Для роли `support`:
```
💬 Support Panel

[ 📋 New Tickets (5) ]  [ 📁 My Tickets    ]
[ 🔙 Main Menu       ]
```

Для роли `moderator`:
```
🔍 Moderation Panel

[ ⚠️ Disputes (3)    ]  [ 📦 Products (7)  ]
[ 👤 Users           ]  [ 🔙 Main Menu     ]
```

Для роли `finance`:
```
💰 Finance Panel

[ 💸 Withdrawals (4) ]  [ 📊 Transactions  ]
[ 🔙 Main Menu       ]
```

Для роли `admin`:
```
⚙️ Admin Panel

[ 📋 Tickets         ]  [ ⚠️ Disputes      ]
[ 📦 Products        ]  [ 💸 Withdrawals   ]
[ 👤 Users           ]  [ 📢 Broadcasts    ]
[ 🔙 Main Menu       ]
```

### 9.2. Флоу: Обработка тикета поддержки

**Уведомление о новом тикете (роль `support`):**
```
📋 New Ticket #TKT-001235

From: @johndoe (ID: 123456789)
Mirror Bot: @NewlookupBot
Message: "I can't top up my balance, the payment page doesn't load."
Created: 12.03.2026 15:45

[💬 Reply]  [✅ Close]  [➡️ Escalate to Moderator]
```

**После нажатия [💬 Reply]:**
```
"Enter your reply:"
  ↓
Сотрудник вводит текст
  ↓
Сообщение отправляется пользователю в Mirror Bot:
"💬 Support reply to your ticket #TKT-001235:
[текст ответа]
[💬 Reply]  [✅ Close Ticket]"
```

**SLA-таймер:** Если тикет не обработан в течение 4 часов — уведомление роли `admin`: `⚠️ SLA breach: Ticket #TKT-001235 unattended for 4 hours.`

### 9.3. Флоу: Разрешение спора

**Уведомление о новом споре (роль `moderator`):**
```
⚠️ New Dispute #DSP-001234

Order: #ORD-2026-001234
Buyer: @johndoe | Seller: @seller_shop
Amount: $145.50
Product: Chase Bank | Selfreg BA
Buyer's reason: "Account credentials don't work"

[👁️ View Full Order]  [💬 Contact Buyer]  [💬 Contact Seller]
[✅ Refund Buyer]  [❌ Keep with Seller]  [⚖️ Split]
```

**После нажатия [✅ Refund Buyer]:**
```
"Confirm refund of $145.50 to @johndoe?
[✅ Confirm Refund]  [❌ Cancel]"
  ↓
Подтверждение → Средства возвращаются на баланс покупателя
→ Продавец получает уведомление: "⚠️ Dispute resolved in buyer's favor. $145.50 returned."
→ Покупатель получает: "✅ Dispute resolved. $145.50 returned to your balance."
→ Действие логируется в audit_logs
```

### 9.4. Флоу: Модерация товара

**Уведомление о новом товаре (роль `moderator`):**
```
📦 New Product for Review

Seller: @seller_shop
Category: Selfreg BA
Product details:
🏦 Chase Bank
💳 Checking | Balance: $2,450.00
🌐 Online: ✅ | 📱 Phone: ✅ Renewable
📧 Email: ✅ | State: CA
💰 Price: $150.00

[✅ Approve]  [❌ Reject]  [✏️ Request Edit]
```

**После [❌ Reject]:**
```
"Enter rejection reason:"
  ↓
Продавец получает: "❌ Your product was rejected.
Reason: [текст причины]
Please fix and resubmit."
```

### 9.5. Флоу: Одобрение вывода средств

**Уведомление (роль `finance`):**
```
💸 Withdrawal Request #WDR-001234

From: @seller_shop (Seller)
Amount: $500.00
Method: Bitcoin
Address: bc1q...xyz
Current balance: $1,250.00
Previous withdrawals: 3 (total $1,200.00)
Last withdrawal: 05.03.2026

[✅ Approve]  [❌ Reject]
```

**После [✅ Approve]:**
```
"Confirm sending $500.00 BTC to bc1q...xyz?
[✅ Confirm]  [❌ Cancel]"
  ↓
Средства отправляются (через BTCPay или вручную)
→ Продавец получает: "✅ Withdrawal #WDR-001234 processed. $500.00 BTC sent."
→ Действие логируется в audit_logs
```

---

## 10. Worker Bot — Бот Воркера {#10}

### 10.1. Главное меню воркера

**Сообщение:**
```
🔧 Worker Panel

Balance: $85.00
Completed orders: 23
Rating: 4.7/5
Status: [ ✅ Online ] [ ⏸️ Pause ]

[ 📋 New Orders (2) ]  [ 📁 My Orders    ]
[ 💰 Withdraw       ]  [ 📊 Statistics   ]
[ 🔙 Main Menu      ]
```

### 10.2. Флоу выполнения заказа Per Order

**Уведомление о новом заказе:**
```
📋 New Order #ORD-2026-001235

Type: Credit Score
Priority: Normal
Expected time: 5 min
Payment: $35.00 → Your share: $28.00 (80%)

Customer data:
Name: John Smith
DOB: 06/15/1985
SSN: ***-**-1234
Address: 123 Main St, New York, NY 10001

[✅ Accept]  [❌ Decline]  [⏰ In 10 min]
```

**После [✅ Accept]:**
```
"✅ Order accepted. Customer notified.
You have 30 minutes to complete this order.

[📤 Submit Result]  [💬 Ask Customer]  [⚠️ Report Issue]"
```

**После [📤 Submit Result]:**
```
"Upload result file (.txt or .csv):"
  [ 📎 Upload File ]
  ↓
"✅ Result submitted. Customer notified.
Payment: +$28.00 added to your balance."
```

### 10.3. Статистика воркера

```
📊 Statistics

Period: [ Today ] [ Week ] [ Month ]

✅ Completed: 23
❌ Declined: 2
⏱️ Avg completion time: 8 min
⭐ Rating: 4.7/5
💰 Earned: $644.00
```

---

## 11. Main Bot — Бот Владельца {#11}

### 11.1. Главное меню владельца

**Сообщение:**
```
👑 Owner Dashboard

System status: ✅ Online
Active bots: 3 mirrors
Total users: 1,247
Active sellers: 8

[ 📊 Statistics    ]  [ 🤖 Manage Bots  ]
[ 📢 Broadcast     ]  [ 💰 Finances     ]
[ ⚙️ System        ]  [ 🔙 Main Menu    ]
```

### 11.2. Управление зеркалами

**Сообщение:**
```
🤖 Mirror Bots

Active: 3

━━━━━━━━━━━━━━━━━━━━
🤖 @NewlookupBot (Main)
Users: 892 | Revenue: $12,450.00
Status: ✅ Online
[📊 Stats]  [⚙️ Settings]

━━━━━━━━━━━━━━━━━━━━
🤖 @NLShopBot
Users: 234 | Revenue: $3,210.00
Status: ✅ Online
[📊 Stats]  [⚙️ Settings]  [🗑️ Remove]

[➕ Add Mirror Bot]  [🔙 Back]
```

**Добавление зеркала:**
```
"Enter the token of the new Mirror Bot:"
  ↓
Валидация токена
  ↓
"✅ Mirror Bot @NewBotName added successfully!"
```

### 11.3. Глобальная рассылка

```
"Select target audience:"
  [ 👥 All Users ] [ 🇺🇸 English ] [ 🇷🇺 Russian ] [ 🇪🇸 Spanish ] [ 🇨🇳 Chinese ]
  ↓
"Enter message text:"
  ↓
"Add button? (optional):"
  [ ✅ Yes ] [ ❌ No ]
  ↓
Если Yes: "Enter button text:" → "Enter button URL or bot command:"
  ↓
"Preview:
[текст сообщения]
[кнопка]

Send to: 1,247 users
[✅ Send Now]  [⏰ Schedule]  [❌ Cancel]"
```

### 11.4. Финансовый обзор

```
💰 Financial Overview

Total revenue: $45,230.00
Platform commission: $6,784.50
Seller payouts: $38,445.50
Pending withdrawals: $2,100.00

Payment gateways:
₿ BTCPay balance: $1,240.00
💵 Helecat balance: $890.00

[💸 Request Withdrawal]  [📊 Full Report]
```

---

## 12. Admin Panel — Веб-панель Управления (v17)

**Философия:** Admin Panel — это центр управления всей системой. Она должна быть быстрой, информативной и отказоустойчивой. Интерфейс должен минимизировать количество кликов для выполнения ключевых действий и предоставлять максимум данных на одном экране.

---

### 12.1. Дизайн Admin Panel — Compact Dark (Стиль DaisySMS)

**Концепция:** Максимальная информационная плотность, тёмная тема, отсутствие лишних отступов. Создан для опытных администраторов и модераторов, которые ценят скорость и эффективность.

*   **Цветовая схема:** Тёмно-серая (#1a1a1a), акцентный синий (#007bff), белый/светло-серый текст.
*   **Шрифты:** Inter, 13px для основного текста, 12px для таблиц.
*   **Ключевые особенности:**
    *   Никаких пустых пространств. Каждый пиксель используется.
    *   Таблицы с виртуальной прокруткой для мгновенной загрузки тысяч строк.
    *   Боковое меню — иконки, которые расширяются при наведении.
    *   Все действия (бан, редактирование, просмотр) — иконки в строке таблицы.

**Визуальный макет (текстовый):**

```
[Newlookup Admin] [Dashboard] [CRM] [Catalog] [Finance] [Moderation] [Broadcasts] [Settings] | [User: admin] [Logout]
---------------------------------------------------------------------------------------------------------------------
CRM / Users / Search: [__________] [Filter]                                                    [+ Add User]

| ID   | User      | Roles    | Balance | Status  | Last Seen  | Actions         |
|------|-----------|----------|---------|---------|------------|-----------------|
| 1254 | @testuser | seller   | $150.50 | Active  | 2m ago     | [👁] [✏️] [💬] [🚫] |
| 1253 | @johndoe  | buyer    | $25.00  | Active  | 15m ago    | [👁] [✏️] [💬] [🚫] |
| 1252 | @spammer  | buyer    | $0.00   | Banned  | 1h ago     | [👁] [✏️] [💬] [✅] |
... (еще 100 строк)

[Page: 1 of 125] [<<] [<] [>] [>>]
```

### 12.2. Детализация логики разделов Admin Panel

#### 12.2.1. Дашборд
*   **Виджеты:** Ключевые метрики в реальном времени (Онлайн пользователей, Новых за 24ч, Продаж за 24ч, Сумма продаж за 24ч, Активных споров, Товаров на модерации).
*   **Графики:** График продаж за последние 30 дней. График регистраций.
*   **Доступ:** Все роли видят дашборд, но состав виджетов может меняться в зависимости от роли (например, `finance` видит виджет "Сумма запросов на вывод").

#### 12.2.2. CRM (Управление пользователями)
*   **360° Профиль:** Как описано в v16, но с добавлением логов изменения цен (если менял `support`) и отправленных рассылок (если делал `moderator`).
*   **Действия:**
    *   `support`: Может менять цены товаров прямо из карточки пользователя, если он продавец.
    *   `moderator`: Может банить/разбанивать, отправлять личные сообщения.
    *   `admin`/`owner`: Полный набор действий.

#### 12.2.3. Финансы (Новый раздел)
*   **Доступ:** `support` (read-only), `finance`, `admin`, `owner`.
*   **Вкладка "Пополнения":** Таблица всех успешных депозитов из `deposits`. Фильтры по дате, пользователю, методу.
*   **Вкладка "Транзакции":** Таблица всех записей из `transactions`. Мощные фильтры: по типу, по сумме, по пользователю. Позволяет отследить любой денежный поток.
*   **Вкладка "Выводы":** Для `finance`, `admin`, `owner`. Таблица из `withdrawal_requests`. Кнопки [Approve] / [Reject] для каждой заявки. При нажатии [Reject] появляется поле для ввода причины.

#### 12.2.4. Рассылки
*   **Доступ:** `moderator`, `admin`, `owner`.
*   **Интерфейс:**
    1.  Поле для ввода текста сообщения.
    2.  Кнопка для загрузки медиа.
    3.  Выбор аудитории (чекбоксы: all, buyers, sellers, marketers) + кнопка [Custom Segment] для открытия фильтров CRM.
    4.  Toggle "Закрепить сообщение".
    5.  Кнопки [Send Now] и [Schedule].
*   **Статистика:** `moderator` видит статистику только своих рассылок. `admin` и `owner` видят все.
| People Search (Manual) | ✅ Enabled | Toggle |

**Статус сервиса:** Automation Module: ✅ Online | Queue: 3 tasks.

**Очередь задач:** Таблица активных задач с колонками: ID / Тип / Статус / Воркер / Создан / Действия.

**Аккаунты SearchBug:**

Таблица: ID / Email / Статус (Active/Banned) / Использований / Добавлен / Действия (Деактивировать / Удалить).

Кнопка: [➕ Add Account].

**Воркеры CRM:**

Таблица: @username / Статус (Online/Offline) / Задач выполнено / Рейтинг / Действия.

---

## 13. Модуль Автоматизации Пробива {#13}

### 13.1. Архитектура

```
Newlookup Bot
    │
    │ POST /tasks
    ▼
Automation API (FastAPI, порт 8001)
    │
    ├── automation_tasks (PostgreSQL)
    │
    ├── Автоматический путь (Celery Worker)
    │       ├── Credit Score → csbot.service (193.221.200.87)
    │       ├── Phone → Numverify API
    │       ├── Address → Smarty API
    │       └── Email → EmailRep API
    │
    └── Ручной путь (CRM)
            ├── People Search → SearchBug (через браузер + прокси)
            └── Воркер вносит результат через CRM-интерфейс
```

### 13.2. API эндпоинты

| Метод | Путь | Описание |
| :--- | :--- | :--- |
| POST | `/tasks` | Создать задачу. |
| GET | `/tasks/{id}` | Получить статус и результат. |
| GET | `/tasks` | Список задач (для Admin Panel). |
| POST | `/tasks/{id}/result` | Воркер вносит результат. |
| GET | `/workers` | Список воркеров CRM. |
| GET | `/accounts` | Список аккаунтов SearchBug. |
| POST | `/accounts/{id}/ban` | Пометить аккаунт как забаненный. |
| GET | `/health` | Проверка состояния сервиса. |

### 13.3. Статусы задачи

| Статус | Описание |
| :--- | :--- |
| `queued` | Задача в очереди Celery. |
| `processing` | Задача выполняется. |
| `completed` | Результат получен. |
| `failed` | Ошибка выполнения. |
| `manual` | Ожидает ручного воркера. |

### 13.4. Сообщение пользователю "В работе"

```
⏳ Order #ORD-2026-001235 — Processing

Type: Credit Score
Expected time: ~5 minutes
Status updates automatically.

[❌ Cancel Order]
```

Бот автоматически обновляет это сообщение (edit_message) каждые 30 секунд.

### 13.5. Сообщение с результатом

```
✅ Order #ORD-2026-001235 — Completed!

Type: Credit Score
Name: John Smith

📊 Credit Score: 742 (Good)
📋 Bureau: Experian
📅 Report date: 12.03.2026

[📄 Download Report .txt]
[📊 Download Report .csv]
[⭐ Rate]  [⚠️ Dispute]
```

Сообщение закрепляется в чате пользователя.

### 13.6. CRM для ручных воркеров

**Страница входа:** Email + Password.

**Главная страница:**
```
Worker CRM — worker_07

New tasks: 2
My active tasks: 1
Completed today: 5

[📋 New Tasks]  [📁 My Tasks]  [📚 Archive]
```

**Карточка задачи:**
```
Task #12345
Service: People Search (SearchBug)
Priority: Normal
Time waiting: 15 min

Input data:
Name: John Smith
Address: 123 Main St, New York, NY

Account to use: searchbug_acc_03
Proxy: 192.168.1.100:8080

[✅ Take Task]
```

**После взятия задачи:**
```
Task #12345 — In Progress

[Поле для результата — большой textarea]

[📎 Attach File]
[✅ Submit Result]  [⚠️ Report Ban]  [❌ Release Task]
```

### 13.7. Управление прокси

**Рекомендуемые провайдеры:**

| Провайдер | Тип | Цена | Примечание |
| :--- | :--- | :--- | :--- |
| **Webshare** | Датацентр | $0.05/IP | API управления, самый дешёвый. |
| **IPRoyal** | Датацентр | $1.39/IP | Безлимитный трафик. |
| **Decodo** | Датацентр | $0.026/IP | Оптом дёшево. |
| **Bright Data** | Резидентный | $8.40/GB | Для сложных случаев. |

**Для 10 воркеров на 2 недели:** 10 IP × $0.05 = **$0.50/мес** (Webshare).

### 13.8. Формат результата

**Файл `.txt`:**
```
=== РЕЗУЛЬТАТ ПОИСКА ===
Заказ: #ORD-2026-001235
Дата: 12.03.2026 15:30
Тип: Credit Score

--- ДАННЫЕ ---
Имя: John Smith
Кредитный скор: 742 (Good)
Бюро: Experian
Дата отчёта: 12.03.2026

--- ИСТОЧНИК ---
Credit Score Bot (csbot.service)
```

**Файл `.csv`:**
```csv
order_id,date,type,name,score,bureau,report_date
ORD-2026-001235,2026-03-12,credit_score,John Smith,742,Experian,2026-03-12
```

---
### 14.1. Selfreg BA — Полная карточка товара (v17)

**Ключевые изменения:** Убраны поля `balance` и `online_access` для упрощения. Добавлен динамический счетчик аренды номера. Загрузка файла теперь обязательна.

**Все поля:**
| Поле | Тип | Обязательное | Описание |
| :--- | :--- | :--- | :--- |
| `bank_name` | String | ✅ | Название банка. |
| `account_type` | Enum + Custom | ✅ | Checking / Savings / [Свой вариант → модерация]. |
| `has_phone` | Boolean | ✅ | Привязан ли номер телефона. |
| `phone_renewable` | Boolean | Если `has_phone=true` | Можно ли продлить номер. |
| `phone_rental_days_left` | Integer | ❌ | **(Новое)** Динамический счетчик дней аренды номера. Уменьшается каждые 24 часа. 0 = аренда истекла. |
| `has_email` | Boolean | ✅ | Привязана ли почта. |
| `email_change_in_settings` | Boolean | ✅ | Можно ли сменить почту в настройках аккаунта. |
| `state` | String (2 chars) | ✅ | Штат (CA, NY, TX, FL и т.д.). |
| `registration_date` | Date | ✅ | Дата регистрации аккаунта. |
| `auto_delete_days` | Integer | ✅ | Через сколько дней авто-удалить/напомнить снизить цену. 0 = выключено. |
| `price` | Decimal | ✅ | Цена в USD. |
| `file` | File | ✅ | **(Изменено)** Прикреплённый файл с данными (txt/pdf/zip). **Обязательно.** |

**Автоматически генерируемая карточка (пример):**
```
🏦 Chase Bank
💳 Checking
📱 Phone: ✅ Renewable (14 days left)
📧 Email: ✅ | Changeable in settings: ✅
📍 State: CA
📅 Registered: 08/15/2024
💰 Price: $150.00
```

---

### 14.2. Selfreg CC — Полная карточка товара (v17)

**Ключевые изменения:** Добавлен счетчик аренды номера и `auto_delete_days`. Загрузка файла стала возможной.

**Все поля:**
| Поле | Тип | Обязательное | Описание |
| :--- | :--- | :--- | :--- |
| `bank_name` | String | ✅ | Название банка/эмитента. |
| `card_name` | String | ✅ | Название карты (Chase Sapphire, etc.). |
| `credit_limit` | Decimal | ✅ | Кредитный лимит в USD. |
| `has_vcc` | Boolean | ✅ | Есть ли виртуальная карта (VCC). |
| `vcc_limit` | Decimal | Если `has_vcc=true` | Лимит VCC в USD. |
| `state` | String | ✅ | Штат. |
| `zip` | String | ✅ | ZIP-код. |
| `billing_address` | String | ✅ | Адрес выставления счёта. |
| `registration_date` | Date | ✅ | Дата регистрации. |
| `has_phone` | Boolean | ✅ | Привязан ли телефон. |
| `phone_rental_days_left` | Integer | ❌ | **(Новое)** Динамический счетчик дней аренды номера. |
| `has_email` | Boolean | ✅ | Привязана ли почта. |
| `auto_delete_days` | Integer | ✅ | **(Добавлено)** Авто-удаление. |
| `price` | Decimal | ✅ | Цена. |
| `file` | File | ✅ | **(Изменено)** Файл с данными. **Обязательно.** |

---

### 14.3. Logs BA — Полная карточка товара (v17)

**Ключевые изменения:** Убрано поле `safepass_unlocked`. Добавлена возможность загрузки скриншота, ручное описание и конфигуратор для нескольких счетов в Mini App.

**Все поля:**
| Поле | Тип | Обязательное | Описание |
| :--- | :--- | :--- | :--- |
| `banks` | JSON Array | ✅ | Массив банков: `[{name, account_type, balance}]`. |
| `total_balance` | Decimal | ✅ | Суммарный баланс. |
| `email_type` | Enum | ✅ | gmail / aol / yahoo / etc. |
| `email_valid` | Boolean | ✅ | Почта валидна. |
| `has_cvv` | Boolean | ✅ | Есть CVV. |
| `has_promo` | Boolean | ✅ | Есть промо-предложения. |
| `zelle_enrolled` | Boolean | ✅ | Зарегистрирован в Zelle. |
| `has_cookies` | Boolean | ✅ | Есть cookies. |
| `manual_description` | Text | ❌ | **(Новое)** Дополнительное описание от продавца. |
| `has_screenshot` | File | ❌ | **(Изменено)** Скриншот баланса или аккаунта (загружается как файл). |
| `price` | Decimal | ✅ | Цена. |
| `file` | File | ✅ | **(Изменено)** Файл с логами. **Обязательно.** |

**Автоматически генерируемая карточка:**
```
🏦 Chase, BoA
💳 Checking - $4,064.18
💳 CC avb - $17,159.00
‼️ there is CVV
🎁 Promo: ✅
💸 Zelle: ✅
📨 Mail: aol valid

**Seller notes:**
Fresh log, never used before. Good for high-value transfers.

[View Screenshot]

🪙 Price: $700
```

#### 14.3.1. Конфигуратор счетов в Mini App

В Seller Mini App при добавлении/редактировании `Logs BA` появляется интерфейс для управления списком банковских счетов:

- **Список счетов:** Отображается текущий список счетов (до 5).
- **Кнопка `[+ Add Account]`:** Открывает модальное окно с полями:
    - `Bank Name` (input)
    - `Account Type` (select: Checking, Savings, Credit Card)
    - `Balance` (input, numeric)
- **Действия:** Для каждого счета в списке есть кнопки `[Edit]` и `[Delete]`.

---

### 14.4. Brute Bank — Полная спецификация (v17)

**Логика отображения категорий:** Категория в меню для покупателя формируется динамически на основе атрибутов, заданных продавцом в Admin Panel. Формат:

`BankName [AN:RN+INST YODLEE+NAME] [Count]`

- `BankName`: Название банка.
- `[...]`: Строка атрибутов, сгенерированная конфигуратором.
- `[Count]`: Количество доступных позиций в этой группе.

**Примеры из ТЗ:**
- `53 [AN:RN+INST YODLEE+INST FINICITY] [1439]`
- `BMO [AN:RN+INST YODLEE+NAME+ADRESS] [26]`

---

### 14.5. CC Dumps — Полная спецификация (v17)

**Логика массового импорта и навигации:**

1.  **Единая точка входа:** В Seller Bot/Mini App есть одна кнопка: `[Add CC Dumps]`.
2.  **Выбор типа загрузки:** После нажатия система предлагает выбор:
    - `[Single Upload]` (для одного или нескольких дампов вручную).
    - `[Mass Import]` (для загрузки файла).
3.  **Процесс Mass Import:**
    *   Продавец загружает `.txt` файл.
    *   Система парсит файл и для каждой строки определяет BIN, банк, страну и т.д.
    *   **Экран ручной пометки:** Система показывает таблицу со всеми загруженными картами и предлагает массово применить теги:
        - **Колонки:** `Card (first 6, last 4)`, `Bank`, `Country`, `[ ] non_vbv`, `[ ] with_fullz`, `[ ] zip_only`.
        - **Действия:** Продавец может проставить галочки для каждой карты или использовать кнопки `[Select All]` и `[Apply tags]`.
    *   **Подтверждение:** После пометки продавец подтверждает импорт, и все карты добавляются в систему как отдельные товары.

**Навигация для покупателя:** Фильтры `non_vbv`, `with_fullz`, `zip_only` добавляются в меню покупателя наравне с фильтрами по банку, стране и т.д. Они работают как теги для поиска. 
6. Покупатель получает данные в Mirror Bot.

### 14.8. Enroll — Полная спецификация

**Описание:** Доступ к банковским порталам (онлайн-банкинг с готовыми учётными данными).

**Поля:**

| Поле | Тип | Описание |
| :--- | :--- | :--- |
| `bank_name` | String | Название банка. |
| `portal_url` | String | URL портала. |
| `account_type` | String | Тип аккаунта. |
| `balance` | Decimal | Баланс. |
| `state` | String | Штат. |
| `price` | Decimal | Цена. |
| `file` | File | Файл с учётными данными. |

---

## 15. Финансовая модель {#15}

### 15.1. Потоки доходов

| Поток | Описание | Размер |
| :--- | :--- | :--- |
| Регистрационный взнос | Единоразово при регистрации продавца. | $600 |
| Комиссия с продаж | С каждой транзакции In Stocks. | 15% |
| Комиссия Per Order | Системная доля с каждого заказа. | 20% (воркер получает 80%) |
| Автоматизация (прямые продажи) | Прямые продажи услуг пробива. | По тарифу |
| Реферальная программа | Комиссия с реферальных пополнений. | 4% (реферер) |
| Маркетинговая программа | Комиссия маркетологам. | 8.5% |




### 15.3. Формула прибыли

```
Прибыль = Сумма_заказа × Комиссия
         - Реферальный_бонус (4% от пополнения)
         - Маркетинговый_бонус (8.5% от пополнения)
         - Скидка_купона (фиксированная или %)
```

### 15.4. Холд средств продавца

- Средства от продажи поступают на баланс продавца с **холдом 48 часов**.
- Если за 48 часов покупатель не открыл спор — средства становятся доступны для вывода.
- Если спор открыт — средства заморожены до решения модератора.

### 15.5. Лимиты вывода

| Роль | Минимум | Максимум в день |
| :--- | :--- | :--- |
| Seller | $50 | $10,000 |
| Marketer | $50 | $5,000 |
| Worker | $20 | $2,000 |

---

## 16. Рекламная платформа и Управление каналами {#16}

### 16.1. Концепция

Система позволяет администратору управлять сетью Telegram-каналов и групп для привлечения трафика.

### 16.2. Управление каналами (Admin Panel)

**Страница "Channels":**

Таблица: Название / @username / Тип (канал/группа) / Подписчики / Статус / Действия.

**Добавление канала:**
- Добавить бота как администратора канала.
- Ввести @username канала в Admin Panel.
- Система автоматически получает статистику через Telegram API.

### 16.3. Рекламные кампании

**Форма создания кампании:**

| Поле | Тип | Описание |
| :--- | :--- | :--- |
| Название | String | Внутреннее название кампании. |
| Тип | Select | Пост в канале / Рассылка в бот / Совместное. |
| Каналы | MultiSelect | Выбор каналов для публикации. |
| Текст | Textarea | Текст поста (с поддержкой HTML). |
| Медиа | File | Фото/видео (необязательно). |
| UTM-метка | String | Для отслеживания трафика. |
| Дата | DateTimePicker | Время публикации. |
| Бюджет | Decimal | Бюджет кампании (для учёта). |

**Аналитика кампании:**

| Метрика | Описание |
| :--- | :--- |
| Охват | Количество просмотров поста. |
| Переходы | Клики по ссылке (через UTM). |
| Регистрации | Новые пользователи с этой кампании. |
| Пополнения | Пополнения от привлечённых пользователей. |
| Выручка | Заказы от привлечённых пользователей. |
| CAC | Cost per Acquisition = Бюджет / Регистрации. |
| ROI | (Выручка - Бюджет) / Бюджет × 100%. |

### 16.4. Контент-план

**Типы постов:**

| Тип | Частота | Описание |
| :--- | :--- | :--- |
| Новые товары | При появлении | Анонс нового товара от продавца. |
| Акции/Купоны | 2-3 раза в неделю | Промо-коды для подписчиков. |
| Обучающий контент | 1 раз в неделю | Гайды по использованию сервиса. |
| Статистика | 1 раз в месяц | "Продано X товаров в этом месяце". |
| Партнёрские посты | По договорённости | Реклама смежных сервисов. |

---

## 17. Публичный сайт {#17}

### 17.1. Структура страниц

| Страница | URL | Описание |
| :--- | :--- | :--- |
| Главная | `/` | Лендинг с презентацией сервиса. |
| Каталог | `/catalog` | Публичный каталог категорий (без цен, для SEO). |
| Блог | `/blog` | Статьи для SEO. |
| FAQ | `/faq` | Часто задаваемые вопросы. |
| Контакты | `/contact` | Ссылки на Telegram-боты. |
| Статус | `/status` | Статус работы сервисов. |

### 17.2. Главная страница — блоки

1. **Hero:** Заголовок + подзаголовок + кнопка [🚀 Open in Telegram].
2. **Статистика:** Живые счётчики (пользователей, товаров, продавцов).
3. **Категории:** Карточки категорий с иконками.
4. **Как это работает:** 3 шага (Зарегистрируйся → Пополни → Купи).
5. **Преимущества:** 6 карточек (Безопасность, Скорость, Выбор и т.д.).
6. **Отзывы:** Карусель отзывов (из рейтинга системы).
7. **CTA:** Повторная кнопка [🚀 Start Now].

### 17.3. SEO-стратегия

**Кластеры ключевых слов:**

| Кластер | Примеры запросов |
| :--- | :--- |
| Банковские данные | "buy bank logs", "bank account data", "selfreg bank account" |
| Кредитные отчёты | "credit score check", "credit report service", "ssn lookup" |
| eSIM | "buy esim usa", "esim telegram", "esim marketplace" |
| Карты | "buy cc dumps", "credit card data", "fullz cards" |

**Технические требования:**
- Core Web Vitals: LCP < 2.5s, FID < 100ms, CLS < 0.1.
- Мобильная версия: Mobile-first дизайн.
- Структурированные данные: schema.org/Product для каталога.
- Sitemap: Автогенерация при добавлении новых страниц.

---

## 18. Безопасность {#18}

### 18.1. Защита API

| Мера | Описание |
| :--- | :--- |
| JWT-токены | Срок жизни 15 минут + refresh token 7 дней. |
| Rate Limiting | 100 запросов/минуту на IP, 1000/минуту на токен. |
| CORS | Разрешены только домены системы. |
| HTTPS | Обязательный TLS 1.3. |
| WAF | Cloudflare WAF для блокировки атак. |

### 18.2. Защита данных

| Мера | Описание |
| :--- | :--- |
| Шифрование файлов товаров | AES-256 в покое, расшифровка только при выдаче. |
| Маскировка SSN | Отображается как `***-**-XXXX`. |
| Логирование доступа | Все обращения к данным товаров логируются. |
| Удаление данных | Данные проданного товара удаляются через 30 дней. |

### 18.3. Защита от мошенничества

| Мера | Описание |
| :--- | :--- |
| 2FA для сотрудников | Обязательный TOTP для всех ролей Support Bot. |
| Аудит-логи | Все действия сотрудников логируются в `audit_logs`. |
| Лимиты вывода | Ограничения по сумме и частоте. |
| Антифрод маркетологов | 30%/90% правила (см. раздел 8.5). |
| Верификация продавцов | Модерация перед публикацией товаров. |

### 18.4. Резервное копирование

| Компонент | Частота | Хранение |
| :--- | :--- | :--- |
| PostgreSQL | Каждые 6 часов | 30 дней |
| Redis | Каждый час | 7 дней |
| Файлы товаров | Ежедневно | 90 дней |
| Конфигурации | При каждом изменении | Бессрочно |

---

## 19. Приоритеты разработки {#19}

### P0 — Критично (MVP)

- [ ] Конфигурация и подключение к БД.
- [ ] Все модели данных.
- [ ] Mirror Bot: `/start`, регистрация, главное меню.
- [ ] Seller Bot: регистрация, депозит $600.
- [ ] Базовые платёжные интеграции (BTCPay).
- [ ] Support Bot: базовые роли.

### P1 — Высокий приоритет

- [ ] Mirror Bot: полный функционал покупок (In Stocks + Per Order).
- [ ] Seller Bot: все 9 FSM-конфигураторов.
- [ ] Купоны с защитой от повторного использования.
- [ ] Закрепление заказов в чате.
- [ ] Споры и модерация.
- [ ] Вывод средств (продавцы + маркетологи).
- [ ] Marketer Bot: боты-прокси.

### P2 — Средний приоритет

- [ ] Seller Mini App (React).
- [ ] Admin Panel (FastAPI + React).
- [ ] Рейтинги и отзывы.
- [ ] Рассылки.
- [ ] Worker Bot.
- [ ] Многоязычность (RU/ES/ZH).

### P3 — Низкий приоритет

- [ ] Модуль автоматизации (Celery).
- [ ] CRM для ручных воркеров.
- [ ] Публичный сайт.
- [ ] Управление рекламными каналами.
- [ ] Расширенная аналитика.
- [ ] Main Bot (владелец).

---

## 20. Глоссарий {#20}

| Термин | Определение |
| :--- | :--- |
| **Mirror Bot** | Клиентский Telegram-бот, через который покупатели делают заказы. Может быть несколько зеркал. |
| **Seller Bot** | Telegram-бот для продавцов — загрузка товаров, управление продажами. |
| **Marketer Bot** | Telegram-бот для маркетологов — управление ботами-прокси, статистика. |
| **Support Bot** | Telegram-бот для команды поддержки — тикеты, споры, модерация, финансы. |
| **Worker Bot** | Telegram-бот для воркеров — выполнение заказов Per Order. |
| **Main Bot** | Telegram-бот для владельца системы — глобальное управление. |
| **In Stocks** | Тип товаров, которые уже загружены и выдаются мгновенно после оплаты. |
| **Per Order** | Тип услуг, которые выполняются вручную или автоматически после заказа. |
| **Selfreg BA** | Саморегистрированный банковский аккаунт. |
| **Selfreg CC** | Саморегистрированная кредитная карта. |
| **Logs BA** | Логи банковских аккаунтов (данные из стилеров). |
| **Brute Bank** | Данные банковских аккаунтов в формате AN:RN+INST. |
| **AN** | Account Number — номер банковского счёта. |
| **RN** | Routing Number — маршрутный номер банка. |
| **INST** | Integration — тип финансовой интеграции (YODLEE, PLAID и т.д.). |
| **CC Dumps** | Данные кредитных карт. |
| **with_fullz** | Карты с полными личными данными владельца. |
| **zip_only** | Карты только с ZIP-кодом. |
| **non_vbv** | Карты без 3D Secure верификации. |
| **VCC** | Virtual Credit Card — виртуальная кредитная карта. |
| **eSIM** | Электронная SIM-карта, активируется через QR-код. |
| **Enroll** | Доступ к банковскому порталу с готовыми учётными данными. |
| **FSM** | Finite State Machine — конечный автомат для пошагового ввода данных в боте. |
| **BIN** | Bank Identification Number — первые 6 цифр карты. |
| **Холд** | Временная заморозка средств продавца (48 часов) до истечения срока спора. |
| **Антифрод** | Система обнаружения мошеннических действий маркетологов. |
| **ARPU** | Average Revenue Per User — средняя выручка на пользователя. |
| **CAC** | Customer Acquisition Cost — стоимость привлечения одного клиента. |
| **ROI** | Return on Investment — возврат на инвестиции. |
| **SLA** | Service Level Agreement — соглашение об уровне сервиса (таймеры ответа). |
| **RBAC** | Role-Based Access Control — управление доступом на основе ролей. |
| **2FA** | Two-Factor Authentication — двухфакторная аутентификация. |
| **audit_logs** | Таблица логов всех действий сотрудников системы. |
| **BTCPay** | Самохостинговый платёжный шлюз для криптовалют. |
| **Helecat** | Платёжный шлюз для фиатных платежей. |
| **Celery** | Система очередей задач для Python (асинхронное выполнение). |
| **Webshare** | Провайдер датацентровых прокси ($0.05/IP). |
| **SearchBug** | Сервис поиска людей (People Search), используется через ручных воркеров. |
| **EmailRep** | API для проверки репутации email-адресов. |
| **Numverify** | API для верификации телефонных номеров. |
| **Smarty** | API для верификации адресов. |
# Newlookup: Техническое Задание v16.0

**Версия:** 17.0  
**Дата:** 13.03.2026  
**Статус:** Финальная, детализированная

---

## 1. Архитектура и Лимиты

### 1.1. Глобальные лимиты системы

Для обеспечения стабильности и защиты от злоупотреблений вводятся следующие глобальные лимиты, управляемые из Admin Panel:

| Лимит | Значение по умолчанию | Описание |
| :--- | :--- | :--- |
| **Макс. кол-во ботов на маркетолога** | 10 | Ограничение на количество создаваемых ботов-прокси. |
| **Макс. кол-во товаров на продавца** | 1,000 | Общий лимит на количество активных товаров. |
| **Макс. кол-во помощников у продавца** | 5 | Ограничение на размер команды продавца. |
| **Частота запросов к API** | 60 запросов/минуту | Rate limit для внешних API-запросов. |
| **Макс. размер файла для загрузки** | 10 MB | Ограничение на размер файлов, загружаемых продавцами. |

## 2. База Данных

### 2.1. Новые таблицы

- **`pinned_messages`**: `(pin_id, user_id, chat_id, message_id, text, pin_type)` — для хранения информации о закреплённых сообщениях.

### 2.2. Изменения в существующих таблицах

- **`users`**: добавить поле `language_code` (для многоязычности).

## 3. Ролевая модель

Все роли и их права остаются как в v15. Важно обеспечить, чтобы все новые функции (управление лимитами, уровнями доступа, рассылки с закреплением) были доступны только роли `owner` и `admin` в Admin Panel.
## 4. Mirror Bot

### 4.1. Закреплённое сообщение

**Концепция:** После любого действия, требующего внимания пользователя (покупка, открытие спора, получение ответа от поддержки), в чате с ботом появляется или обновляется закреплённое сообщение. Это позволяет пользователю не терять важную информацию в потоке сообщений.

**Типы закреплённых сообщений:**

| Тип | Текст | Кнопки |
| :--- | :--- | :--- |
| **Активный заказ** | `You have an active order #12345. Status: In Progress.` | `[View Order]` `[Open Dispute]` |
| **Новый ответ в тикете** | `You have a new reply in ticket #567.` | `[View Ticket]` |
| **Спор решён** | `Dispute #890 has been resolved.` | `[View Dispute]` |

**Логика работы:**
- Система хранит `message_id` текущего закреплённого сообщения для каждого пользователя.
- При появлении нового события система сначала пытается **отредактировать** существующее закреплённое сообщение.
- Если редактирование невозможно (например, сообщение удалено), система отправляет новое и закрепляет его.

## 5. Seller Bot

### 5.1. Уведомления

Продавец должен получать мгновенные уведомления о всех ключевых событиях. Уведомления приходят в Seller Bot.

**Типы уведомлений:**

- **Новая покупка:** `✅ New Sale! Product "Chase Log" sold to @username for $150.`
- **Открыт спор:** `⚠️ Dispute Opened for order #12345. Buyer's message: "..."`
- **Товар прошёл модерацию:** `👍 Your product "Citi Bank Account" has been approved.`
- **Товар отклонён:** `❌ Your product "..." was rejected. Reason: "..."`
- **Запрос на вывод средств:** `💰 Withdrawal request for $500 has been created.`
- **Вывод средств одобрен:** `✅ Your withdrawal of $500 has been approved and sent.`

### 5.2. Статистика и отчёты

В Seller Bot добавляются команды для быстрого получения отчётов:

- `/stats_today`: Статистика за сегодня (продажи, доход, комиссия).
- `/stats_week`: Статистика за неделю.
- `/stats_month`: Статистика за месяц.
- `/payouts`: История выводов средств.

## 6. Seller Mini App

### 6.1. Логическая структура меню

Главное меню Mini App должно быть интуитивно понятным и логичным.

1. **Дашборд (Главная):** Ключевые метрики (баланс, продажи за сегодня, активные товары, открытые споры).
2. **Товары:**
    - Список всех товаров с возможностью поиска и фильтрации.
    - Кнопка `[➕ Add Product]` для перехода к FSM-конфигуратору в боте.
3. **Заказы:**
    - Список всех заказов.
    - Возможность открыть чат с покупателем (если предусмотрено).
4. **Споры:**
    - Список открытых и закрытых споров.
5. **Финансы:**
    - Запрос на вывод средств.
    - История транзакций (пополнения, продажи, выводы, комиссии).
6. **Аналитика:**
    - Детальная аналитика с выбором периода (продажи по дням, по товарам, по категориям).
7. **Настройки:**
    - Управление командой (добавление/удаление помощников).
    - Настройки уведомлений.
    - Апгрейд уровня доступа.

### 6.2. Настройки уведомлений

В разделе "Настройки" продавец может управлять уведомлениями. **Важно:** нельзя полностью отключить критически важные уведомления, можно лишь выбрать способ их получения (в боте, email, push).

| Уведомление | Настройка по умолчанию | Описание |
| :--- | :--- | :--- |
| **Новая покупка** | Включено (нельзя отключить) | Уведомление о продаже. |
| **Открыт спор** | Включено (нельзя отключить) | Уведомление о споре. |
| **Модерация товара** | Включено | Уведомление о статусе модерации. |
| **Финансовые операции** | Включено (нельзя отключить) | Уведомления о выводе средств. |
| **Ежедневный отчёт** | Выключено | Ежедневная сводка по продажам. |
## 7. Marketer Bot

### 7.1. Главное меню маркетолога

Логика работы маркетолога кардинально меняется. Вместо реферальных ссылок он создаёт и управляет собственными ботами-прокси.

| Кнопка | Описание |
| :--- | :--- |
| **[🤖 My Bots]** | Просмотр списка созданных ботов, их статистика (пользователи, доход). |
| **[➕ Create Bot]** | Запуск FSM-сценария для добавления нового бота-прокси. |
| **[📊 Statistics]** | Общая статистика по всем ботам, ARPU, LTV, ROI. |
| **[💰 Payouts]** | Запрос на вывод средств и просмотр истории выплат. |
| **[📞 Support]** | Связь с поддержкой. |

### 7.2. Флоу: Создание бота-прокси

1.  **Нажатие кнопки:** Маркетолог нажимает `[➕ Create Bot]`.
2.  **Запрос токена:** Бот отвечает: `To create a new proxy bot, go to @BotFather, create a new bot, and forward me the message with the token.`
3.  **Получение токена:** Маркетолог пересылает сообщение от `@BotFather`.
4.  **Валидация:** Система проверяет токен на валидность через Telegram API.
    *   **Успех:** Бот отвечает: `✅ Bot @YourNewBotName has been successfully connected! It will appear in the "My Bots" list within a few minutes.`
    *   **Ошибка:** Бот отвечает: `❌ Invalid token. Please try again.`
5.  **Активация:** Система регистрирует нового бота, привязывает его к маркетологу и запускает для него обработчик (вебхук).

### 7.3. Многоязычность

Все боты (Mirror, Seller, Marketer, Main) должны поддерживать 4 языка: **English (en), Русский (ru), Spanish (es), Chinese (zh)**.

- При первом запуске бот определяет язык пользователя по `user.language_code`.
- В настройках каждого бота есть кнопка `[🌐 Language]` для смены языка.
- Все тексты, кнопки и сообщения хранятся в отдельных файлах локализации (например, `.po` или `.json`) и подгружаются в зависимости от выбранного языка.

## 8. Support Bot

### 8.1. Аудит действий саппортов

Для контроля за работой команды поддержки вводится система аудита. Каждое значимое действие записывается в таблицу `support_audit_log`.

**Что логируется:**

- Открытие/закрытие тикета.
- Ответ в тикете.
- Решение по спору (в пользу покупателя/продавца).
- Бан/разбан пользователя/продавца.
- Одобрение/отклонение вывода средств.
- Модерация товара (одобрение/отклонение).

**Кто видит лог:** Роли `owner` и `auditor` в Admin Panel имеют доступ к полному логу действий команды поддержки с возможностью фильтрации по саппорту, дате и типу действия.

## 9. Worker Bot и Main Bot

Логика этих ботов остаётся без изменений по сравнению с v15. Основная задача — обеспечить стабильную работу и корректное отображение статистики для воркеров и владельца системы.
## 10. Admin Panel

### 10.1. Расширенная CRM

Раздел CRM в Admin Panel становится центральным инструментом для управления пользователями. Он должен предоставлять 360-градусный обзор каждого клиента.

**Карточка пользователя:**

При клике на пользователя в списке открывается его детальная карточка, разделённая на вкладки:

1.  **Обзор (Overview):**
    *   Основная информация: `user_id`, `username`, `first_name`, `language_code`.
    *   Статус: `active`, `banned`.
    *   Ключевые метрики: Total Spend, AOV, LTV, Registration Date, Last Seen.
    *   Теги пользователя (например, `VIP`, `problematic`, `whale`).

2.  **История заказов (Order History):**
    *   Таблица со всеми заказами пользователя: `order_id`, `product_name`, `price`, `status`, `date`.
    *   Возможность перейти в карточку конкретного заказа.

3.  **Финансы (Finances):**
    *   История всех транзакций: пополнения, списания, возвраты.
    *   Текущий баланс.

4.  **Активность (Activity Log):**
    *   Лента всех действий пользователя в системе: запуск бота, нажатие кнопок, использование команд, ошибки.
    *   Это помогает понять, как пользователь взаимодействует с системой и где у него возникают проблемы.

5.  **Коммуникация (Communication):**
    *   Возможность отправить прямое сообщение пользователю от имени бота.
    *   Просмотр истории переписки с поддержкой (если есть интеграция).

### 10.2. Рассылки с закреплением

В разделе "Рассылки" при создании новой рассылки добавляется новый функционал.

**Интерфейс:**

-   Поле для ввода текста сообщения (поддерживает Markdown).
-   Кнопки для добавления inline-клавиатуры.
-   **Новый чекбокс: `[ ] Pin this message for all users`**.

**Логика работы:**

-   Если чекбокс отмечен, то после отправки сообщения всем пользователям система дополнительно отправляет запрос `pinChatMessage` для каждого пользователя.
-   Это сообщение останется закреплённым до тех пор, пока пользователь сам его не открепит или пока не будет отправлена новая рассылка с закреплением.

## 11. Модуль Автоматизации

Логика модуля автоматизации остаётся без изменений по сравнению с v15. Основная задача — обеспечить его стабильную работу и интеграцию с новыми категориями товаров, если они будут добавляться. Важно, чтобы в Admin Panel в разделе "Управление автоматизациями" можно было легко включать/отключать автоматический пробив для каждой категории товаров.
## 12. Спецификации товаров

Все спецификации и конфигураторы для 9 категорий товаров остаются без изменений по сравнению с v15. Все спецификации и конфигураторы для 9 категорий товаров остаются без изменений.

## 13. Финансовая модель

### 13.1. Комиссия платформы

Комиссия платформы теперь зависит от уровня доступа продавца:

| Уровень | Депозит | Комиссия |
| :--- | :--- | :--- |
| **Basic** | $600 | 15% |
| **Advanced** | $1,500 | 13% |
| **Pro** | $5,000 | 12% |

Это изменение должно быть отражено в формуле расчёта прибыли продавца при каждой продаже.

### 13.2. Холд и вывод средств

Логика холда и лимитов на вывод средств остаётся без изменений по сравнению с v15.

## 14. Безопасность

### 14.1. Защита CRM

Поскольку новый раздел CRM в Admin Panel предоставляет доступ к чувствительным данным пользователей, необходимо обеспечить его дополнительную защиту:

-   **Аудит-лог:** Каждое действие в CRM (просмотр карточки, отправка сообщения, изменение тега) должно логироваться с указанием администратора и времени.
-   **Гранулярный доступ:** В будущем можно будет настроить, какие именно поля в карточке пользователя видит та или иная роль поддержки (например, `support` видит только историю заказов, а `admin` — всё).

## 15. Закреплённые сообщения (Pinned Messages)

Это новая глобальная функция, затрагивающая несколько частей системы.

### 15.1. Общая логика

-   В таблице `pinned_messages` хранится информация о текущем закреплённом сообщении для каждого пользователя (`user_id`, `chat_id`, `message_id`).
-   Когда система инициирует событие, требующее закрепления (например, `create_order`), она вызывает внутреннюю функцию `update_pinned_message(user_id, text, keyboard)`.
-   Эта функция:
    1.  Проверяет, есть ли уже закреплённое сообщение для этого `user_id` в таблице `pinned_messages`.
    2.  **Если есть:** Вызывает метод `editMessageText` и `editMessageReplyMarkup` для обновления существующего сообщения.
    3.  **Если нет (или при редактировании возникла ошибка):**
        a. Отправляет новое сообщение.
        b. Закрепляет его с помощью `pinChatMessage`.
        c. Сохраняет/обновляет `message_id` в таблице `pinned_messages`.

### 15.2. Триггеры для закрепления

| Событие | Текст закреплённого сообщения |
| :--- | :--- |
| **Создание заказа Per Order** | `⏳ Your order #12345 is in progress.` |
| **Выполнение заказа** | `✅ Your order #12345 is complete.` |
| **Открытие спора** | `⚠️ You have an open dispute for order #12345.` |
| **Новый ответ в тикете** | `💬 You have a new reply in ticket #567.` |
| **Рассылка с закреплением** | Текст рассылки. |
