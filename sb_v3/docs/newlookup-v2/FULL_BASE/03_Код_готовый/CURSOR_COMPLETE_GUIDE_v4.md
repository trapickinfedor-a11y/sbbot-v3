# CURSOR COMPLETE GUIDE — newlookup v24
## Полная инструкция для реализации проекта в Cursor
### Версия 4.0 | Написана после прочтения каждого файла проекта

---

## ЧАСТЬ 1 — АРХИТЕКТУРА СИСТЕМЫ

### 1.1 Что это за система

**newlookup** — это мультибот-маркетплейс на Telegram. Покупатели покупают цифровые товары и услуги через зеркальные боты. Продавцы управляют своим стоком через seller_bot. Воркеры выполняют заказы через support_bot. Маркетологи привлекают покупателей через реферальные ссылки.

### 1.2 Полная структура проекта

```
newlookup_v2_work/
├── shared/                          # Общий код для всех ботов
│   ├── database/
│   │   ├── models.py                # ВСЕ SQLAlchemy модели (40+ классов)
│   │   └── database.py              # Async engine, get_session
│   ├── config.py                    # Общие настройки
│   ├── services/
│   │   ├── admin_notification_service.py
│   │   ├── bot_pool.py              # Пул ботов для рассылки
│   │   ├── log_channel_service.py   # Логирование в Telegram-канал
│   │   ├── notification_log_service.py
│   │   └── order_notification_service.py
│   └── utils/
│       ├── chat_filter.py           # Фильтр контактных данных
│       └── chat_render.py           # Рендер истории чата
│
├── mirror_bot/                      # Бот покупателя (может быть несколько)
│   ├── bot.py                       # Инициализация бота
│   ├── config.py                    # Конфиг mirror_bot
│   ├── handlers/
│   │   ├── start.py                 # /start, выбор языка, правила
│   │   ├── profile.py               # Профиль, реферальная система
│   │   ├── payment.py               # Пополнение баланса (CryptoPay/Cryptomus)
│   │   ├── products.py              # Каталог товаров, покупка
│   │   ├── buyer_orders.py          # Мои заказы
│   │   ├── buyer_chat.py            # Чат с воркером
│   │   ├── support.py               # Тикеты поддержки
│   │   ├── banks.py                 # Банки (услуга)
│   │   ├── accounts.py              # Аккаунты (услуга)
│   │   ├── cc.py                    # CC (услуга)
│   │   ├── fullz.py                 # Fullz (услуга)
│   │   ├── brute_bank.py            # Brute bank (услуга)
│   │   ├── education.py             # Образование (услуга)
│   │   ├── esim.py                  # eSIM (услуга)
│   │   ├── documents.py             # Документы (услуга)
│   │   ├── addinfo.py               # Дополнительная инфо (услуга)
│   │   ├── another_services.py      # Другие услуги
│   │   ├── credit_reports.py        # Кредитные отчёты
│   │   ├── lookup/                  # Lookup услуги
│   │   │   ├── main.py
│   │   │   ├── ssn.py
│   │   │   ├── phone.py
│   │   │   ├── bank_lookup.py
│   │   │   └── others.py
│   │   ├── messages.py              # Обработка входящих сообщений
│   │   ├── rules.py                 # Правила использования
│   │   └── fallback.py              # Неизвестные команды
│   ├── services/
│   │   ├── user_service.py          # CRUD пользователей
│   │   ├── product_service.py       # Покупка товаров (КРИТИЧНО)
│   │   ├── order_service.py         # Управление заказами
│   │   ├── payment_service.py       # Платёжные операции
│   │   ├── payment_monitor.py       # Мониторинг платежей
│   │   ├── crypto_pay.py            # CryptoPay API
│   │   ├── cryptomus.py             # Cryptomus API
│   │   ├── support_service.py       # Тикеты поддержки
│   │   ├── file_service.py          # Работа с файлами
│   │   ├── product_delivery_service.py  # Доставка товаров
│   │   ├── support_notification_service.py
│   │   ├── validator.py             # Валидация данных
│   │   └── parser.py                # Парсинг данных
│   ├── keyboards/
│   │   ├── inline.py                # Inline клавиатуры
│   │   └── reply.py                 # Reply клавиатуры
│   ├── middlewares/
│   │   ├── mirror_bot.py            # Middleware для multi-bot
│   │   ├── session.py               # DB сессия
│   │   ├── language.py              # Язык пользователя
│   │   ├── user_update.py           # Обновление данных пользователя
│   │   ├── ban_check.py             # Проверка бана
│   │   ├── bot_status_check.py      # Проверка статуса бота
│   │   ├── debug_logger.py          # Логирование
│   │   └── reply_keyboard_cancel.py
│   ├── states/
│   │   ├── order.py                 # FSM состояния заказа
│   │   ├── banks.py                 # FSM состояния банков
│   │   ├── accounts.py              # FSM состояния аккаунтов
│   │   └── fullz.py                 # FSM состояния fullz
│   └── constants/
│       ├── texts_ru.py              # Русские тексты (1300 строк)
│       ├── texts_en.py              # Английские тексты
│       ├── texts_zh.py              # Китайские тексты
│       ├── buttons_ru.py            # Русские кнопки
│       ├── buttons_en.py            # Английские кнопки
│       ├── buttons_zh.py            # Китайские кнопки
│       ├── language_loader.py       # Загрузчик языков
│       ├── bank_data.py             # Данные банков
│       ├── states_data.py           # Данные штатов
│       ├── prices.py                # Цены услуг
│       └── product_descriptions.py  # Описания товаров
│
├── seller_bot/                      # Бот продавца
│   ├── bot.py
│   ├── config.py
│   ├── handlers/
│   │   ├── start.py                 # Регистрация, главное меню
│   │   ├── orders.py                # Заказы продавца (КРИТИЧНО: не показывать buyer_user_id)
│   │   ├── chat.py                  # Чат с покупателем через воркера
│   │   ├── stock.py                 # Управление стоком банков
│   │   ├── cc_stock.py              # Управление CC стоком
│   │   ├── brute_bank.py            # Brute bank заказы
│   │   └── profile.py               # Профиль продавца
│   ├── services/
│   │   ├── seller_service.py        # CRUD продавцов
│   │   ├── stock_service.py         # Управление стоком
│   │   └── cc_stock_service.py      # CC сток
│   ├── keyboards/
│   │   └── inline.py
│   └── middlewares/
│       ├── seller_auth.py           # Авторизация продавца
│       └── database.py
│
├── support_bot/                     # Бот воркера (и модерации)
│   ├── bot.py
│   ├── config.py
│   ├── handlers/
│   │   ├── start.py                 # Главное меню воркера
│   │   ├── orders.py                # Доступные заказы, взять заказ
│   │   ├── work_orders.py           # Выполнение заказов, отправка результата
│   │   ├── files.py                 # Отправка файлов воркером (КРИТИЧНО: проверка блокировки)
│   │   ├── seller_orders.py         # Просмотр заказов продавцов (для модераторов)
│   │   ├── seller_moderation.py     # Модерация банков продавцов
│   │   ├── upload_product.py        # Загрузка товаров воркером
│   │   ├── bulk_orders.py           # Массовые заказы
│   │   ├── complaints.py            # Жалобы
│   │   ├── history.py               # История заказов
│   │   ├── profile.py               # Профиль воркера
│   │   ├── statistics.py            # Статистика (сегодня/неделя/месяц)
│   │   └── user_info.py             # Инфо о пользователе (для модераторов)
│   ├── services/
│   │   ├── order_service.py         # Логика заказов воркера
│   │   ├── worker_service.py        # CRUD воркеров
│   │   ├── balance_service.py       # Баланс воркера
│   │   ├── order_delivery_service.py # Доставка результата
│   │   ├── order_channel_service.py  # Канал заказов
│   │   ├── notification_service.py   # Уведомления
│   │   ├── worker_notification_service.py
│   │   ├── order_notification_service.py
│   │   ├── complaint_service.py     # Жалобы
│   │   └── support_logger.py        # Логирование
│   ├── keyboards/
│   │   └── inline.py
│   └── middlewares/
│       ├── worker_auth.py           # Авторизация воркера
│       └── database.py
│
├── marketer_bot/                    # Бот маркетолога
│   ├── bot.py
│   ├── config.py
│   ├── handlers/
│   │   ├── start.py                 # Дашборд маркетолога
│   │   └── withdrawal.py            # Вывод средств (FSM: сумма → сеть → кошелёк → подтверждение)
│   ├── keyboards/
│   │   └── main_kb.py
│   └── services/
│       └── marketer_service.py      # Комиссии, статистика, вывод
│
├── main_bot/                        # Главный бот (управление зеркальными ботами)
│   └── app/
│       ├── handlers/
│       │   ├── start.py             # /start
│       │   └── token.py             # Управление токенами ботов
│       ├── services/
│       │   └── mirror_bot.py        # Создание/управление зеркальными ботами
│       └── middlewares/
│           ├── ban_check.py
│           ├── error_handler.py
│           └── logging.py
│
├── web_panel/                       # FastAPI панель управления
│   ├── main.py                      # Инициализация FastAPI, все роутеры
│   ├── auth.py                      # JWT авторизация
│   ├── database.py                  # DB подключение
│   └── api/
│       ├── auth.py                  # POST /login, POST /refresh
│       ├── dashboard.py             # GET /stats, /recent-orders, /recent-users
│       ├── analytics.py             # Аналитика: summary, by-category, timeline, growth
│       ├── users.py                 # CRUD пользователей + бан + баланс
│       ├── orders.py                # CRUD заказов + статистика
│       ├── workers.py               # CRUD воркеров + статистика + категории
│       ├── sellers.py               # CRUD продавцов + approve/toggle
│       ├── seller_crm.py            # CRM: отчёты, чаты, история
│       ├── seller_moderation.py     # Модерация банков продавцов
│       ├── products.py              # CRUD товаров + категории + штаты
│       ├── banks.py                 # Банки
│       ├── bank_items.py            # Позиции банков
│       ├── marketers.py             # CRUD маркетологов
│       ├── deposits.py              # Депозиты
│       ├── complaints.py            # Жалобы
│       ├── support_tickets.py       # Тикеты поддержки
│       ├── broadcasts.py            # Рассылки
│       ├── announcements.py         # Объявления
│       ├── bots.py                  # Управление ботами
│       ├── admins.py                # Управление администраторами
│       ├── audit.py                 # Audit log
│       ├── analytics.py             # Аналитика
│       ├── reports.py               # Отчёты
│       ├── accounts.py              # Аккаунты
│       ├── cc.py                    # CC
│       ├── cc_catalog.py            # CC каталог
│       ├── catalog.py               # Каталог
│       ├── categories.py            # Категории
│       ├── checks.py                # Чеки
│       ├── education.py             # Образование
│       ├── esim.py                  # eSIM
│       ├── files.py                 # Файлы
│       ├── imports.py               # Импорт данных
│       ├── service_prices.py        # Цены услуг
│       ├── services.py              # Услуги
│       ├── stock.py                 # Сток
│       └── telegram_sync.py         # Синхронизация с Telegram
│
├── docker-compose.yml               # 8 сервисов: postgres, redis, main_bot, support_bot,
│                                    # seller_bot, marketer_bot, mirror_bot, web_panel
└── .env                             # Все переменные окружения
```

