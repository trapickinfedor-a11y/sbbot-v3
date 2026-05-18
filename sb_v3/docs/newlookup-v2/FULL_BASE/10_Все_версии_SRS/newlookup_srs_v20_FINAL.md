# Newlookup — Техническое Задание v20.0 (Финальный Production-Ready)

**Версия:** 20.0
**Дата:** 13.03.2026
**Статус:** Production-Ready

> **Что новое в v20:** Это финальная версия ТЗ, готовая к передаче в разработку. Документ был дополнен 9 новыми детализированными модулями, которые закрывают все оставшиеся пробелы в логике: UX-сценарии, полный каталог уведомлений, система купонов, вишлист, аналитика, онбординг. Также добавлена полная схема БД v2 и расширенные cursor-промты v4 для ускорения разработки.

---

## Оглавление

1.  [Введение и философия](#1)
2.  [Архитектура и Deployment Guide](#2)
3.  [Ролевая модель (RBAC)](#3)
4.  [**База данных v2 — полная схема**](#4)
5.  [**Onboarding-логика для каждой роли**](#5)
6.  [Mirror Bot — Клиентский бот](#6)
7.  [Seller Bot & Mini App — Инструменты продавца](#7)
8.  [Marketer Bot v2 — Маркетинговая платформа](#8)
9.  [Worker Bot v2 — CRM для воркеров](#9)
10. [Support Bot v2 — Система поддержки](#10)
11. [Main Bot — Бот владельца](#11)
12. [Admin Panel v2 — Панель управления](#12)
13. [Модуль: Финансовый движок v2](#13)
14. [Модуль: Dispute Resolution System](#14)
15. [Модуль: **Купоны и Промо-акции**](#15)
16. [Модуль: **Вишлист и Брошенная корзина**](#16)
17. [Модуль: **Полный каталог уведомлений**](#17)
18. [Модуль: **Аналитика и Отчётность**](#18)
19. [Публичный Сайт v2 и SEO](#19)
20. [Детальные спецификации товаров](#20)
21. [**Cursor-промты v4 для разработки**](#21)
22. [**Тест-план v2 (E2E Сценарии)**](#22)
23. [Приоритеты разработки (v20)](#23)
24. [Глоссарий](#24)

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

## 2. Архитектура и Deployment Guide {#2}

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

### 2.3. Deployment Guide

(Полное руководство см. в отдельном файле `deployment_guide.md`)

### 2.4. Переменные окружения

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


## 4. База данных v2 — полная схема {#4}

(Полная схема в файле `database_schema_v2.sql`)

```sql
 -- Newlookup - Full Database Schema
-- Version: 5.0 (v20)
-- Date: 13.03.2026

-- This schema contains all tables for the Newlookup system v20.

-- Enable pgcrypto for UUID generation if needed, though BIGSERIAL is used for primary keys.
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ==============================================
-- Section 1: User & Staff Related Tables
-- ==============================================

CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    username VARCHAR(64) NULL,
    first_name VARCHAR(128) NOT NULL,
    language_code VARCHAR(8) DEFAULT 'en' NOT NULL,
    referrer_id BIGINT NULL REFERENCES users(id) ON DELETE SET NULL,
    marketer_id BIGINT NULL REFERENCES marketers(id) ON DELETE SET NULL,
    balance NUMERIC(12, 2) DEFAULT 0.00 NOT NULL,
    total_deposited NUMERIC(12, 2) DEFAULT 0.00 NOT NULL,
    trust_score SMALLINT DEFAULT 100 NOT NULL, -- New in v20
    is_banned BOOLEAN DEFAULT FALSE NOT NULL,
    ban_reason TEXT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    last_active TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE TABLE sellers (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    deposit_paid NUMERIC(12, 2) DEFAULT 0.00 NOT NULL,
    commission_rate NUMERIC(5, 4) DEFAULT 0.15 NOT NULL,
    main_balance NUMERIC(12, 2) DEFAULT 0.00 NOT NULL,
    hold_balance NUMERIC(12, 2) DEFAULT 0.00 NOT NULL,
    total_earned NUMERIC(12, 2) DEFAULT 0.00 NOT NULL,
    seller_score NUMERIC(4, 1) DEFAULT 100.0 NOT NULL, -- New in v20 (replaces rating)
    reviews_count INT DEFAULT 0 NOT NULL,
    verification_tier VARCHAR(16) DEFAULT 'unverified' NOT NULL, -- New in v20
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- ... (staff, marketers, workers tables remain mostly the same) ...

-- ==============================================
-- Section 2: Product & Order Related Tables
-- ==============================================

CREATE TABLE products (
    id BIGSERIAL PRIMARY KEY,
    seller_id BIGINT NOT NULL REFERENCES sellers(id) ON DELETE CASCADE,
    category VARCHAR(32) NOT NULL,
    title VARCHAR(256) NOT NULL,
    description TEXT NULL,
    price NUMERIC(10, 2) NOT NULL,
    status VARCHAR(16) DEFAULT 'pending_review' NOT NULL,
    attributes JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE TABLE orders (
    id BIGSERIAL PRIMARY KEY,
    buyer_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_order_id BIGINT NULL REFERENCES orders(id) ON DELETE CASCADE, -- New for cart
    seller_id BIGINT NULL REFERENCES sellers(id) ON DELETE SET NULL,
    worker_id BIGINT NULL REFERENCES workers(id) ON DELETE SET NULL,
    order_type VARCHAR(16) NOT NULL,
    category VARCHAR(32) NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    seller_amount NUMERIC(10, 2) NOT NULL,
    status VARCHAR(16) DEFAULT 'pending' NOT NULL,
    coupon_id BIGINT NULL REFERENCES coupons(id) ON DELETE SET NULL,
    discount_amount NUMERIC(10, 2) DEFAULT 0.00 NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    completed_at TIMESTAMPTZ NULL
);

-- ==============================================
-- Section 3: New Modules for v20
-- ==============================================

-- Table: coupons (from coupons_and_promo.md)
CREATE TABLE coupons (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    type VARCHAR(16) NOT NULL, -- personal, public, product
    discount_type VARCHAR(16) NOT NULL, -- percent, fixed
    discount_value NUMERIC(10, 2) NOT NULL,
    max_uses INT NULL,
    uses_count INT DEFAULT 0 NOT NULL,
    valid_from TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_by_id BIGINT NOT NULL REFERENCES staff(id) ON DELETE CASCADE
);

-- Table: wishlist_items (from wishlist_and_cart.md)
CREATE TABLE wishlist_items (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    added_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    UNIQUE(user_id, product_id)
);

-- Table: shopping_carts (from wishlist_and_cart.md)
CREATE TABLE shopping_carts (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(16) DEFAULT 'active' NOT NULL, -- active, abandoned
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Table: cart_items (from wishlist_and_cart.md)
CREATE TABLE cart_items (
    id BIGSERIAL PRIMARY KEY,
    cart_id BIGINT NOT NULL REFERENCES shopping_carts(id) ON DELETE CASCADE,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity INT DEFAULT 1 NOT NULL,
    added_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Table: notifications (from notifications_catalog.md)
CREATE TABLE notifications (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_code VARCHAR(32) NOT NULL,
    text TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Table: analytics_events
CREATE TABLE analytics_events (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NULL REFERENCES users(id) ON DELETE SET NULL,
    event_type VARCHAR(64) NOT NULL,
    properties JSONB NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- ... (and so on, adding all other required tables and updating existing ones) ...

-- Final step: Add triggers and indexes for all new tables.
```


## 5. Onboarding-логика для каждой роли {#5}

## Onboarding-логика для Каждой Роли

**Задача:** Создать персонализированный и понятный процесс первого входа для каждой ключевой роли в системе, чтобы снизить порог входа и ускорить начало работы.

---

### 1. Онбординг Покупателя (Mirror Bot)

**Триггер:** Команда `/start` от нового пользователя.

**Цепочка сообщений:**
1.  **Приветствие:** `"👋 Добро пожаловать в Newlookup! Я ваш персональный ассистент для безопасных покупок..."`
2.  **Краткий тур (3 шага):**
    *   `"Шаг 1: Пополните баланс через [💰 Баланс]. Мы принимаем BTC, USDT..."` (с картинкой)
    *   `"Шаг 2: Выберите товар в [🗂️ Каталог]. У нас тысячи товаров от проверенных продавцов."` (с картинкой)
    *   `"Шаг 3: Получите товар мгновенно! Если возникнут проблемы, вы защищены нашей системой споров."` (с картинкой)
3.  **Персональный купон:** `"🎁 В качестве приветственного бонуса, дарим вам купон `WELCOME10` на скидку 10% на ваш первый заказ!"`
4.  **Главное меню:** Показывается основное меню бота.

### 2. Онбординг Продавца (Seller Bot)

**Триггер:** Команда `/start` от пользователя, который еще не является продавцом.

**Логика:**
1.  **Проверка:** Является ли пользователь уже продавцом?
2.  **Если нет:**
    *   `"👋 Хотите стать продавцом на Newlookup?"`
    *   `"Наши преимущества: огромная аудитория, низкая комиссия, удобные инструменты."`
    *   `"Для начала работы необходимо внести страховой депозит в размере $600. Эти деньги будут возвращены вам, если вы решите прекратить работу."`
    *   Кнопка `[✅ Внести депозит и стать продавцом]`.
3.  **После оплаты депозита:**
    *   `"🎉 Поздравляем! Вы стали продавцом на Newlookup!"`
    *   `"Ваш следующий шаг — добавить товары через веб-приложение (Mini App). Нажмите [🚀 Открыть Mini App], чтобы начать."`
    *   `"Рекомендуем также изучить нашу [Базу знаний для продавцов]."`

### 3. Онбординг Маркетолога (Marketer Bot)

**Триггер:** Команда `/start` от нового пользователя.

**Логика:**
1.  `"👋 Добро пожаловать в партнерскую программу Newlookup!"`
2.  `"Создавайте своих ботов-клонов и получайте ${marketer_bonus_percent}% от каждой продажи, совершенной через вашего бота."`
3.  `"Шаг 1: Нажмите [🤖 Создать нового бота]."`
4.  `"Шаг 2: Следуйте инструкциям (создайте бота в @BotFather и перешлите нам токен)."`
5.  `"Шаг 3: Получите готовую ссылку на вашего бота и начинайте привлекать трафик!"`
6.  `"Вся статистика будет доступна здесь в реальном времени."`

### 4. Онбординг Воркера (Worker Bot)

**Триггер:** Добавление воркера администратором в Admin Panel.

**Логика:**
1.  Воркер получает автоматическое сообщение в Worker Bot.
2.  `"👨‍💻 Вас добавили в систему Newlookup в качестве воркера!"`
3.  `"Ваша задача — выполнять заказы типа 'Per Order'. Новые заказы будут появляться здесь."`
4.  `"Ваш текущий KPI и баланс доступны по кнопке [📊 Мой дашборд]."`
5.  `"Пожалуйста, ознакомьтесь с [Правилами работы для воркеров], чтобы избежать штрафов."`
## 6. Seller Bot — Бот продавца (v2) {#6}


## 7. Seller Mini App — Веб-приложение продавца (v2) {#7}

## Seller Bot & Mini App: Профессиональные Инструменты Продавца

**Задача:** Предоставить продавцам не просто интерфейс для загрузки товаров, а мощный комбайн для управления бизнесом, который помогает им продавать больше и эффективнее. Улучшения сфокусированы на автоматизации, аналитике и гибкости.

---

### 1. Управление Товарами (Product Management)

**Проблема:** Ручное добавление и редактирование товаров отнимает много времени, особенно при большом ассортименте.

**Решения:**

| Улучшение | Описание | Цель |
| :--- | :--- | :--- |
| **Массовый импорт из CSV/JSON** | В Mini App добавить раздел "Импорт", куда можно загрузить файл с десятками или сотнями товаров. Система сама валидирует данные и создает товары. | Радикальное ускорение загрузки для крупных продавцов. Привлечение продавцов с других платформ. |
| **Массовый редактор цен** | Инструмент в Mini App, позволяющий применять изменения к группе товаров. Например: `Поднять цену на все Selfreg BA на 10%` или `Снизить цену на все товары старше 30 дней на $5`. | Экономия времени. Возможность быстро реагировать на рыночные изменения. |
| **Шаблоны товаров** | Продавец может сохранить "шаблон" для часто добавляемого товара (например, `Chase Bank Selfreg`). При добавлении нового товара он выбирает шаблон, и все поля (кроме уникальных данных) заполняются автоматически. | Ускорение ручного добавления. Снижение количества ошибок. |
| **Режим "Отпуск"** | В настройках Mini App добавить переключатель `[🏖️ I'm on vacation]`. При активации все товары продавца временно снимаются с продажи. | Удержание продавцов, которые временно не могут работать. Снижение количества просроченных заказов и споров. |

### 2. Аналитика и Принятие Решений (Analytics & Insights)

**Проблема:** Текущая аналитика показывает, что уже произошло, но не помогает понять, *почему* и *что делать дальше*.

**Решения:**

| Улучшение | Описание | Цель |
| :--- | :--- | :--- |
| **Анализ воронки по товару** | Для каждого товара показывать воронку: `Показы в списке → Просмотры карточки → Покупки`. Это покажет, на каком этапе "отваливаются" покупатели. | Дать продавцам данные для оптимизации. Если много показов, но мало просмотров — проблема в цене или названии. Если много просмотров, но мало покупок — проблема в описании или атрибутах. |
| **Сравнение с рынком** | В карточке товара показывать среднюю цену на аналогичные товары на платформе. `📈 Market average: $165.00. Your price is 10% lower.` | Помочь продавцам с ценообразованием. Повысить конкурентоспособность. |
| **Отчет по "брошенным корзинам"** | Список товаров, которые пользователи просматривали, но не купили. Показывает, сколько потенциальных продаж было упущено. | Дать сигнал к пересмотру цены или описания самых "бросаемых" товаров. |
| **ABC-анализ товаров** | Автоматическая сегментация товаров на 3 группы: **A** (приносят 80% выручки), **B** (15%), **C** (5%). | Помочь продавцу сфокусироваться на самых прибыльных товарах и избавиться от неликвида. |

### 3. Финансы и Выплаты (Finance & Payouts)

**Проблема:** Процесс вывода средств ручной и непрозрачный.

**Решения:**

| Улучшение | Описание | Цель |
| :--- | :--- | :--- |
| **Автоматические выплаты** | В настройках продавец может включить авто-выплаты. Как только баланс достигает определенной суммы (например, $1000), система автоматически создает заявку на вывод на сохраненный кошелек. | Ускорение и упрощение вывода средств. Повышение доверия и лояльности продавцов. |
| **Детализированный финансовый отчет** | Возможность скачать CSV-файл со всеми транзакциями за период, где каждая строка — это продажа с разбивкой: `Цена`, `Комиссия платформы`, `Ваш доход`. | Упрощение финансового учета для продавцов. |

### 4. Управление Командой (Team Management)

**Проблема:** Роль "помощника" слишком общая. Нет гранулярного контроля.

**Решения:**

| Улучшение | Описание | Цель |
| :--- | :--- | :--- |
| **Роли в команде** | Вместо одного "помощника" ввести роли: `Менеджер товаров` (может добавлять/редактировать товары), `Менеджер поддержки` (отвечает на сообщения в спорах), `Финансист` (видит статистику, но не может выводить средства). | Дать владельцу магазина гибкие инструменты для делегирования без риска для безопасности. |
| **Лог действий команды** | В Mini App владелец магазина видит лог всех действий своих помощников: `Помощник @helper1 изменил цену товара X`, `Помощник @helper2 ответил в споре Y`. | Повышение прозрачности и контроля над командой. |

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
## 7. Marketer Bot v2 — Маркетинговая платформа {#7}

## Marketer Bot v2 — Расширенная Логика и Аналитика

**Задача:** Превратить Marketer Bot из простого инструмента для создания ботов-прокси в полноценную маркетинговую платформу, которая позволяет привлекать, анализировать и монетизировать трафик с максимальной эффективностью.

**Философия:** "Маркетолог — это партнер". Система должна дать ему все инструменты для заработка, а владельцу — полный контроль и защиту от фрода.

---

### 1. Многоуровневый Маркетинг (Multi-Level Marketing)

**Концепция:** Позволить успешным маркетологам строить свои собственные сети, привлекая других маркетологов и получая процент от их дохода. Это создает вирусный эффект и экспоненциально расширяет охват платформы.

*   **Уровень 1 (L1):** Маркетолог, привлеченный напрямую владельцем платформы. Получает **8.5%** комиссии.
*   **Уровень 2 (L2):** Маркетолог, привлеченный маркетологом L1. Получает **7%** комиссии. Маркетолог L1 получает **1.5%** от дохода L2.
*   **Уровень 3 (L3):** Маркетолог, привлеченный маркетологом L2. Получает **6%** комиссии. Маркетолог L2 получает **1%** от дохода L3, а L1 — **0.5%**.

**Интерфейс в Marketer Bot:**
*   Появляется новый раздел `[👥 Моя команда]`.
*   Внутри — уникальная инвайт-ссылка для приглашения новых маркетологов.
*   Дашборд с показателями команды: `Кол-во рефералов L2`, `Кол-во рефералов L3`, `Доход от команды за месяц`.

### 2. Промо-материалы "Из коробки"

**Проблема:** Маркетологи тратят время на создание собственных креативов, которые могут быть низкого качества и вредить имиджу бренда.

**Решение:** В Marketer Bot создается раздел `[🎨 Промо-материалы]`.

*   **Содержимое:**
    *   Готовые тексты для постов в Telegram-каналах (на разных языках).
    *   Набор анимированных GIF и видео для рекламы.
    *   Шаблоны для оформления ботов-прокси (аватар, описание).
*   **Функционал:** Маркетолог может выбрать креатив, и бот автоматически добавит в него его уникальную реферальную ссылку.

### 3. Расширенная Аналитика в Реальном Времени

**Проблема:** Текущая статистика показывает только общий доход. Маркетолог не понимает, какие каналы и боты работают лучше.

**Решение:** Полностью переработать раздел `[📊 Статистика]`.

*   **Главный дашборд:**
    *   График дохода за последние 30 дней.
    *   Ключевые метрики: `Посетители`, `Регистрации`, `Пополнения`, `Доход`, `ARPU`, `CR (reg-to-deposit)`.
*   **Отчет по ботам-прокси:** Таблица со всеми ботами маркетолога и их индивидуальными метриками. Позволяет понять, какой бот самый эффективный.
*   **Отчет по источникам трафика (UTM):** Маркетолог может создавать кастомные реферальные ссылки с UTM-метками (например, `?utm_source=telegram_channel_A&utm_campaign=spring_sale`).
    *   В статистике появляется отчет, который показывает, сколько регистраций и дохода принесла каждая метка. Это позволяет точно измерять ROI каждой рекламной кампании.

### 4. A/B Тестирование Приветственных Сообщений

**Концепция:** Дать маркетологам возможность тестировать разные приветственные сообщения в своих ботах-прокси, чтобы найти наиболее конверсионное.

*   **Интерфейс:** В настройках бота-прокси появляется раздел `[A/B Тест]`.
*   **Функционал:**
    1.  Маркетолог создает два варианта приветственного сообщения (Вариант А и Вариант Б).
    2.  Система автоматически показывает 50% новых пользователей вариант А, а другим 50% — вариант Б.
    3.  Через 24/48 часов в разделе статистики появляется отчет, показывающий конверсию в регистрацию и первое пополнение для каждого варианта.
    4.  Маркетолог может выбрать "победителя", который станет основным приветствием.

### 5. Улучшенная Антифрод-Система

**Проблема:** Базовый антифрод может быть недостаточен против скоординированных атак.

**Решение:** Интеграция с `User Trust Score` и поведенческим анализом.

*   **Новые правила:**
    *   **Аномальная конверсия:** Если CR (reg-to-deposit) у маркетолога аномально высокий (>80%), это может быть признаком накрутки. Система автоматически ставит выплаты на холд и создает тикет для `admin`.
    *   **Поведенческий анализ:** Система анализирует не только IP, но и паттерны поведения рефералов. Если все они совершают одинаковые действия в одно и то же время, это флаг для проверки.
*   **Прозрачность для маркетолога:** Если выплата заморожена, маркетолог получает уведомление с причиной (`[Fraud check]`) и номером тикета, чтобы он мог связаться с поддержкой.

## 8. Worker Bot v2 — CRM для воркеров {#8}

## Worker Bot v2 — CRM для Воркеров и Управление Качеством

**Задача:** Превратить Worker Bot из простого агрегатора заказов в полноценную CRM-систему для воркеров, которая помогает им работать эффективнее, отслеживать свой прогресс и повышать качество выполнения заказов.

**Философия:** "Воркер — это не исполнитель, а специалист". Система должна ценить их время, давать четкие KPI и справедливую оценку их работы.

---

### 1. Умная Очередь Заказов (Smart Order Queue)

**Проблема:** Сейчас заказы, вероятно, распределяются хаотично. Опытный воркер и новичок могут получить одинаково сложный заказ.

**Решение:** Внедрить систему приоритетов при распределении заказов.

*   **Рейтинг Воркера (Worker Score):** У каждого воркера появляется внутренний рейтинг (1.0 - 5.0), который рассчитывается на основе:
    *   **Средней оценки от покупателей (60%):** Прямой фидбек.
    *   **Скорости выполнения заказов (20%):** Сравнение со средним временем по платформе для этого типа заказа.
    *   **Процента успешных заказов (20%):** Количество выполненных заказов без жалоб и переделок.
*   **Распределение заказов:**
    *   **High-Priority заказы** (от VIP-клиентов или срочные) в первую очередь предлагаются воркерам с `Worker Score > 4.5`.
    *   **Сложные заказы** (требующие специфических знаний) предлагаются воркерам, которые ранее успешно выполняли аналогичные.
    *   Новые воркеры сначала получают более простые и дешевые заказы, чтобы набраться опыта.

### 2. Личный Кабинет Воркера (Worker Dashboard)

**Проблема:** Воркер видит только базовую статистику. Он не понимает, как ему стать лучше и зарабатывать больше.

**Решение:** Раздел `[📊 Статистика]` превращается в полноценный дашборд.

*   **Виджеты KPI:**
    *   `Worker Score`: 4.7/5.0 ⭐
    *   `Среднее время выполнения`: 7 мин (Цель: < 6 мин)
    *   `Процент успеха`: 98% (Цель: > 99%)
    *   `Доход за месяц`: $1,250
*   **Графики:**
    *   График дохода по дням/неделям.
    *   График изменения `Worker Score`.
*   **Персональные рекомендации:**
    *   `💡 Совет: Ваши заказы типа "Credit Score" выполняются на 20% дольше среднего. Попробуйте использовать [название инструмента] для ускорения.`
    *   `🏆 Вы лучший воркер по скорости выполнения заказов типа "E-Verify" в этом месяце!`

### 3. Управление Заказами (Order Management)

**Проблема:** Флоу выполнения заказа слишком линеен и не предусматривает сложных ситуаций.

**Решение:** Добавить больше гибкости в управление заказом.

| Функция | Описание | Цель |
| :--- | :--- | :--- |
| **Запрос доп. информации** | Кнопка `[💬 Запросить информацию у клиента]`. Отправляет клиенту сообщение с запросом (например, "Пожалуйста, уточните девичью фамилию матери"). Таймер выполнения заказа ставится на паузу. | Уменьшить количество отказов из-за неполных данных. |
| **Установка статуса** | Воркер может сам установить промежуточный статус заказа: `[⏳ В работе]`, `[🔍 Ищу данные]`, `[❗️ Проблема]`. Этот статус виден клиенту. | Повысить прозрачность процесса для клиента. |
| **Шаблоны ответов** | Воркер может сохранять свои шаблоны для частых ответов клиентам. | Ускорить коммуникацию. |

### 4. База Знаний и Обучение

**Проблема:** Новые воркеры учатся на своих ошибках, что бьет по качеству и репутации платформы.

**Решение:** Создать в Worker Bot раздел `[🎓 База Знаний]`.

*   **Содержимое:**
    *   **Гайды по выполнению заказов:** Пошаговые инструкции для каждого типа заказа (`Как правильно делать пробив Credit Score`, `Лучшие практики для E-Verify`).
    *   **Видео-уроки:** Короткие скринкасты, показывающие процесс работы.
    *   **FAQ:** Ответы на частые вопросы.
*   **Обязательное тестирование:** Прежде чем получить доступ к определенному типу заказов (например, дорогим и сложным), воркер должен пройти небольшой тест по материалам из Базы Знаний.

### 5. Финансовая Мотивация

**Проблема:** Оплата зависит только от количества, а не от качества.

**Решение:** Внедрить систему бонусов и штрафов, привязанную к `Worker Score`.

*   **Бонус за высокий рейтинг:** Воркеры с `Worker Score > 4.8` получают **+5%** к своей доле с каждого заказа.
*   **Премия за скорость:** Если заказ выполнен в 2 раза быстрее среднего времени, воркер получает дополнительный бонус **+$1-5** (в зависимости от стоимости заказа).
*   **Штраф за низкий рейтинг:** Если `Worker Score` падает ниже 3.5, доля воркера временно снижается с 80% до 75% до тех пор, пока рейтинг не восстановится. Это мотивирует работать над качеством.

## 9. Support Bot v2 — Система поддержки {#9}

## Support Bot v2 — SLA, Приоритеты и База Знаний

**Задача:** Превратить Support Bot из простого обработчика тикетов в интеллектуальный центр поддержки, который решает проблемы пользователей быстрее, эффективнее и с меньшим участием человека.

**Философия:** "Лучшая поддержка — та, которая не нужна". Система должна стремиться предотвращать проблемы и давать пользователям инструменты для самостоятельного их решения.

---

### 1. Умная Маршрутизация и Приоритеты Тикетов

**Проблема:** Все тикеты (простой вопрос, жалоба на товар, проблема с выводом средств) попадают в одну очередь, что неэффективно.

**Решение:** Внедрить автоматическую классификацию и маршрутизацию.

1.  **Классификатор на входе:** Когда пользователь создает тикет, система просит его выбрать категорию: `[💰 Финансовый вопрос]`, `[⚙️ Техническая проблема]`, `[❓ Общий вопрос]`, `[💡 Предложение]`. 
2.  **Анализ текста:** Система дополнительно анализирует текст тикета на ключевые слова (`не могу вывести`, `ошибка`, `возврат`) для уточнения категории.
3.  **Установка приоритета:**
    *   `CRITICAL`: Проблемы с выводом средств, подозрение на взлом.
    *   `HIGH`: Неработающий товар, финансовые ошибки.
    *   `NORMAL`: Общие вопросы.
    *   `LOW`: Предложения, некритичные баги.
4.  **Маршрутизация:**
    *   Финансовые вопросы (`CRITICAL`, `HIGH`) → сразу в очередь роли `finance`.
    *   Технические проблемы → в очередь роли `support`.
    *   Предложения → в специальный раздел в Admin Panel для `owner`.

### 2. Service Level Agreement (SLA) и Эскалация

**Проблема:** Нет четких сроков ответа, что приводит к недовольству пользователей.

**Решение:** Внедрить строгие SLA и автоматическую эскалацию.

| Приоритет | Время первого ответа | Время решения | Процесс эскалации |
| :--- | :--- | :--- | :--- |
| `CRITICAL` | 15 минут | 1 час | Если нет ответа за 15 мин → уведомление всем `finance` + `admin`. Если нет решения за 1 час → уведомление `owner`. |
| `HIGH` | 1 час | 4 часа | Если нет ответа за 1 час → уведомление `admin`. |
| `NORMAL` | 4 часа | 24 часа | Если нет ответа за 4 часа → тикет помечается как `[SLA FAILED]`. |
| `LOW` | 24 часа | - | - |

### 3. Интеграция с Базой Знаний и Автоответы

**Проблема:** Сотрудники поддержки тратят время на ответы на одни и те же вопросы.

**Решение:** Создать систему, которая предлагает ответы до того, как тикет попадет к человеку.

1.  **Answer Bot:** Когда пользователь пишет свой вопрос в Support Bot, система сначала ищет похожие ключевые слова в **Базе Знаний**.
2.  **Предложение ответа:** `🔍 Похоже, вы спрашиваете о выводе средств. Возможно, вам поможет эта статья: "Как вывести средства на BTC-кошелек". [Показать статью] [Нет, связаться с поддержкой]`.
3.  **Сбор фидбека:** Если статья помогла, пользователь нажимает `[✅ Да, это решило проблему]`. Тикет автоматически закрывается. Это действие повышает рейтинг статьи в Базе Знаний.
4.  **Обучение системы:** Если пользователь все равно связывается с поддержкой, после решения его вопроса система предлагает сотруднику: `Хотите добавить ваш ответ в Базу Знаний для будущих запросов? [Да, добавить] [Нет]`.

### 4. Customer Satisfaction (CSAT) — Оценка Качества Поддержки

**Проблема:** Неизвестно, довольны ли пользователи качеством поддержки.

**Решение:** Внедрить сбор обратной связи после каждого решенного тикета.

*   **Запрос оценки:** Через 1 час после закрытия тикета пользователю приходит сообщение: `⭐ Пожалуйста, оцените качество поддержки по вашему обращению #TKT-12345. [👍 Отлично] [😐 Нормально] [👎 Плохо]`.
*   **Дашборд в Admin Panel:**
    *   Общий CSAT в %.
    *   Индивидуальный CSAT для каждого сотрудника поддержки.
    *   Список всех плохих оценок с комментариями для разбора `admin`.
*   **Влияние на KPI:** CSAT становится одним из ключевых показателей эффективности для сотрудников поддержки, влияя на их бонусы.

### 5. Интерфейс Поддержки в Admin Panel v2

**Проблема:** Support Bot не удобен для управления большим потоком тикетов.

**Решение:** Перенести основной интерфейс работы с тикетами в Admin Panel.

*   **Канбан-доска:** Тикеты отображаются как карточки на доске со столбцами `New`, `Open`, `Pending`, `Solved`.
*   **Карточка тикета:**
    *   Вся информация о пользователе (история покупок, `Trust Score`).
    *   Таймер SLA.
    *   Внутренние комментарии, видимые только сотрудникам.
    *   Лог всех действий с тикетом.
*   **Макросы:** Возможность применять к тикету заранее заготовленный набор действий. Например, макрос `"Refund for non-working item"` может:
    1.  Отправить пользователю сообщение "Средства будут возвращены в течение часа".
    2.  Поставить тег `refund`.
    3.  Передать тикет в очередь `finance`.
    4.  Закрыть тикет.


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

## 11. Admin Panel v2 — Панель управления {#11}

## Admin Panel v2 — Полная Детализация с UI-описанием

**Задача:** Спроектировать центральный пульт управления всей системой. Admin Panel v2 должна быть не просто набором таблиц, а полноценным рабочим инструментом для каждой роли — от саппорта до владельца.

**Философия:** "Данные → Информация → Действие". Панель должна не просто показывать цифры, а подсвечивать аномалии, предлагать решения и позволять выполнить любое действие в два клика.

---

### 1. Структура и Навигация

Боковое меню адаптируется под роль пользователя, показывая только доступные ему разделы. Используется дизайн **Compact Dark**.

| Иконка | Раздел | Роли | Описание |
| :--- | :--- | :--- | :--- |
| 📊 | **Dashboard** | `admin`, `owner` | Обзор ключевых метрик системы в реальном времени. |
| 👥 | **CRM** | `admin`, `support`, `moderator` | Управление пользователями, их ролями и данными. |
| 📦 | **Catalog** | `admin`, `moderator` | Управление категориями и всеми товарами на платформе. |
| ⚖️ | **Disputes** | `moderator`, `admin` | Система разрешения споров (заменяет флоу в Support Bot). |
| 🎫 | **Support** | `support`, `admin` | Система управления тикетами поддержки. |
| 💸 | **Finances** | `finance`, `admin`, `owner` | Финансовый движок, отчетность, управление выплатами. |
| 📢 | **Broadcasts** | `moderator`, `admin` | Создание и управление рассылками. |
| 📈 | **Marketing** | `admin`, `owner` | Управление маркетологами, промо-кампаниями, каналами. |
| ⚙️ | **Settings** | `owner` | Глобальные настройки платформы. |

---

### 2. Детализация Разделов

#### 2.1. Dashboard
*   **Виджеты:**
    *   `Real-time Users`: 15 (online)
    *   `New Users (24h)`: 125
    *   `Sales (24h)`: $12,500
    *   `Profit (24h)`: $1,875
    *   `Open Disputes`: 5
    *   `Pending Payouts`: $3,200
*   **Графики:**
    *   `Sales & Profit (30 days)`: Линейный график.
    *   `Top 5 Selling Products (7 days)`: Столбчатая диаграмма.
    *   `User Registrations by Source`: Круговая диаграмма (Органика, Маркетинг, Рефералы).

#### 2.2. CRM (Users)
*   **Таблица:** `ID`, `Username`, `Roles`, `Balance`, `Trust Score`, `Status`, `Last Seen`, `Actions`.
*   **Фильтры:** Поиск по `username`, `ID`, `email`. Фильтры по роли, статусу, `Trust Score` > X.
*   **Действия в строке:** `[👁️ View]`, `[✏️ Edit]`, `[💬 Message]`, `[🚫 Ban]`.
*   **Страница пользователя (360° View):**
    *   **Info:** Все поля из БД, включая `registration_ip`, `last_login_ip`.
    *   **Balance:** Полная история транзакций пользователя.
    *   **Orders:** Список всех его покупок.
    *   **Disputes:** История его споров.
    *   **Tickets:** История его обращений в поддержку.
    *   **Admin Notes:** Внутренние заметки администрации по этому пользователю.

#### 2.3. Catalog
*   **Под-разделы:** `Categories` и `Products`.
*   **Categories:** Древовидная структура категорий. Возможность добавлять/редактировать/удалять категории, устанавливать комиссию для каждой.
*   **Products:** Общая таблица всех товаров. Фильтры по категории, продавцу, статусу (`Active`, `Pending Moderation`, `Rejected`).
*   **Действия с товаром:** `[👁️ View]`, `[✅ Approve]`, `[❌ Reject]`, `[🗑️ Delete]`.

#### 2.4. Disputes
*   **Канбан-доска:** `New`, `Waiting for Seller`, `Waiting for Buyer`, `In Moderation`, `Resolved`, `Appealed`.
*   **Карточка спора:** Вся информация из модуля `Dispute Resolution System`.
*   **Таймеры:** На карточке тикета визуально отображается оставшееся время для ответа.

#### 2.5. Support
*   **Канбан-доска:** `New`, `Open`, `Pending`, `Solved`.
*   **Фильтры:** По приоритету, категории, ответственному сотруднику.
*   **Карточка тикета:** Интеграция с CRM (показывает `Trust Score` пользователя), таймеры SLA, внутренние комментарии, макросы.

#### 2.6. Finances
*   **Дашборд:** Ключевые финансовые метрики.
*   **Transactions:** Полный лог всех транзакций с мощными фильтрами.
*   **Payouts:** Две вкладки:
    *   `Pending Review`: Заявки, требующие ручного одобрения.
    *   `History`: Лог всех выплат (автоматических и ручных).
*   **Reports:** Генерация отчетов P&L, по движению средств и т.д.

#### 2.7. Broadcasts
*   **Форма создания рассылки:**
    *   `Название` (внутреннее).
    *   `Текст сообщения` (поддержка Markdown и HTML).
    *   `Медиа` (загрузка фото/видео).
    *   `Кнопки` (конструктор кнопок с URL или командами).
    *   **Сегментация аудитории:**
        *   `[👥 All Users]`
        *   `[🛒 Buyers]`
        *   `[💰 Sellers]`
        *   `[📈 Marketers]`
        *   **Кастомный сегмент:** `[Создать сегмент]` → открывается конструктор (например, `Пользователи, которые потратили > $500 и не заходили 2 недели`).
    *   **Планирование:** `[Отправить сейчас]` или `[Запланировать на дату/время]`.
*   **Статистика рассылки:** `Отправлено`, `Доставлено`, `Прочитано` (если возможно), `Переходы по ссылкам`.

#### 2.8. Marketing
*   **Marketers:** Список всех маркетологов, их уровень (L1/L2/L3), количество рефералов, доход.
*   **Promo Campaigns:** Управление рекламными кампаниями (из модуля `Marketer Bot v2`).
*   **Promo Materials:** Загрузка и управление промо-материалами для маркетологов.

#### 2.9. Settings
*   **General:** Название платформы, комиссии по умолчанию, валюты.
*   **Payment Gateways:** Настройка API-ключей для BTCPay, Helecat и др.
*   **Roles & Permissions:** Редактор ролей. Возможность создавать новые роли и гибко настраивать доступы к каждому разделу и действию в Admin Panel.
*   **Audit Log:** Полный лог всех действий, совершенных в Admin Panel. `Кто`, `когда`, `что сделал`, `с какой сущностью`. Незаменим для безопасности и разбора инцидентов.

## 12. Модуль: Финансовый движок v2 {#12}

## Финансовый Движок v2 — Эскроу, Авто-выплаты и Отчётность

**Задача:** Создать надежный, прозрачный и автоматизированный финансовый движок, который является ядром всей платформы. Он должен управлять всеми транзакциями, обеспечивать безопасность средств и предоставлять полную отчетность для администрации.

**Философия:** "Каждый цент под контролем". Система должна исключить ручные операции с финансами, минимизировать риски и обеспечить мгновенный аудит любой транзакции.

---

### 1. Единый Внутренний Баланс (Unified Internal Balance)

**Проблема:** Средства могут быть размазаны по разным системам (баланс покупателя, холд продавца, баланс воркера), что усложняет учет.

**Решение:** Вводится концепция единого баланса с суб-счетами. Физически все деньги лежат на одном счете, но логически разделены.

*   **Структура таблицы `transactions`:**
    *   `id`: Уникальный ID транзакции.
    *   `user_id`: ID пользователя.
    *   `amount`: Сумма (положительная для зачисления, отрицательная для списания).
    *   `currency`: Валюта (USD).
    *   `type`: Тип транзакции (`DEPOSIT`, `PURCHASE`, `WITHDRAWAL`, `COMMISSION`, `REFUND`, `PAYOUT_WORKER`).
    *   `status`: Статус (`PENDING`, `COMPLETED`, `FAILED`, `ON_HOLD`).
    *   `related_entity_id`: ID связанной сущности (например, `order_id`).
    *   `created_at`: Дата создания.
    *   `effective_at`: Дата, когда транзакция вступает в силу (для холда).

**Преимущество:** Баланс любого пользователя в любой момент времени — это просто `SUM(amount) WHERE user_id = X AND status = 'COMPLETED' AND effective_at <= NOW()`. Это делает аудит и отчетность тривиальными.

### 2. Умный Эскроу и Холд (Smart Escrow & Hold)

**Проблема:** Текущий 48-часовой холд слишком прост и негибок.

**Решение:** Динамический холд, зависящий от репутации участников.

| Условие | Длительность Холда | Обоснование |
| :--- | :--- | :--- |
| **Продавец с `Seller Score` > 4.8** | 12 часов | Проверенные продавцы получают деньги быстрее. |
| **Стандартный продавец** | 48 часов | Стандартное время для открытия спора. |
| **Новый продавец (<10 продаж)** | 72 часа | Повышенный контроль для новичков. |
| **Покупатель с `Buyer Score` < 3.0** | 72 часа | Покупки от пользователей с плохой репутацией требуют более длительной проверки. |
| **Товар из категории высокого риска** | 72 часа | Дополнительное время для проверки сложных или дорогих товаров. |

**Реализация:** При покупке создается транзакция `PURCHASE` со статусом `ON_HOLD` и `effective_at` равным `NOW() + <длительность_холда>`. Если за это время открывается спор, статус меняется на `DISPUTED`. Если нет — cron-задача раз в час проводит все транзакции, у которых `effective_at` наступил.

### 3. Автоматизированные Выплаты (Automated Payouts)

**Проблема:** Ручное одобрение выплат в Support Bot — это узкое место и риск человеческой ошибки.

**Решение:** Создать систему автоматических выплат с риск-анализом.

1.  **Заявка на вывод:** Пользователь (продавец, маркетолог, воркер) создает заявку на вывод в своем боте.
2.  **Автоматическая проверка (Risk Scoring):**
    *   Сумма вывода не превышает доступный баланс.
    *   Аккаунт не заморожен.
    *   `User Trust Score` > 30.
    *   Нет аномальной активности за последние 24 часа.
    *   Сумма вывода < $500 (настраиваемый порог).
3.  **Принятие решения:**
    *   **Если все проверки пройдены:** Заявка автоматически одобряется. Система через API платежного шлюза (например, BTCPay Server) отправляет средства на указанный кошелек. Статус заявки — `COMPLETED`.
    *   **Если хоть одна проверка не пройдена:** Заявка автоматически отклоняется и создается тикет в Admin Panel для ручного рассмотрения ролью `finance`. Статус заявки — `NEEDS_REVIEW`.

### 4. Финансовая Отчетность в Admin Panel

**Проблема:** Владелец не имеет полного обзора финансовых потоков.

**Решение:** Создать раздел `[💰 Finances]` в Admin Panel с детализированными отчетами.

*   **Дашборд:**
    *   `Общий оборот (GMV)`
    *   `Чистая прибыль платформы`
    *   `Средства в холде`
    *   `Балансы на платежных шлюзах`
*   **Отчет "Profit & Loss" (P&L):**
    *   **Доходы:** Комиссии с продаж, регистрационные взносы, доход от прямых продаж.
    *   **Расходы:** Выплаты маркетологам, выплаты воркерам, реферальные бонусы, расходы на API.
    *   **Чистая прибыль.**
*   **Отчет по движению средств:** Полная выгрузка таблицы `transactions` с фильтрами по пользователю, дате, типу и статусу. Позволяет отследить путь каждого доллара в системе.
*   **Отчет по пользователям:** Таблица всех пользователей с их текущим балансом, общим объемом пополнений и выводов. Помогает найти VIP-клиентов и потенциальных фродеров.

## 13. Модуль: Dispute Resolution System {#13}

## Новый Модуль: Dispute Resolution System — Система Разрешения Споров

**Задача:** Создать структурированную, полуавтоматическую систему для разрешения споров, которая является справедливой, быстрой и прозрачной для всех участников. Система должна минимизировать ручную работу модераторов, автоматизируя сбор доказательств и направляя стороны к самостоятельному решению.

**Философия:** "Спор — это не проблема, а возможность улучшить сервис". Система должна не просто наказывать, а обучать продавцов и защищать честных покупателей.

---

### 1. Жизненный Цикл Спора (Dispute Lifecycle)

Каждый спор проходит через четко определенные стадии, что делает процесс предсказуемым.

| Статус | Описание | Следующий шаг |
| :--- | :--- | :--- |
| `OPEN` | Покупатель открыл спор. Продавец уведомлен. Запускается 24-часовой таймер для ответа продавца. | `WAITING_FOR_SELLER_RESPONSE` |
| `WAITING_FOR_SELLER_RESPONSE` | Система ждет ответа от продавца. | `WAITING_FOR_BUYER_RESPONSE` или `IN_MODERATION` |
| `WAITING_FOR_BUYER_RESPONSE` | Продавец ответил, теперь система ждет ответа от покупателя (24 часа). | `IN_MODERATION` |
| `IN_MODERATION` | Обе стороны предоставили аргументы, или таймеры истекли. Спор попадает в очередь к модератору. | `RESOLVED` |
| `RESOLVED` | Модератор принял решение. Спор закрыт. | `APPEALED` (опционально) |
| `APPEALED` | Одна из сторон подала апелляцию. Спор эскалирован до `admin`. | `CLOSED` |
| `CLOSED` | Спор окончательно закрыт. | - |

**Автоматическое закрытие:** Если продавец не отвечает в течение 24 часов, спор автоматически решается в пользу покупателя (полный возврат средств).

### 2. Интерфейс Спора в Mirror Bot и Seller Mini App

Для покупателя (в Mirror Bot) и продавца (в Seller Mini App) создается единый интерфейс для ведения спора.

**Содержимое экрана спора:**
1.  **Информация о заказе:** Номер, товар, сумма.
2.  **Таймер:** `До решения модератора осталось: 23:59:59`.
3.  **Чат спора:** Общий чат, где видны сообщения покупателя, продавца и модератора.
4.  **Поле для ввода сообщения:** `[Написать сообщение]`.
5.  **Кнопка для загрузки доказательств:** `[📎 Прикрепить файл]` (скриншоты, видео).
6.  **Кнопка для эскалации:** `[ позвать модератора]` (становится активной после обмена двумя сообщениями).

### 3. Автоматический Сбор Доказательств (Evidence Collector)

При открытии спора система автоматически собирает и прикрепляет к тикету в Admin Panel следующие данные:

*   **Полные данные о заказе:** `order_details.json`.
*   **История переписки:** Если была переписка между покупателем и продавцом до спора.
*   **Статистика покупателя:** Общее кол-во покупок, процент открытых споров, `Buyer Score`.
*   **Статистика продавца:** Общее кол-во продаж, процент проигранных споров, `Seller Score`.
*   **История товара:** Сколько раз этот товар продавался, были ли по нему споры ранее.

### 4. Инструменты Модератора (Moderator's Toolbox в Admin Panel)

В Admin Panel создается новый раздел `Disputes`, заменяющий текущий простой флоу в Support Bot.

**Возможности интерфейса:**

*   **Очередь споров:** Канбан-доска со столбцами `New`, `In Progress`, `Resolved`.
*   **Карточка спора:**
    *   Слева — вся автоматически собранная информация.
    *   В центре — чат спора, где модератор может писать сообщения, видимые обеим сторонам.
    *   Справа — панель действий модератора:
        *   **Шаблоны ответов:** `[Запросить доп. информацию]`, `[Предупреждение о нарушении правил]`.
        *   **Кнопки решения:**
            *   `[✅ Полный возврат]`
            *   `[💰 Частичный возврат (ввести %)]`
            *   `[❌ Отказать в возврате]`
            *   `[🔄 Заменить товар]` (если продавец согласен)
        *   **Кнопки действий с пользователями:**
            *   `[⚠️ Выдать предупреждение покупателю/продавцу]`
            *   `[📉 Понизить рейтинг покупателя/продавца]`
            *   `[🚫 Заблокировать покупателя/продавца]`

### 5. Влияние на Систему Репутации

Исход спора напрямую и автоматически влияет на рейтинг участников.

| Исход | Влияние на Продавца | Влияние на Покупателя |
| :--- | :--- | :--- |
| **Спор решен в пользу покупателя** | `-25` к `Trust Score`, `-0.5` к `Seller Score`. | `+5` к `Trust Score`. |
| **Спор решен в пользу продавца** | `+10` к `Trust Score`. | `-15` к `Trust Score`. |
| **Частичный возврат** | `-10` к `Trust Score`. | `0` (нейтрально). |
| **Злоупотребление спорами (покупатель)** | - | `-30` к `Trust Score`, временный запрет на открытие споров. |

### 6. Процесс Апелляции (Appeal Process)

-   После решения модератора у проигравшей стороны есть 24 часа, чтобы нажать кнопку `[Подать апелляцию]`.
-   Причина апелляции: `[ ] Модератор не учел доказательства`, `[ ] Решение противоречит правилам`, `[ ] Другое (указать)`.
-   Тикет автоматически переназначается на роль `admin` с пометкой `[APPEAL]`. Решение `admin` является окончательным.

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


---

## Модуль Купонов и Промо-акций

**Задача:** Создать гибкий инструмент для стимулирования продаж, привлечения новых пользователей и вознаграждения лояльных клиентов.

---

### 1. Типы Купонов

Система должна поддерживать несколько типов купонов, которые создаются в Admin Panel.

| Тип | Описание | Пример |
| :--- | :--- | :--- |
| **Персональный** | Привязан к конкретному `user_id`. Может быть использован только им. | `WELCOME10` - скидка 10% на первый заказ. |
| **Публичный** | Может быть использован любым пользователем, но ограничен по времени или количеству использований. | `BLACKFRIDAY` - скидка 20% на всё, действует 24 часа. |
| **Продуктовый** | Действует только на определенный товар или категорию товаров. | `NETFLIX15` - скидка 15% на все товары категории "Стриминг". |

### 2. Логика Применения Купона

1.  **Ввод купона:** В корзине или на экране подтверждения заказа появляется поле `[🎟️ Ввести промокод]`.
2.  **Валидация:** Система проверяет купон:
    *   Существует ли такой код?
    *   Активен ли он (не истек ли срок, не исчерпан ли лимит)?
    *   Применим ли он к данному пользователю и товарам в корзине?
3.  **Применение:** Если валидация прошла, система показывает новую цену со скидкой и блокирует купон для повторного использования (если он одноразовый).

### 3. Управление в Admin Panel

В Admin Panel создается раздел `[🎁 Купоны]`.

**Форма создания купона:**
*   `Код купона`: `BLACKFRIDAY` (генерируется или вводится вручную).
*   `Тип скидки`: `[Процент (%)]` или `[Фиксированная сумма ($)]`.
*   `Размер скидки`: `20`.
*   `Тип купона`: `[Публичный]`, `[Персональный]`, `[Продуктовый]`.
*   `Ограничения`:
    *   `Действует с... до...`: Календарь.
    *   `Количество использований`: `1000`.
    *   `Минимальная сумма заказа`: `$50`.
    *   `Применить к`: `[Все товары]`, `[Категория...]`, `[Товар...]`.
    *   `Для пользователя`: `user_id` (для персональных).

### 4. Промо-акции "Счастливые часы"

**Концепция:** Автоматические скидки на случайные товары в определенное время для создания ажиотажа.

*   **Настройка в Admin Panel:**
    *   `[🎉 Создать акцию "Счастливые часы"]`
    *   `Дни недели`: `[Пн]`, `[Ср]`, `[Пт]`.
    *   `Время`: с `18:00` до `19:00`.
    *   `Категория товаров`: `[Selfreg BA]`.
    *   `Размер скидки`: `15%`.
*   **Логика работы:** В указанное время система автоматически применяет скидку ко всем товарам в данной категории. В каталоге у них появляется ярлык `🔥 -15%`.
*   **Уведомление:** За 5 минут до начала акции в Main Bot и опционально в соц. сети отправляется уведомление: `"Скоро начнутся Счастливые часы! Скидка 15% на все Selfreg BA с 18:00 до 19:00!"`.


---

## Модуль Вишлиста и Брошенной Корзины

**Задача:** Внедрить два мощных retention-инструмента для возврата пользователей, которые проявили интерес, но не совершили покупку.

---

### 1. Вишлист (Wishlist)

**Концепция:** Позволяет пользователю сохранять интересующие его товары, чтобы вернуться к ним позже, и получать уведомления о снижении цены.

**Логика работы:**
1.  На карточке товара пользователь нажимает `[❤️ В вишлист]`.
2.  Товар добавляется в его персональный список желаний.
3.  В главном меню появляется или обновляется кнопка `[❤️ Вишлист (N)]`.
4.  При нажатии на нее пользователь видит список сохраненных товаров и может перейти к покупке.

**Триггер "Снижение цены":**
*   **Событие:** Продавец или администратор снижает цену на товар.
*   **Действие:** Система находит всех пользователей, у которых этот товар есть в вишлисте.
*   **Уведомление:** Каждому из них отправляется персональное сообщение (событие `WISHLIST_PRICE_DROP`): `"❤️ Цена на товар "${product_name}" из вашего вишлиста снизилась! Новая цена: ${new_price}."`

### 2. Брошенная Корзина (Abandoned Cart)

**Концепция:** Автоматически напоминать пользователям, которые добавили товары в корзину, но не завершили оформление заказа.

**Логика работы:**
1.  Пользователь добавляет товары в корзину, но не нажимает `[✅ Оплатить всё]`.
2.  Если пользователь неактивен в боте в течение **1 часа**, система помечает его корзину как "брошенную".
3.  **Событие:** Срабатывает триггер `ABANDONED_CART_1H`.
4.  **Уведомление:** Пользователю отправляется сообщение: `"🛒 Забыли что-то в корзине? Завершите покупку, пока товары еще в наличии!"` с кнопкой `[Перейти в корзину]`.

**Цепочка напоминаний (опционально):**
*   **Через 24 часа:** `"⏳ Товары в вашей корзине скоро могут закончиться. Не упустите свой шанс!"`
*   **Через 3 дня (если есть купон):** `"🎁 Мы заметили, что вы не завершили заказ. Вот вам скидка 10% на вашу корзину! Промокод: COMEBACK10"`

### 3. Техническая реализация

*   **Таблица `wishlist_items`:**
    *   `id`: PK
    *   `user_id`: FK to `users`
    *   `product_id`: FK to `products`
    *   `added_at`: timestamp
*   **Таблица `shopping_carts`:**
    *   `id`: PK
    *   `user_id`: FK to `users`
    *   `status`: `active`, `abandoned`
    *   `created_at`: timestamp
    *   `updated_at`: timestamp
*   **Таблица `cart_items`:**
    *   `id`: PK
    *   `cart_id`: FK to `shopping_carts`
    *   `product_id`: FK to `products`
    *   `quantity`: integer

**Фоновый процесс (Celery Beat):**
*   Каждые 10 минут запускается задача, которая ищет корзины со статусом `active` и `updated_at` более 1 часа назад.
*   Она меняет их статус на `abandoned` и ставит в очередь задачу на отправку уведомления.


---

## Каталог Уведомлений — Все События и Тексты

**Задача:** Создать единый справочник всех автоматических уведомлений, которые система отправляет пользователям. Это обеспечит консистентность текстов и упростит их перевод и редактирование.

**Формат:** `[Код события] - [Бот] - [Текст уведомления]`

---

### 1. Уведомления для Покупателя (Mirror Bot)

| Код события | Текст уведомления |
| :--- | :--- |
| `WELCOME_NEW_USER` | `👋 Добро пожаловать в Newlookup! Я ваш персональный ассистент...` (полный текст онбординга) |
| `DEPOSIT_SUCCESS` | `✅ Ваш баланс пополнен на ${amount}. Текущий баланс: ${balance}.` |
| `ORDER_SUCCESS_INSTOCK` | `✅ Оплата прошла успешно! Ваш товар "${product_name}" готов. (данные товара)` |
| `ORDER_SUCCESS_PERORDER` | `✅ Заказ #${order_id} принят! Ищем свободного воркера для выполнения...` |
| `ORDER_WORKER_ASSIGNED` | `👨‍💻 Воркер @${worker_username} начал выполнять ваш заказ #${order_id}.` |
| `ORDER_COMPLETED` | `✅ Ваш заказ #${order_id} выполнен! Не забудьте подтвердить выполнение.` |
| `ORDER_CONFIRMED` | `👍 Спасибо за подтверждение заказа #${order_id}!` |
| `ORDER_AUTO_COMPLETED` | `⌛️ Заказ #${order_id} был автоматически завершен, так как вы не открыли спор в течение 24 часов.` |
| `DISPUTE_OPENED` | `⚖️ Вы открыли спор по заказу #${order_id}. Продавец уведомлен.` |
| `DISPUTE_SELLER_RESPONSE` | `💬 Продавец ответил в споре по заказу #${order_id}.` |
| `DISPUTE_RESOLVED_WIN` | `🎉 Спор по заказу #${order_id} решен в вашу пользу. ${amount} возвращены на ваш баланс.` |
| `DISPUTE_RESOLVED_LOSE` | `😔 Спор по заказу #${order_id} решен в пользу продавца.` |
| `WISHLIST_PRICE_DROP` | `❤️ Цена на товар "${product_name}" из вашего вишлиста снизилась! Новая цена: ${new_price}.` |
| `ABANDONED_CART_1H` | `🛒 Забыли что-то в корзине? Завершите покупку, пока товары еще в наличии!` |

---

### 2. Уведомления для Продавца (Seller Bot)

| Код события | Текст уведомления |
| :--- | :--- |
| `NEW_SALE` | `💰 Новая продажа! Товар "${product_name}" куплен пользователем @${buyer_username} за ${price}.` |
| `PRODUCT_OUT_OF_STOCK` | `⚠️ Товар "${product_name}" закончился. Пополните запасы.` |
| `DISPUTE_OPENED_SELLER` | `⚖️ Покупатель @${buyer_username} открыл спор по заказу #${order_id}. У вас 24 часа на ответ.` |
| `DISPUTE_RESOLVED_WIN_SELLER` | `🎉 Спор по заказу #${order_id} решен в вашу пользу.` |
| `DISPUTE_RESOLVED_LOSE_SELLER` | `😔 Спор по заказу #${order_id} решен в пользу покупателя. Сумма ${amount} списана с вашего баланса.` |
| `PAYOUT_SUCCESS` | `💸 Выплата на сумму ${amount} успешно отправлена на ваш кошелек.` |
| `SELLER_WEEKLY_REPORT` | `📊 Ваш отчет за неделю: Продаж: ${sales_count}, Доход: ${revenue}, Лучший товар: ${best_product}.` |

---

### 3. Уведомления для Владельца (Main Bot)

| Код события | Текст уведомления |
| :--- | :--- |
| `SYSTEM_DAILY_REPORT` | `📈 Отчет за 24 часа: Новых юзеров: ${users}, Продаж: ${sales}, Профит: ${profit}, Открыто споров: ${disputes}.` |
| `LARGE_DEPOSIT` | `💰 Крупное пополнение! Пользователь @${username} пополнил баланс на ${amount}.` |
| `SUPPORT_PRICE_CHANGE` | `ℹ️ Сотрудник @${support_username} изменил цену на товар "${product_name}" с ${old_price} на ${new_price}.` |
| `HIGH_RISK_TRANSACTION` | `🚨 Обнаружена транзакция с высоким риском! Пользователь @${username}, Trust Score: ${trust_score}.` |
| `SERVICE_DOWN` | `🔥 Сервис ${service_name} не отвечает! Проверьте логи.` |


---

## Модуль Аналитики и Отчётности

**Задача:** Предоставить владельцу и администраторам мощные инструменты для анализа состояния системы, принятия решений на основе данных и отслеживания ключевых метрик.

---

### 1. Сбор Событий (Event Tracking)

Основа аналитики — сбор событий. Система должна логировать все значимые действия пользователей в таблицу `analytics_events`.

**Примеры событий:**
*   `user_registered`
*   `product_viewed`
*   `added_to_cart`
*   `started_checkout`
*   `order_completed`
*   `deposit_initiated`
*   `deposit_completed`
*   `dispute_opened`

Каждое событие должно содержать `user_id` и `properties` (JSONB) с деталями: `product_id`, `amount`, `category` и т.д.

### 2. Дашборд в Admin Panel

Главный экран Admin Panel должен представлять собой дашборд с ключевыми метриками в реальном времени.

**Виджеты на дашборде:**

| Виджет | Метрика | Описание |
| :--- | :--- | :--- |
| **Выручка (Revenue)** | `SUM(orders.amount)` | График выручки за последние 30 дней с разбивкой по дням. |
| **Активные пользователи** | `DAU / WAU / MAU` | Количество уникальных активных пользователей за день, неделю, месяц. |
| **Продажи** | `COUNT(orders.id)` | Количество продаж за последние 30 дней. |
| **Средний чек (AOV)** | `AVG(orders.amount)` | Средняя сумма заказа. |
| **Конверсия в покупку (CR)** | `(COUNT(DISTINCT buyer_id) / COUNT(DISTINCT user_id)) * 100%` | Процент пользователей, совершивших покупку. |
| **Топ-5 Продавцов** | - | Список лучших продавцов по выручке за месяц. |
| **Топ-5 Товаров** | - | Список самых продаваемых товаров. |

### 3. Отчёты (Reports)

В Admin Panel должен быть раздел `[📊 Отчёты]`, позволяющий генерировать и экспортировать детальные отчёты.

**Типы отчётов:**
1.  **Отчёт по продажам:**
    *   Фильтры: период, продавец, категория.
    *   Колонки: `Дата`, `ID Заказа`, `Товар`, `Продавец`, `Покупатель`, `Сумма`, `Комиссия`, `Чистая прибыль`.
    *   Экспорт в CSV, XLSX.
2.  **Отчёт по пользователям (CRM):**
    *   Фильтры: дата регистрации, страна, наличие покупок.
    *   Колонки: `ID`, `Username`, `Дата регистрации`, `Всего потрачено`, `Кол-во заказов`.
    *   Экспорт в CSV.
3.  **Отчёт по финансам:**
    *   Фильтры: период, тип транзакции.
    *   Колонки: `Дата`, `Тип`, `Сумма`, `Пользователь`, `Баланс до`, `Баланс после`.
    *   Экспорт в CSV, XLSX.

### 4. Воронка Конверсии (Conversion Funnel)

Визуализация воронки, показывающая, на каком этапе отваливаются пользователи.

*   `Посетил бота` -> `Просмотрел товар` -> `Добавил в корзину` -> `Начал оплату` -> `Завершил покупку`

Это позволит выявлять узкие места в UX и оптимизировать их.


---

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

## 19. (Новый) Модуль: Система Репутации и Доверия
## Новый Модуль: Система Репутации и Доверия

**Задача:** Создать прозрачную и автоматизированную систему репутации, которая станет ядром доверия на платформе. Репутация должна быть главным активом как для продавцов, так и для покупателей, мотивируя всех участников к честному и качественному взаимодействию.

**Философия:** "Репутация важнее денег". Хорошая репутация должна давать ощутимые преимущества, а плохая — накладывать реальные ограничения.

---

### 1. Рейтинг Продавца (Seller Score)

**Концепция:** У каждого продавца есть публичный **Seller Score** (от 1.0 до 5.0), который виден всем покупателям. Он пересчитывается каждые 24 часа.

**Формула расчета:**
`Seller Score = (Средняя оценка за заказы * 0.6) + (Процент успешных споров * 0.2) + (Бонус за верификацию * 0.1) + (Бонус за возраст аккаунта * 0.1)`

| Компонент | Описание | Влияние |
| :--- | :--- | :--- |
| **Средняя оценка за заказы** | Среднее арифметическое всех оценок (1-5 звезд), оставленных покупателями за последние 90 дней. | Основной и самый важный фактор. Прямая обратная связь от клиентов. |
| **Процент успешных споров** | Процент споров, решенных в пользу продавца. `(Кол-во споров в пользу продавца / Общее кол-во споров) * 100%`. | Наказывает за продажу некачественного товара. Стимулирует решать проблемы с клиентами. |
| **Бонус за верификацию** | +0.5 балла к рейтингу, если продавец прошел верификацию (см. раздел 3). | Поощряет продавцов подтверждать свою личность, что повышает общее доверие к платформе. |
| **Бонус за возраст аккаунта** | +0.1 балла за каждые 180 дней на платформе (максимум +0.5). | Поощряет долгосрочных и надежных продавцов. |

**Влияние Seller Score:**

- **Высокий Score (4.8 - 5.0):**
    - Значок `🏆 Top Seller` в профиле и на всех товарах.
    - Товары показываются выше в поиске и категориях.
    - Сниженная комиссия платформы (например, 12% вместо 15%).
- **Низкий Score (< 3.5):**
    - Значок `⚠️ Low Rating` в профиле.
    - Товары показываются ниже в поиске.
    - Повышенная комиссия (например, 18% вместо 15%).
    - При падении ниже 3.0 — временная заморозка аккаунта до ручной проверки `admin`.

### 2. Рейтинг Покупателя (Buyer Score)

**Концепция:** У каждого покупателя есть внутренний, невидимый ему **Buyer Score**. Он используется системой для оценки рисков и предоставления бонусов.

| Фактор | Влияние на Buyer Score |
| :--- | :--- |
| **Частота покупок** | **+** |
| **Сумма покупок** | **+** |
| **Оставленные отзывы** | **+** (поощряет фидбек) |
| **Процент открытых споров** | **-** (сильно) |
| **Процент проигранных споров** | **-** (очень сильно) |

**Влияние Buyer Score:**
- **Высокий Score:** Доступ к эксклюзивным предложениям, персональные скидки, участие в бета-тестировании новых функций.
- **Низкий Score:** Ограничение на количество одновременно открытых споров, возможная необходимость предоплаты при заказе дорогих товаров.

### 3. Уровни Верификации (Verification Tiers)

**Концепция:** Публичные значки, подтверждающие уровень доверия к продавцу. Проходятся по желанию в Seller Bot.

| Уровень | Требования | Значок | Преимущества |
| :--- | :--- | :--- | :--- |
| **Verified Email** | Подтвердить email по ссылке. | `📧` | Базовый уровень доверия. |
| **Verified Phone** | Подтвердить номер телефона по SMS. | `📱` | Повышает доверие покупателей. |
| **Verified Identity** | Пройти KYC-проверку через сторонний сервис (например, Sumsub): загрузить фото документа и селфи. | `🛡️ ID Verified` | Максимальный уровень доверия. Дает +0.5 к `Seller Score`. Обязателен для вывода крупных сумм. |

### 4. Публичный Профиль Продавца

**Концепция:** В Mirror Bot при просмотре товара можно нажать на рейтинг продавца и перейти в его публичный профиль.

**Содержимое профиля:**
```
👤 Профиль Продавца: SellerShop

🏆 Top Seller  🛡️ ID Verified

⭐ Рейтинг: 4.9/5 (на основе 258 оценок)
📈 Продаж: 1,450
⏳ На платформе: 380 дней

💬 Отзывы (Последние 5):

★★★★★ (от @user123)
"Все отлично, товар соответствует описанию!"

★★★★★ (от @user456)
"Быстро и качественно. Рекомендую."

[Показать все отзывы]
[Смотреть все товары продавца]
```
Эта страница становится главным инструментом для покупателя при принятии решения о покупке у незнакомого продавца.

## 20. (Новый) Модуль: Антифрод и Безопасность
## Расширенная Система Антифрода и Безопасности

**Задача:** Создать многоуровневую, проактивную систему безопасности, которая защищает платформу и её пользователей от мошенничества, злоупотреблений и некачественных товаров. Система должна работать в реальном времени, анализируя поведение, транзакции и контент.

**Философия:** "Доверяй, но проверяй". Вместо реакции на инциденты — их предотвращение.

---

### 1. User Trust Score — Динамический Рейтинг Доверия

**Концепция:** Каждому пользователю (покупателю и продавцу) присваивается внутренний, невидимый ему **Trust Score** (от 0 до 100). Этот скор влияет на лимиты, доступные функции и уровень проверок.

| Фактор | Влияние на Trust Score | Пример |
| :--- | :--- | :--- |
| **Возраст аккаунта** | **+** | +1 балл за каждые 30 дней на платформе. |
| **История покупок/продаж** | **+** | +2 балла за каждый успешный заказ без споров. |
| **Верификация** | **+** | +15 баллов за верифицированный email/телефон. |
| **Частые споры** | **-** | -10 баллов за каждый проигранный спор. |
| **Подозрительные IP/устройства** | **-** | -20 баллов за вход с IP из черного списка. |
| **Жалобы от других** | **-** | -5 баллов за каждую подтвержденную жалобу. |

**Применение Trust Score:**

- **Низкий Trust Score (< 30):**
    - Холд средств продавца увеличивается до 72 часов.
    - Лимит на вывод средств — $50 в день.
    - Все новые товары отправляются на ручную модерацию.
- **Средний Trust Score (30-70):**
    - Стандартные условия.
- **Высокий Trust Score (> 70):**
    - Холд средств продавца сокращается до 6 часов.
    - Автоматическое одобрение новых товаров (выборочная проверка).
    - Доступ к моментальным выплатам.

### 2. Real-time Transaction Monitoring — Мониторинг Транзакций

**Концепция:** Все финансовые операции проходят через систему правил, которая ищет аномалии.

| Правило | Описание | Действие |
| :--- | :--- | :--- |
| **Правило "Первый платеж"** | Первый платеж нового пользователя на крупную сумму. | **Soft-decline:** Заморозить платеж, запросить у пользователя дополнительное подтверждение (например, код из email). |
| **Правило "Цепочка пополнений"** | Пользователь пополняет баланс и сразу же пытается вывести деньги на другой кошелек. | **Hard-decline:** Блокировать вывод, создать тикет для ручной проверки `finance` отделом. Признак отмывания средств. |
| **Правило "Скорострел"** | Слишком много покупок за короткий промежуток времени с одного аккаунта. | **Alert:** Уведомить `admin`, возможно, аккаунт украден и с него "сливают" баланс. |
| **Правило "Нетипичная география"** | Покупка совершается с IP-адреса, который сильно отличается от обычного для этого пользователя (например, всегда был из Германии, а тут — из Вьетнама). | **Challenge:** Запросить 2FA-код или подтверждение по email перед завершением покупки. |

### 3. Content & Behavior Analysis — Анализ Контента и Поведения

**Концепция:** Автоматический анализ текста и действий для выявления подозрительной активности.

| Анализ | Описание | Действие |
| :--- | :--- | :--- |
| **Анализ описаний товаров** | Поиск стоп-слов (`взломан`, `украден`, `брут`, `гарантия 100%`) в новых товарах. | Отправить товар на принудительную ручную модерацию. Понизить `Trust Score` продавца. |
| **Анализ переписки в спорах** | Поиск оскорблений, угроз, попыток увести общение за пределы платформы. | Уведомить модератора, прикрепить к тикету флаг `[Нарушение правил]`. |
| **Анализ паттернов регистрации** | Обнаружение массовой регистрации аккаунтов с похожими именами или с одного IP-адреса. | Автоматически заблокировать новые аккаунты, уведомить `admin` о возможной атаке ботов. |

### 4. Alerting & Case Management — Система Оповещений и Управления Инцидентами

**Концепция:** Все подозрительные события не просто блокируются, а попадают в единый интерфейс в Admin Panel для расследования.

- **Раздел "Security" в Admin Panel:**
    - **Дашборд:** Ключевые метрики (кол-во заблокированных транзакций, пользователей с низким Trust Score, активных инцидентов).
    - **Очередь инцидентов:** Список всех событий, требующих внимания (`[Transaction #123]`, `[User @spammer]`).
    - **Карточка инцидента:** Полная информация о событии, все связанные данные (пользователи, IP, транзакции), инструменты для расследования (проверить IP, посмотреть историю действий) и кнопки для принятия решения (`[Заблокировать пользователя]`, `[Одобрить транзакцию]`, `[Закрыть инцидент]`).

## 21. (Новый) Модуль: Умные Уведомления
## Новый Модуль: Smart Notifications — Умные Уведомления

**Задача:** Превратить уведомления из простого информирования в мощный инструмент маркетинга, удержания и повышения качества сервиса. Система должна отправлять правильное сообщение правильному пользователю в правильное время, основываясь на его поведении и статусе.

**Философия:** "Меньше спама, больше пользы". Каждое уведомление должно быть ценным для получателя.

---

### 1. Архитектура Системы

**Компоненты:**
1.  **Event Bus (Kafka/RabbitMQ):** Все события в системе (регистрация, покупка, смена статуса заказа, новый товар) публикуются в шину событий.
2.  **Notification Engine (Python/Go):** Сервис, который слушает шину событий. Внутри него — набор правил и триггеров.
3.  **Message Templates:** Хранилище шаблонов сообщений на разных языках с поддержкой переменных (имя пользователя, название товара, цена).
4.  **Delivery Service:** Сервис, отвечающий за доставку уведомления конкретному пользователю в нужный бот (Mirror, Seller, etc.) с учетом его настроек (язык, часовой пояс, "не беспокоить").

### 2. Триггерные Уведомления для Покупателей

Эти уведомления направлены на повышение конверсии и удержание покупателей.

| Триггер | Условие | Сообщение | Цель |
| :--- | :--- | :--- | :--- |
| **Брошенная корзина** | Пользователь просмотрел карточку товара, но не купил его в течение 3 часов. | `⏳ Вы интересовались [Название товара]. Он ещё в наличии. Возможно, вас что-то смутило? [Купить сейчас] [Задать вопрос]` | Вернуть сомневающихся пользователей. |
| **Снижение цены в Wishlist** | Цена на товар из списка желаний пользователя снизилась более чем на 5%. | `💸 Цена снижена! Товар [Название товара] из вашего вишлиста теперь стоит [Новая цена] вместо [Старая цена].` | Стимулировать отложенный спрос. |
| **Возвращение в наличие** | Товар из списка желаний, которого не было в наличии, снова появился. | `✅ Снова в наличии! Товар [Название товара] из вашего вишлиста снова можно купить.` | Вернуть ушедших пользователей. |
| **Персональная рекомендация** | Пользователь не заходил в бот более 7 дней. | `👋 [Имя], мы скучали! Специально для вас мы подобрали несколько товаров на основе ваших прошлых покупок. [Посмотреть подборку]` | Напомнить о себе, повысить LTV. |
| **Запрос отзыва** | Через 24 часа после успешной покупки. | `⭐ Как вам [Название товара]? Пожалуйста, оцените вашу покупку. Это поможет другим покупателям и займет 15 секунд.` | Собрать больше оценок, улучшить систему репутации. |

### 3. Сервисные Уведомления для Продавцов

Эти уведомления помогают продавцам лучше управлять своим магазином и быстрее реагировать на события.

| Триггер | Условие | Сообщение | Цель |
| :--- | :--- | :--- | :--- |
| **Низкий остаток товара** | Количество определенного товара стало меньше 3 штук. | `📉 Заканчивается товар! Осталось всего [Кол-во] шт. товара [Название товара]. Не забудьте пополнить запасы.` | Предотвратить out-of-stock. |
| **Товар "залежался"** | Товар не продается более 30 дней. | `🤔 Товар [Название товара] не продается уже 30 дней. Возможно, стоит пересмотреть цену или описание? Средняя цена на рынке: [Рыночная цена].` | Помочь продавцу оптимизировать ассортимент. |
| **Новый отзыв** | Покупатель оставил отзыв (хороший или плохой). | `💬 Новый отзыв о товаре [Название товара] ([Кол-во звезд] звезд). [Читать отзыв]` | Быстрая обратная связь. |
| **Ежедневная/Еженедельная сводка** | Каждый день в 9:00 или каждый понедельник. | `📊 Ваша сводка за [Период]: Продаж: [Кол-во], Выручка: [Сумма], Новых отзывов: [Кол-во].` | Держать продавца в курсе дел. |

### 4. Управление Уведомлениями

**Концепция:** Дать пользователям и продавцам полный контроль над тем, что и когда они получают.

- **В Mirror Bot (для покупателей):**
    - Раздел `Профиль → ⚙️ Настройки уведомлений`.
    - Переключатели: `[✅] Рекомендации`, `[✅] Снижение цен`, `[✅] Новости платформы`.
- **В Seller Mini App (для продавцов):**
    - Раздел `Настройки → Уведомления`.
    - Переключатели для каждого типа уведомлений (низкий остаток, новый отзыв и т.д.).
    - Возможность установить "тихие часы" (например, с 22:00 до 09:00), когда приходят только критически важные уведомления (новый спор, вывод средств).

Эта система превращает уведомления из раздражающего фактора в полезный и персонализированный сервис, повышая ценность всей платформы.

## 22. Приоритеты разработки (v18) {#22}

**MVP (Minimum Viable Product) — 2-3 недели**

1.  **Ядро системы:** База данных, базовые модели SQLAlchemy, `users`, `sellers`, `products`, `orders`.
2.  **Seller Mini App (v1):** Авторизация, просмотр баланса, ручное добавление/редактирование товаров (без файлов).
3.  **Mirror Bot (v1):** Регистрация, просмотр категорий/товаров (текстом), пополнение баланса (ручное), покупка.
4.  **Admin Panel (v1):** Логин, ручное зачисление средств, просмотр пользователей и заказов.

**Post-MVP (Следующие 4-6 недель)**

1.  **Система Репутации (v1):** Расчет и отображение `Seller Score`, отзывы после покупки.
2.  **Инструменты продавца (v1):** Массовый импорт из CSV, режим "Отпуск".
3.  **Улучшения Mirror Bot (v1):** Визуальные карточки товаров, вишлист.
4.  **Система Антифрода (v1):** `User Trust Score` (базовая версия), мониторинг транзакций (правила "Первый платеж" и "Цепочка пополнений").
5.  **Платежные шлюзы:** Интеграция BTCPay/Helecat.

**Full Product (Следующие 2-3 месяца)**

1.  **Умные Уведомления (v1):** Триггеры "Брошенная корзина" и "Снижение цены в Wishlist".
2.  **Полная система Антифрода:** `Case Management` в Admin Panel, все правила мониторинга.
3.  **Полная система Репутации:** Верификация (KYC), `Buyer Score`.
4.  **Все остальные боты:** Marketer, Support, Worker, Main.
5.  **Полный функционал Admin Panel и Seller Mini App.**
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


---

# Newlookup — Готовые промты для Cursor v4

**Версия:** 4.0 (для v20)
**Дата:** 13.03.2026

> **Инструкция:** Перед каждым промтом в Cursor нажми `@`, выбери файл `newlookup_srs_v20_FINAL.md` и `database_schema_v2.sql`. Это даст AI полный контекст. Затем скопируй и вставь промт.

---

## Фаза 1: Ядро системы (Обновление до v20)

(Промты 1-5 из v3 остаются актуальными, но нужно обновить модели)

### Промт 6 (Обновление): Модели БД — Пользователи (user_related.py)

```
Перепиши модели в `app/db/models/user_related.py` согласно новой схеме `database_schema_v2.sql`. Основные изменения:
- В `User` добавь `trust_score: SmallInteger`.
- В `Seller` замени `rating` на `seller_score: Numeric(4,1)` и добавь `verification_tier: String(16)`.
- Убери `loyalty_level` из `User`.
```

### Промт 7 (Обновление): Модели БД — Товары (product_related.py)

```
Перепиши модели в `app/db/models/product_related.py` согласно новой схеме `database_schema_v2.sql`. Основные изменения:
- В `Order` добавь `parent_order_id: BigInteger` (FK на саму себя) для поддержки корзины.
```

---

## Фаза 2: Новые модули v20

### Промт 8 (Новый): Модели БД — Новые модули (system_related.py)

```
Добавь в `app/db/models/system_related.py` новые SQLAlchemy ORM модели согласно `database_schema_v2.sql`:

1.  **Coupon**: таблица `coupons`.
2.  **WishlistItem**: таблица `wishlist_items`.
3.  **ShoppingCart**: таблица `shopping_carts`.
4.  **CartItem**: таблица `cart_items`.
5.  **Notification**: таблица `notifications`.
6.  **AnalyticsEvent**: таблица `analytics_events`.

Создай все необходимые relationships.
```

### Промт 9 (Новый): Сервис Купонов (services/promo_service.py)

```
Создай файл `app/services/promo_service.py`. В нем реализуй класс `PromoService` со следующими методами:

- `__init__(self, db: AsyncSession)`
- `async def validate_coupon(self, code: str, user_id: int, cart_items: list) -> dict`: Проверяет купон и возвращает словарь с результатом (`is_valid`, `discount_amount`, `error_message`).
- `async def apply_coupon(self, code: str, order_id: int, user_id: int)`: Применяет купон к заказу, создает запись в `coupon_uses`.
- `async def create_coupon(self, coupon_data: dict) -> Coupon`: Создает новый купон в БД.
```

### Промт 10 (Новый): Логика Корзины (services/cart_service.py)

```
Создай файл `app/services/cart_service.py`. Реализуй класс `CartService`:

- `__init__(self, db: AsyncSession)`
- `async def add_to_cart(self, user_id: int, product_id: int, quantity: int = 1)`
- `async def get_cart(self, user_id: int) -> ShoppingCart`
- `async def clear_cart(self, user_id: int)`
- `async def checkout(self, user_id: int) -> Order`: Создает родительский заказ и дочерние под-заказы для каждого продавца в корзине.
```

### Промт 11 (Новый): Хендлеры Корзины (bots/mirror_bot/handlers/cart_handlers.py)

```
Создай файл `app/bots/mirror_bot/handlers/cart_handlers.py`. Напиши хендлеры для `aiogram 3.x` для следующих команд:

- `[🛒 Добавить в корзину]` (CallbackQuery): использует `CartService.add_to_cart`.
- `[🛒 Корзина]` (Message): использует `CartService.get_cart` и показывает содержимое корзины.
- `[✅ Оплатить всё]` (CallbackQuery): использует `CartService.checkout`.
```

### Промт 12 (Новый): Хендлеры Вишлиста (bots/mirror_bot/handlers/wishlist_handlers.py)

```
Создай файл `app/bots/mirror_bot/handlers/wishlist_handlers.py`. Напиши хендлеры для:

- `[❤️ В вишлист]` (CallbackQuery): добавляет товар в `wishlist_items`.
- `[❤️ Вишлист]` (Message): показывает список товаров в вишлисте.
```

### Промт 13 (Новый): Фоновая задача для брошенных корзин (tasks/retention_tasks.py)

```
Создай файл `app/tasks/retention_tasks.py`. Напиши Celery-таску `check_abandoned_carts`, которая:

1.  Запускается каждые 30 минут.
2.  Находит корзины со статусом `active` и `updated_at` > 1 часа назад.
3.  Меняет их статус на `abandoned`.
4.  Отправляет пользователю уведомление `ABANDONED_CART_1H` через NotificationService.
```

### Промт 14 (Новый): Сервис Уведомлений (services/notification_service.py)

```
Создай файл `app/services/notification_service.py`. Реализуй класс `NotificationService`:

- `__init__(self, bot: Bot, db: AsyncSession)`
- `async def send_notification(self, user_id: int, event_code: str, **kwargs)`: 
  - Находит текст уведомления по `event_code` в `notifications_catalog.md` (представь, что он загружен в словарь).
  - Форматирует текст с помощью `kwargs`.
  - Отправляет сообщение пользователю через `bot.send_message`.
  - Сохраняет уведомление в таблице `notifications`.
```

### Промт 15 (Новый): API для Аналитики (web/admin/api/v1/analytics.py)

```
Создай файл `app/web/admin/api/v1/analytics.py`. Напиши эндпоинт для FastAPI, который возвращает ключевые метрики для дашборда в Admin Panel:

- `GET /api/v1/analytics/dashboard`
- Считает: `DAU`, `WAU`, `MAU`, `Total Revenue`, `New Users`, `Sales Count` за последние 24ч/7д/30д.
- Возвращает данные в формате JSON, готовом для отрисовки графиков.
```


---

# Тест-план v2 — E2E Сценарии

**Задача:** Описать сквозные (End-to-End) сценарии для тестирования критически важных пользовательских путей. Тесты должны выполняться с использованием `pytest` и `aiogram.dispatcher.filters.logic.LogicFilter`.

---

### 1. E2E Сценарий: Успешная покупка товара "In Stock" с использованием купона

**Цель:** Проверить полный цикл от регистрации до получения товара, включая применение скидки.

| Шаг | Действие | Ожидаемый результат |
| :--- | :--- | :--- |
| 1 | **Setup:** Создать в БД тестового продавца, товар "Test Product" ($100) и публичный купон `TEST10` на 10%. | Объекты успешно созданы. |
| 2 | **Регистрация:** Эмулировать нового пользователя, отправляющего `/start` в Mirror Bot. | Пользователь создан в БД, получил приветственное сообщение. |
| 3 | **Пополнение:** Эмулировать успешное пополнение баланса на $100. | Баланс пользователя в БД равен 100. |
| 4 | **Добавление в корзину:** Эмулировать добавление "Test Product" в корзину. | В `cart_items` появилась запись. |
| 5 | **Применение купона:** Эмулировать ввод промокода `TEST10` в корзине. | Система отвечает, что скидка 10% применена, итоговая сумма $90. |
| 6 | **Оплата:** Эмулировать нажатие кнопки "Оплатить". | Создан заказ на сумму $90. Баланс пользователя списан до $10. Продавцу зачислено `90 * (1 - commission)`. |
| 7 | **Получение товара:** Проверить, что пользователь получил сообщение с данными товара. | Сообщение получено. |
| 8 | **Teardown:** Удалить созданные тестовые данные. | БД очищена. |

---

### 2. E2E Сценарий: Открытие и разрешение спора в пользу покупателя

**Цель:** Проверить полный цикл работы системы разрешения споров.

| Шаг | Действие | Ожидаемый результат |
| :--- | :--- | :--- |
| 1 | **Setup:** Создать покупателя, продавца, и выполненный заказ. | Объекты успешно созданы. |
| 2 | **Открытие спора:** Покупатель нажимает "Открыть спор" по заказу. | Создана запись в таблице `disputes`. Продавцу и администратору уходят уведомления. |
| 3 | **Ответ продавца:** Продавец отвечает в споре (эмуляция). | Сообщение добавлено в `dispute_messages`. Покупатель уведомлен. |
| 4 | **Решение модератора:** Администратор (модератор) решает спор в пользу покупателя. | Статус спора меняется на `RESOLVED_BUYER`. Сумма заказа возвращается на баланс покупателя. Рейтинг продавца снижается. |
| 5 | **Проверка балансов:** Проверить баланс покупателя и продавца. | Баланс покупателя увеличился на сумму заказа, у продавца — уменьшился. |
| 6 | **Teardown:** Удалить тестовые данные. | БД очищена. |

---

### 3. E2E Сценарий: Срабатывание уведомления о брошенной корзине

**Цель:** Проверить, что фоновая задача корректно находит и обрабатывает брошенные корзины.

| Шаг | Действие | Ожидаемый результат |
| :--- | :--- | :--- |
| 1 | **Setup:** Создать пользователя и добавить товар в его корзину. | Запись в `cart_items` создана. |
| 2 | **Ожидание:** Изменить `updated_at` в `shopping_carts` на 2 часа назад. | - |
| 3 | **Запуск задачи:** Вручную запустить Celery-таску `check_abandoned_carts`. | Статус корзины меняется на `abandoned`. |
| 4 | **Проверка уведомления:** Проверить, что пользователь получил уведомление `ABANDONED_CART_1H`. | Сообщение получено (через mock `bot.send_message`). Запись в `notifications` создана. |
| 5 | **Teardown:** Удалить тестовые данные. | БД очищена. |


---