---

## ЧАСТЬ 2 — МОДЕЛИ БАЗЫ ДАННЫХ (40 классов)

### 2.1 Полный список моделей

| Модель | Таблица | Назначение |
|--------|---------|------------|
| `MirrorBot` | `mirror_bots` | Зеркальные боты покупателей |
| `User` | `users` | Покупатели |
| `Order` | `orders` | Заказы покупателей |
| `BulkOrderItem` | `bulk_order_items` | Позиции массовых заказов |
| `Worker` | `workers` | Воркеры |
| `WorkerStats` | `worker_stats` | Статистика воркеров |
| `Transaction` | `transactions` | Финансовые транзакции |
| `Product` | `products` | Товары продавцов |
| `ProductPurchase` | `product_purchases` | Покупки товаров |
| `Referral` | `referrals` | Реферальные связи |
| `SupportTicket` | `support_tickets` | Тикеты поддержки |
| `SupportMessage` | `support_messages` | Сообщения в тикетах |
| `Complaint` | `complaints` | Жалобы |
| `Broadcast` | `broadcasts` | Рассылки |
| `Report` | `reports` | Отчёты |
| `Seller` | `sellers` | Продавцы |
| `SellerBank` | `seller_banks` | Банки продавцов |
| `SellerOrder` | `seller_orders` | Заказы продавцов |
| `SellerChat` | `seller_chats` | Чаты продавцов |
| `BankPosition` | `bank_positions` | Позиции банков |
| `BankItem` | `bank_items` | Предметы банков |
| `ServicePrice` | `service_prices` | Цены услуг |
| `NotificationLog` | `notification_logs` | Логи уведомлений |
| `Admin` | `admins` | Администраторы |
| `AdminAuditLog` | `admin_audit_logs` | Audit log |
| `CCCategory` | `cc_categories` | Категории CC |
| `CCItem` | `cc_items` | CC предметы |
| `SellerCCItem` | `seller_cc_items` | CC предметы продавцов |
| `SellerCCOrder` | `seller_cc_orders` | CC заказы |
| `EducationCategory` | `education_categories` | Категории обучения |
| `EducationSubscription` | `education_subscriptions` | Подписки на обучение |
| `EducationManual` | `education_manuals` | Материалы обучения |
| `AccountCategory` | `account_categories` | Категории аккаунтов |
| `AccountItem` | `account_items` | Аккаунты |
| `AnotherServiceButton` | `another_service_buttons` | Кнопки доп. услуг |
| `BruteBankItem` | `brute_bank_items` | Brute bank предметы |
| `Marketer` | `marketers` | Маркетологи |
| `MarketerStats` | `marketer_stats` | Статистика маркетологов |
| `MarketerWithdrawal` | `marketer_withdrawals` | Выводы маркетологов |
| `LogChannel` | `log_channels` | Каналы логирования |
| `ProductImport` | `product_imports` | Импорт товаров |
| `Announcement` | `announcements` | Объявления |
| `AdminRole` | `admin_roles` | Роли администраторов |
| `SellerReport` | `seller_reports` | Отчёты CRM |

### 2.2 Ключевые поля Order (заказ покупателя)

```python
class Order(Base):
    id: int (PK)
    mirror_bot_id: int (FK → mirror_bots)
    user_id: int (FK → users)          # ← НИКОГДА не показывать продавцу/воркеру
    worker_id: Optional[int] (FK → workers)
    category: str                       # banks, accounts, cc, fullz, etc.
    service: Optional[str]
    state: Optional[str]                # US state
    status: str                         # pending, processing, completed, cancelled, disputed
    price: float
    worker_price: float                 # Выплата воркеру
    result_text: Optional[str]          # Результат от воркера
    result_file_id: Optional[str]       # Файл от воркера
    is_bulk: bool
    created_at: datetime
    completed_at: Optional[datetime]
    escrow_released: bool = False       # ← КРИТИЧНО: флаг идемпотентности выплаты
    auto_complete_at: Optional[datetime] # ← Таймер автозавершения
```

### 2.3 Ключевые поля Product (товар продавца)

```python
class Product(Base):
    id: int (PK)
    seller_id: int (FK → sellers)
    category: str
    state: Optional[str]
    name: str
    description: Optional[str]
    price: float
    is_available: bool = True
    is_active: bool = True              # ← Проверять при покупке
    moderation_status: str = "pending_moderation"  # ← Новое в v24
    moderation_comment: Optional[str]  # ← Новое в v24
    moderated_at: Optional[datetime]   # ← Новое в v24
    moderated_by: Optional[int]        # ← Новое в v24
    created_at: datetime
```

### 2.4 Ключевые поля Seller (продавец)

```python
class Seller(Base):
    id: int (PK)
    telegram_id: int (unique)
    username: Optional[str]
    name: str
    status: str                         # pending, active, blocked
    balance: float = 0.0
    total_earned: float = 0.0
    commission_rate: float = 0.15       # ← 15% платформы
    created_at: datetime
```

---

## ЧАСТЬ 3 — ПРАВИЛА БЕЗОПАСНОСТИ (ОБЯЗАТЕЛЬНО)

### 3.1 Анонимность покупателей

**ПРАВИЛО: Продавец и воркер НИКОГДА не видят данные покупателя.**

| Что скрывать | Где скрывать |
|---|---|
| `user_id` (Telegram ID) | `seller_bot/handlers/orders.py` |
| `username` покупателя | Везде в seller_bot и support_bot |
| Telegram-ник в чате | `shared/utils/chat_filter.py` |
| Контакты в сообщениях | `chat_filter.filter_message()` |

**Что продавец МОЖЕТ видеть:**
- Номер заказа (`order_id`)
- Категория и услуга
- Штат (US state)
- Сумма заказа
- Статус заказа
- Дата создания

**Что воркер МОЖЕТ видеть:**
- Номер заказа
- Категория и услуга
- Штат
- Цена воркера (его выплата)
- Дата создания

### 3.2 Фильтр контента (chat_filter.py)

Применяется в:
- `mirror_bot/handlers/buyer_chat.py` — при отправке сообщения покупателем
- `seller_bot/handlers/chat.py` — при отправке сообщения продавцом
- `support_bot/handlers/work_orders.py` — при отправке текста воркером
- `support_bot/handlers/files.py` — при отправке файлов воркером

**Что фильтруется:**
```python
@username → [КОНТАКТ СКРЫТ]
https://... → [ССЫЛКА СКРЫТА]
t.me/... → [ССЫЛКА СКРЫТА]
+79991234567 → [ТЕЛЕФОН СКРЫТ]
email@domain.com → [EMAIL СКРЫТ]  # ← добавить в v24
discord#1234 → [КОНТАКТ СКРЫТ]   # ← добавить в v24
```

### 3.3 Модерация товаров

Все товары проходят через модератора:
1. Продавец добавляет товар → `moderation_status = "pending_moderation"`
2. Товар НЕ виден покупателям пока `moderation_status != "approved"`
3. Модератор проверяет: нет ли никнеймов продавца, контактов, рекламы
4. После approve → `moderation_status = "approved"`, товар появляется в каталоге
5. При изменении описания → снова `pending_moderation`

---

## ЧАСТЬ 4 — ФИНАНСОВАЯ ЛОГИКА

### 4.1 Флоу покупки товара (product_service.py)

```
Покупатель нажимает "Купить"
    ↓
SELECT product FOR UPDATE (блокировка строки)
    ↓
Проверить: product.is_available AND product.is_active AND product.moderation_status == "approved"
    ↓
Проверить: user.balance >= product.price
    ↓
user.balance -= product.price
    ↓
Создать Transaction(type="purchase", amount=-product.price)
    ↓
Создать ProductPurchase
    ↓
Уведомить продавца (без данных покупателя!)
    ↓
Уведомить покупателя
```

### 4.2 Флоу заказа услуги (order_service.py)

```
Покупатель оформляет заказ
    ↓
user.balance -= order.price (эскроу)
    ↓
Создать Order(status="pending")
    ↓
Отправить в канал заказов
    ↓
Воркер берёт заказ → status="processing"
    ↓
Воркер отправляет результат → status="completed"
    ↓
auto_complete_at = now() + 24h (таймер для покупателя)
    ↓
Если покупатель не открыл спор за 24h:
    worker.balance += order.worker_price
    seller.balance += seller_commission (если через продавца)
    Transaction(type="escrow_release", escrow_released=True)
```

### 4.3 Идемпотентность выплат (КРИТИЧНО)

```python
# В auto_complete.py — ВСЕГДА проверять флаг перед выплатой
async def release_escrow(order_id: int, session: AsyncSession):
    order = await session.get(Order, order_id, with_for_update=True)
    if order.escrow_released:
        return  # Уже выплачено — выходим
    order.escrow_released = True
    worker.balance += order.worker_price
    await session.commit()
```

### 4.4 Комиссии

| Кто | Комиссия | Когда |
|---|---|---|
| Платформа | 15% от суммы заказа | При выплате эскроу |
| Маркетолог | 5-10% от пополнения | При пополнении баланса покупателем |
| Продавец | Остаток после комиссии платформы | При выплате эскроу |

---

## ЧАСТЬ 5 — ПОРЯДОК РЕАЛИЗАЦИИ В CURSOR

### Этап 1: Настройка окружения

**Команды для запуска:**
```bash
# 1. Скопировать .env.example → .env и заполнить
cp .env.example .env

# 2. Запустить базу данных
docker-compose up -d postgres redis

# 3. Применить миграции
cd newlookup_v2_work
alembic upgrade head

# 4. Запустить все сервисы
docker-compose up -d
```

**Промт для Cursor:**
```
Открой файл docker-compose.yml и .env.example.
Проверь что все переменные окружения заполнены.
Убедись что все 8 сервисов (postgres, redis, main_bot, support_bot, 
seller_bot, marketer_bot, mirror_bot, web_panel) настроены правильно.
```

---

### Этап 2: Модели базы данных

**Файл:** `shared/database/models.py`

**Промт для Cursor:**
```
@shared/database/models.py @newlookup_srs_v24_FINAL.md

Добавь в models.py следующие изменения:

1. В класс Order добавь поля:
   escrow_released: Mapped[bool] = mapped_column(Boolean, default=False)
   auto_complete_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

2. В класс Product добавь поля:
   is_active: Mapped[bool] = mapped_column(Boolean, default=True)
   moderation_status: Mapped[str] = mapped_column(String(30), default="pending_moderation")
   moderation_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
   moderated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
   moderated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

3. Создай новую модель WorkerViolation:
   id, worker_id (FK→workers), order_id (FK→orders), 
   violation_type (String), message_text (Text), created_at (DateTime)

4. Создай новую модель SystemSetting:
   id, key (String unique), value (String), updated_at (DateTime)

Не меняй существующие поля. Добавь только новые.
```

---

### Этап 3: Миграция Alembic

**Файл:** `alembic/versions/v24_001_additions.py`

**Промт для Cursor:**
```
@alembic/versions/v24_001_additions.py @shared/database/models.py

Создай Alembic миграцию которая добавляет:

upgrade():
- ALTER TABLE orders ADD COLUMN escrow_released BOOLEAN DEFAULT FALSE
- ALTER TABLE orders ADD COLUMN auto_complete_at TIMESTAMP NULL
- ALTER TABLE products ADD COLUMN is_active BOOLEAN DEFAULT TRUE
- ALTER TABLE products ADD COLUMN moderation_status VARCHAR(30) DEFAULT 'pending_moderation'
- ALTER TABLE products ADD COLUMN moderation_comment TEXT NULL
- ALTER TABLE products ADD COLUMN moderated_at TIMESTAMP NULL
- ALTER TABLE products ADD COLUMN moderated_by BIGINT NULL
- CREATE TABLE worker_violations (id, worker_id, order_id, violation_type, message_text, created_at)
- CREATE TABLE system_settings (id, key VARCHAR UNIQUE, value VARCHAR, updated_at TIMESTAMP)
- INSERT INTO system_settings VALUES ('platform_fee', '0.15', now()), ('dispute_window_hours', '24', now())

downgrade():
- Обратные операции

Применить командой: alembic upgrade head
```

---

### Этап 4: Сервис покупки товаров (КРИТИЧНО)

**Файл:** `mirror_bot/services/product_service.py`

**Промт для Cursor:**
```
@mirror_bot/services/product_service.py @shared/database/models.py

Обнови метод purchase_product() чтобы:

1. Использовал SELECT FOR UPDATE для блокировки строки товара:
   result = await session.execute(
       select(Product).where(Product.id == product_id).with_for_update()
   )

2. Проверял ДО списания баланса:
   if not product.is_available:
       raise ValueError("Товар недоступен")
   if not product.is_active:
       raise ValueError("Товар деактивирован")
   if product.moderation_status != "approved":
       raise ValueError("Товар на модерации")
   if user.balance < product.price:
       raise ValueError("Недостаточно средств")

3. После списания создавал транзакцию:
   Transaction(type="purchase", amount=-product.price, user_id=user.id)

4. НЕ передавал user_id или username покупателя в уведомление продавцу.

Сохрани всю существующую логику, только добавь проверки.
```

---

### Этап 5: Заказы продавца (Анонимность)

**Файл:** `seller_bot/handlers/orders.py`

**Промт для Cursor:**
```
@seller_bot/handlers/orders.py @shared/database/models.py

В функции order_detail_handler() УДАЛИ строку:
f"👤 Buyer ID: <code>{order.buyer_user_id}</code>\n"

И ЗАМЕНИ на:
f"🔢 Order: #{order.id}\n"
f"📦 Category: {order.category}\n"
f"🏦 Service: {order.service or '—'}\n"
f"📍 State: {order.state or '—'}\n"
f"💰 Amount: ${order.price:.2f}\n"
f"📊 Status: {order.status}\n"
f"📅 Created: {order.created_at.strftime('%Y-%m-%d %H:%M')}\n"

ВАЖНО: Продавец НЕ должен видеть:
- user_id покупателя
- username покупателя
- Telegram ID покупателя
- Любые личные данные покупателя
```

---

### Этап 6: Фильтр контента воркеров

**Файл:** `shared/utils/chat_filter.py`

**Промт для Cursor:**
```
@shared/utils/chat_filter.py

Добавь в функцию filter_message() новые паттерны:

# Email адреса
text = re.sub(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[EMAIL СКРЫТ]", text)

# Discord
text = re.sub(r"\b\w{2,32}#\d{4}\b", "[КОНТАКТ СКРЫТ]", text)

# Skype
text = re.sub(r"skype:\s*\S+", "[КОНТАКТ СКРЫТ]", text, flags=re.I)

# WhatsApp
text = re.sub(r"whatsapp\s*:?\s*\+?\d+", "[КОНТАКТ СКРЫТ]", text, flags=re.I)

Также добавь функцию log_violation():
async def log_violation(session, worker_id: int, order_id: int, 
                        violation_type: str, message_text: str):
    violation = WorkerViolation(
        worker_id=worker_id,
        order_id=order_id,
        violation_type=violation_type,
        message_text=message_text[:500]
    )
    session.add(violation)
    await session.commit()
```

---

### Этап 7: Автозавершение заказов (Celery)

**Файл:** `shared/tasks/auto_complete.py` (НОВЫЙ ФАЙЛ)

**Промт для Cursor:**
```
@shared/database/models.py @shared/config.py

Создай новый файл shared/tasks/auto_complete.py:

from celery import Celery
from sqlalchemy import select
from shared.database.models import Order, Worker, Transaction
from shared.database.database import get_session_context

celery_app = Celery('newlookup', broker=settings.REDIS_URL)

@celery_app.task(bind=True, max_retries=3)
def release_escrow_task(self, order_id: int):
    """Идемпотентная выплата эскроу после автозавершения"""
    async with get_session_context() as session:
        # SELECT FOR UPDATE — блокировка от двойной выплаты
        order = await session.execute(
            select(Order).where(Order.id == order_id).with_for_update()
        )
        order = order.scalar_one_or_none()
        
        if not order or order.escrow_released:
            return  # Уже выплачено или заказ не найден
        
        if order.status != "completed":
            return  # Заказ не завершён
        
        # Выплата воркеру
        worker = await session.get(Worker, order.worker_id)
        worker.balance += order.worker_price
        
        # Флаг идемпотентности
        order.escrow_released = True
        
        # Транзакция
        session.add(Transaction(
            user_id=order.user_id,
            type="escrow_release",
            amount=order.worker_price,
            description=f"Escrow release for order #{order.id}"
        ))
        
        await session.commit()

# Beat расписание — проверять каждые 5 минут
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(300.0, check_auto_complete.s())

@celery_app.task
def check_auto_complete():
    """Проверить заказы с истёкшим таймером"""
    # Найти все completed заказы где auto_complete_at < now() и escrow_released = False
    # Для каждого вызвать release_escrow_task.delay(order.id)
    pass
```

---

### Этап 8: Модерация товаров (web_panel)

**Файл:** `web_panel/api/products.py`

**Промт для Cursor:**
```
@web_panel/api/products.py @shared/database/models.py

Добавь новые эндпоинты для модерации:

@router.get("/pending-moderation")
async def get_pending_products(db: AsyncSession = Depends(get_db)):
    """Список товаров ожидающих модерации"""
    result = await db.execute(
        select(Product).where(Product.moderation_status == "pending_moderation")
        .order_by(Product.created_at.asc())
    )
    return result.scalars().all()

@router.post("/{product_id}/approve")
async def approve_product(product_id: int, db: AsyncSession = Depends(get_db),
                          admin = Depends(get_current_admin)):
    product = await db.get(Product, product_id)
    product.moderation_status = "approved"
    product.moderated_at = datetime.utcnow()
    product.moderated_by = admin.id
    await db.commit()
    return {"status": "approved"}

@router.post("/{product_id}/reject")
async def reject_product(product_id: int, comment: str,
                         db: AsyncSession = Depends(get_db),
                         admin = Depends(get_current_admin)):
    product = await db.get(Product, product_id)
    product.moderation_status = "rejected"
    product.moderation_comment = comment
    product.moderated_at = datetime.utcnow()
    product.moderated_by = admin.id
    await db.commit()
    # Уведомить продавца о причине отказа
    return {"status": "rejected"}
```

---

### Этап 9: Нарушения воркеров (web_panel)

**Файл:** `web_panel/api/workers.py`

**Промт для Cursor:**
```
@web_panel/api/workers.py @shared/database/models.py

Добавь эндпоинты для нарушений воркеров:

@router.get("/{worker_id}/violations")
async def get_worker_violations(worker_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WorkerViolation)
        .where(WorkerViolation.worker_id == worker_id)
        .order_by(WorkerViolation.created_at.desc())
    )
    return result.scalars().all()

@router.get("/violations/recent")
async def get_recent_violations(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Последние нарушения всех воркеров для модератора"""
    result = await db.execute(
        select(WorkerViolation)
        .order_by(WorkerViolation.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()
```

---

### Этап 10: Тексты ботов (локализация)

**Файлы:** `mirror_bot/constants/texts_ru.py`, `texts_en.py`, `texts_zh.py`

**Промт для Cursor:**
```
@mirror_bot/constants/texts_ru.py

Добавь в класс BotTexts следующие тексты:

# Модерация товаров
PRODUCT_PENDING_MODERATION = "⏳ Товар на модерации. Ожидайте проверки."
PRODUCT_REJECTED = "❌ Товар отклонён модератором.\nПричина: {reason}"
PRODUCT_APPROVED = "✅ Товар одобрен и доступен покупателям."

# Споры
DISPUTE_WINDOW_OPEN = "⚠️ У вас есть {hours} часов чтобы открыть спор."
DISPUTE_OPENED = "🚨 Спор открыт. Модератор рассмотрит в течение 24 часов."
DISPUTE_WINDOW_CLOSED = "❌ Окно для спора закрыто. Заказ автоматически завершён."

# Автозавершение
ORDER_AUTO_COMPLETED = "✅ Заказ #{order_id} автоматически завершён. Средства выплачены."

# Нарушения воркера
WORKER_VIOLATION_WARNING = "⚠️ Обнаружена попытка передать контактные данные. Нарушение зафиксировано."
```

---

## ЧАСТЬ 6 — ПОЛНЫЙ ЧЕКЛИСТ ПЕРЕД ДЕПЛОЕМ

### 6.1 Безопасность

- [ ] Продавец не видит `user_id` покупателя (проверить `seller_bot/handlers/orders.py` строка ~93)
- [ ] Воркер не видит `username` покупателя (проверить `support_bot/handlers/work_orders.py`)
- [ ] `chat_filter.py` применяется во всех 4 местах (buyer_chat, seller_chat, work_orders, files)
- [ ] `chat_filter.py` фильтрует: @username, ссылки, телефоны, email, Discord
- [ ] JWT токены имеют срок жизни (проверить `web_panel/auth.py`)
- [ ] Rate limiting на API эндпоинтах
- [ ] Все пароли в `.env`, не в коде

### 6.2 Финансы

- [ ] `SELECT FOR UPDATE` в `product_service.py` при покупке
- [ ] Проверка `is_available AND is_active AND moderation_status == "approved"` перед покупкой
- [ ] Флаг `escrow_released` в модели Order
- [ ] Celery задача `release_escrow_task` идемпотентна
- [ ] Комиссия платформы 15% (проверить в `system_settings`)
- [ ] Комиссия маркетолога начисляется при пополнении, не при покупке

### 6.3 Модерация

- [ ] Новые товары получают `moderation_status = "pending_moderation"`
- [ ] Товары с `moderation_status != "approved"` не видны в каталоге
- [ ] При изменении описания товара — снова `pending_moderation`
- [ ] Модератор получает уведомление о новом товаре

### 6.4 Логика

- [ ] FSM состояния очищаются после завершения операции
- [ ] Все inline кнопки имеют обработчики
- [ ] Обработка ошибок во всех хендлерах (try/except)
- [ ] Логирование в Telegram-канал через `log_channel_service.py`

### 6.5 Производительность

- [ ] Индексы на `user_id`, `worker_id`, `status`, `created_at` в таблице orders
- [ ] Индекс на `moderation_status` в таблице products
- [ ] Redis кэш для часто запрашиваемых данных (цены услуг, настройки)
- [ ] Пагинация во всех списках (orders, products, users)

---

## ЧАСТЬ 7 — ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ (.env)

```env
# База данных
DATABASE_URL=postgresql+asyncpg://newlookup:password@postgres:5432/newlookup
POSTGRES_USER=newlookup
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=newlookup

# Redis
REDIS_URL=redis://redis:6379/0

# Боты
MAIN_BOT_TOKEN=your_main_bot_token
SUPPORT_BOT_TOKEN=your_support_bot_token
SELLER_BOT_TOKEN=your_seller_bot_token
MARKETER_BOT_TOKEN=your_marketer_bot_token

# Платежи
CRYPTOPAY_TOKEN=your_cryptopay_token
CRYPTOMUS_MERCHANT_ID=your_merchant_id
CRYPTOMUS_API_KEY=your_api_key

# Telegram каналы
ORDERS_CHANNEL_ID=-100xxxxxxxxxx      # Канал заказов для воркеров
LOG_CHANNEL_ID=-100xxxxxxxxxx         # Канал логов
ADMIN_TELEGRAM_ID=your_admin_id

# Web Panel
WEB_PANEL_SECRET_KEY=your_jwt_secret_key_min_32_chars
WEB_PANEL_PORT=8000

# Celery
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
```

---

## ЧАСТЬ 8 — КОМАНДЫ ДЛЯ CURSOR

### 8.1 Как добавлять контекст

В Cursor Chat нажми `@` и добавь файлы:
- `@models.py` — всегда при работе с БД
- `@newlookup_srs_v24_FINAL.md` — при вопросах о логике
- `@privacy_and_moderation.md` — при работе с безопасностью
- Конкретный файл который редактируешь

### 8.2 Шаблон промта для Cursor

```
@[файл_который_редактируешь] @models.py

Контекст: [краткое описание что делает этот файл]

Задача: [конкретная задача]

Требования:
1. [требование 1]
2. [требование 2]

НЕ делать:
- [что нельзя]
- [что нельзя]

Сохрани всю существующую логику, только добавь/измени указанное.
```

### 8.3 Промт для проверки безопасности

```
@seller_bot/handlers/orders.py @support_bot/handlers/work_orders.py @shared/utils/chat_filter.py

Проверь что:
1. В seller_bot/handlers/orders.py нет передачи user_id, username или любых данных покупателя продавцу
2. В support_bot/handlers/work_orders.py нет передачи данных покупателя воркеру
3. chat_filter.filter_message() вызывается перед отправкой любого сообщения от воркера покупателю

Если находишь нарушение — исправь и объясни что изменил.
```

### 8.4 Промт для проверки финансов

```
@mirror_bot/services/product_service.py @shared/tasks/auto_complete.py @models.py

Проверь что:
1. purchase_product() использует SELECT FOR UPDATE
2. Проверяется is_available AND is_active AND moderation_status == "approved"
3. release_escrow_task() проверяет флаг escrow_released перед выплатой
4. Нет возможности двойной выплаты

Если находишь проблему — исправь и объясни.
```

---

## ЧАСТЬ 9 — СТРУКТУРА ОТВЕТОВ API (Pydantic схемы)

### 9.1 Схема заказа для продавца (БЕЗ данных покупателя)

```python
class SellerOrderView(BaseModel):
    id: int
    category: str
    service: Optional[str]
    state: Optional[str]
    status: str
    price: float
    created_at: datetime
    completed_at: Optional[datetime]
    # НЕТ: user_id, buyer_username, buyer_telegram_id
    
    class Config:
        from_attributes = True
```

### 9.2 Схема заказа для воркера (БЕЗ данных покупателя)

```python
class WorkerOrderView(BaseModel):
    id: int
    category: str
    service: Optional[str]
    state: Optional[str]
    worker_price: float
    created_at: datetime
    is_bulk: bool
    # НЕТ: user_id, buyer_username, price (полная цена)
    
    class Config:
        from_attributes = True
```

### 9.3 Схема заказа для владельца (ПОЛНАЯ)

```python
class AdminOrderView(BaseModel):
    id: int
    user_id: int                    # Только владелец видит
    worker_id: Optional[int]
    category: str
    service: Optional[str]
    state: Optional[str]
    status: str
    price: float
    worker_price: float
    created_at: datetime
    escrow_released: bool
    
    class Config:
        from_attributes = True
```

---

## ЧАСТЬ 10 — ФИНАЛЬНЫЙ ЧЕКЛИСТ CURSOR

После каждого этапа проверяй:

**После Этапа 2 (модели):**
```bash
python3 -c "from shared.database.models import Order, Product, WorkerViolation, SystemSetting; print('OK')"
```

**После Этапа 3 (миграция):**
```bash
alembic upgrade head
alembic current  # Должно показать v24_001
```

**После Этапа 4 (product_service):**
```bash
grep -n "with_for_update" mirror_bot/services/product_service.py
grep -n "is_active" mirror_bot/services/product_service.py
grep -n "moderation_status" mirror_bot/services/product_service.py
```

**После Этапа 5 (seller orders):**
```bash
grep -n "buyer_user_id\|buyer.*id\|user_id" seller_bot/handlers/orders.py
# Должно вернуть 0 результатов
```

**После Этапа 6 (chat_filter):**
```bash
python3 -c "
from shared.utils.chat_filter import filter_message
tests = ['test@email.com', 'discord#1234', '@username', 'https://t.me/test', '+79991234567']
for t in tests:
    r = filter_message(t)
    assert 'СКРЫТ' in r, f'FAIL: {t} → {r}'
    print(f'OK: {t} → {r}')
"
```

**После Этапа 7 (Celery):**
```bash
celery -A shared.tasks.auto_complete worker --loglevel=info &
celery -A shared.tasks.auto_complete beat --loglevel=info &
```

**Финальная проверка:**
```bash
docker-compose up -d
docker-compose ps  # Все 8 сервисов должны быть healthy
curl http://localhost:8000/api/dashboard/stats  # Web panel отвечает
```

---

## ЧАСТЬ 11 — ТИПИЧНЫЕ ОШИБКИ И КАК ИХ ИЗБЕЖАТЬ

| Ошибка | Причина | Решение |
|---|---|---|
| `DetachedInstanceError` | Обращение к lazy-loaded полю вне сессии | Использовать `selectinload()` или `joinedload()` |
| `MissingGreenlet` | Синхронный код в async контексте | Все DB операции через `await` |
| `UniqueViolation` при покупке | Нет `SELECT FOR UPDATE` | Добавить `.with_for_update()` |
| Двойная выплата | Нет проверки `escrow_released` | Проверять флаг перед выплатой |
| Покупатель видит данные | Нет фильтрации в схеме | Использовать `SellerOrderView` без `user_id` |
| Товар виден без модерации | Нет проверки `moderation_status` | Фильтровать в каталоге |
| FSM зависает | Не вызван `state.clear()` | Вызывать `await state.clear()` после завершения |
| Бот не отвечает | Middleware не пропускает | Проверить порядок middlewares в `bot.py` |

---

## ЧАСТЬ 12 — КОНТЕКСТНЫЕ ФАЙЛЫ ДЛЯ CURSOR

Держи всегда открытыми в Cursor:

| Файл | Когда использовать |
|---|---|
| `shared/database/models.py` | При любой работе с БД |
| `newlookup_srs_v24_FINAL.md` | При вопросах о бизнес-логике |
| `privacy_and_moderation.md` | При работе с безопасностью |
| `consistency_report_v3.md` | При проверке логики |
| `cursor_master_guide.md` | Как навигатор |

**Порядок добавления контекста в Cursor Chat:**
1. Нажми `@` → выбери файл который редактируешь
2. Нажми `@` → добавь `models.py`
3. Нажми `@` → добавь `newlookup_srs_v24_FINAL.md` (только для сложных вопросов)
4. Напиши промт

---

*Инструкция написана на основе полного прочтения всех 140+ файлов проекта newlookup-v2.*
*Версия 4.0 | Март 2026*
