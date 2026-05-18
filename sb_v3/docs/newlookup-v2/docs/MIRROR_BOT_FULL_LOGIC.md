# Mirror Bot — Полная структура, логика и распределение задач

> Полная документация по архитектуре, модулям, обработчикам, сервисам и потокам данных mirror_bot.

---

## Оглавление

1. [Общая архитектура](#1-общая-архитектура)
2. [Дерево файлов](#2-дерево-файлов)
3. [Точка входа — bot.py](#3-точка-входа--botpy)
4. [Конфигурация — config.py](#4-конфигурация--configpy)
5. [Middleware (цепочка обработки)](#5-middleware-цепочка-обработки)
6. [FSM States (состояния)](#6-fsm-states-состояния)
7. [Handlers (обработчики)](#7-handlers-обработчики)
   - 7.1 [start.py — Регистрация и главное меню](#71-startpy)
   - 7.2 [dynamic_menu.py — Динамическое меню из БД](#72-dynamic_menupy)
   - 7.3 [profile.py — Профиль пользователя](#73-profilepy)
   - 7.4 [payment.py — Пополнение баланса](#74-paymentpy)
   - 7.5 [Lookup (поиск данных)](#75-lookup-поиск-данных)
   - 7.6 [credit_reports.py — Кредитные отчёты](#76-credit_reportspy)
   - 7.7 [banks.py — Банки](#77-bankspy)
   - 7.8 [cc.py — Кредитные карты](#78-ccpy)
   - 7.9 [fullz.py — FULLZ](#79-fullzpy)
   - 7.10 [documents.py — Документы](#710-documentspy)
   - 7.11 [esim.py — eSIM](#711-esimpy)
   - 7.12 [accounts.py — Аккаунты](#712-accountspy)
   - 7.13 [addinfo.py — Добавление информации в CR](#713-addinfopy)
   - 7.14 [education.py — Обучение](#714-educationpy)
   - 7.15 [seller_specials.py — Товары продавцов](#715-seller_specialspy)
   - 7.16 [brute_bank.py — Brute Bank](#716-brute_bankpy)
   - 7.17 [buyer_chat.py — Чат покупатель-продавец](#717-buyer_chatpy)
   - 7.18 [buyer_orders.py — Заказы покупателя](#718-buyer_orderspy)
   - 7.19 [support.py — Поддержка](#719-supportpy)
   - 7.20 [cart.py — Корзина](#720-cartpy)
   - 7.21 [wishlist.py — Список желаний](#721-wishlistpy)
   - 7.22 [checkout_coupons.py — Купоны при оплате](#722-checkout_couponspy)
   - 7.23 [onboarding.py — Онбординг](#723-onboardingpy)
   - 7.24 [catalog_search.py — Поиск по каталогу](#724-catalog_searchpy)
   - 7.25 [another_services.py — Другие сервисы](#725-another_servicespy)
   - 7.26 [vip_watchlist.py — VIP Watchlist](#726-vip_watchlistpy)
   - 7.27 [notification_settings.py — Настройки уведомлений](#727-notification_settingspy)
   - 7.28 [rules.py — Правила сервиса](#728-rulespy)
   - 7.29 [fallback.py — Обработка неизвестных сообщений](#729-fallbackpy)
8. [Services (бизнес-логика)](#8-services-бизнес-логика)
   - 8.1 [user_service.py](#81-user_servicepy)
   - 8.2 [order_service.py](#82-order_servicepy)
   - 8.3 [payment_service.py](#83-payment_servicepy)
   - 8.4 [payment_monitor.py](#84-payment_monitorpy)
   - 8.5 [crypto_pay.py / cryptomus.py](#85-crypto_paypy--cryptomuspy)
   - 8.6 [product_service.py](#86-product_servicepy)
   - 8.7 [product_delivery_service.py](#87-product_delivery_servicepy)
   - 8.8 [file_service.py](#88-file_servicepy)
   - 8.9 [parser.py / validator.py](#89-parserpy--validatorpy)
   - 8.10 [support_service.py / support_notification_service.py](#810-support_servicepy)
   - 8.11 [checkout_coupon_service.py](#811-checkout_coupon_servicepy)
   - 8.12 [menu_counts_service.py](#812-menu_counts_servicepy)
   - 8.13 [Automation (cs, cr, ssn_dl)](#813-automation)
   - 8.14 [Фоновые сервисы](#814-фоновые-сервисы)
9. [Keyboards (клавиатуры)](#9-keyboards-клавиатуры)
10. [Constants (константы и данные)](#10-constants-константы-и-данные)
11. [Utils (утилиты)](#11-utils-утилиты)
12. [Filters (фильтры)](#12-filters-фильтры)
13. [Взаимодействие с shared модулем](#13-взаимодействие-с-shared-модулем)
14. [Потоки данных (Data Flows)](#14-потоки-данных)
15. [Таблицы БД, используемые mirror_bot](#15-таблицы-бд)
16. [Схема обработки запроса](#16-схема-обработки-запроса)

---

## 1. Общая архитектура

Mirror Bot — клиентский Telegram-бот для покупателей (Buyers). Это **aiogram 3** бот, который:

- Запускается **динамически** из `main_bot` — для каждого `MirrorBot` в БД создаётся отдельный экземпляр `Bot + Dispatcher`
- Использует **единую PostgreSQL БД** (через `shared/database`)
- Поддерживает **4 языка**: en, ru, zh, es
- Работает с **MemoryStorage** для FSM
- Запускает **фоновые задачи**: CS/CR/SSN automation, abandoned cart watcher, review request service

**Роль mirror_bot в системе:**
```
Покупатель ←→ mirror_bot ←→ PostgreSQL ←→ support_bot / worker_bot / seller_bot
                  ↕
           Crypto Pay / Cryptomus (платежи)
           Lookup API (автоматизация)
```

---

## 2. Дерево файлов

```
mirror_bot/
├── __init__.py
├── bot.py                          # Фабрика бота и диспетчера
├── config.py                       # Конфигурация (цены, лимиты, платежи)
├── requirements.txt
│
├── constants/                      # Статические данные и тексты
│   ├── accounts_data.py            # Каталог аккаунтов (BG, Lookup)
│   ├── addinfo_data.py             # Каталог Add Info (CR, BG, Employer, Unfreeze)
│   ├── bank_data.py                # Каталог банков (VCC, Personal, Business, Crypto, Merchant, Logs)
│   ├── buttons_en.py               # Тексты кнопок EN
│   ├── buttons_es.py               # Тексты кнопок ES
│   ├── buttons_ru.py               # Тексты кнопок RU
│   ├── buttons_zh.py               # Тексты кнопок ZH
│   ├── language_loader.py          # Загрузчик языков (кэширование)
│   ├── prices.py                   # Все цены (ServicePrices, BulkDiscounts, SystemFees)
│   ├── product_descriptions.py     # Описания товаров + ссылки на туториалы
│   ├── service_descriptions.py     # Описания сервисов (мультиязычные)
│   ├── service_eta.py              # ETA для каждого сервиса
│   ├── states_data.py              # Список штатов США
│   ├── texts.py                    # Базовые тексты (EN)
│   ├── texts_en.py                 # Полные тексты EN (~950 строк)
│   ├── texts_es.py                 # Полные тексты ES
│   ├── texts_ru.py                 # Полные тексты RU (~1342 строки)
│   ├── texts_zh.py                 # Полные тексты ZH (~1339 строк)
│   ├── texts_zh_notifications.py   # Уведомления ZH
│   ├── texts_zh_temp.py            # Временные тексты ZH
│   └── tutorial_links.py           # Ссылки на все туториалы
│
├── filters/
│   └── service_filter.py           # FSM-фильтр по текущему сервису
│
├── handlers/                       # Все обработчики Telegram-событий
│   ├── start.py                    # /start, выбор языка, правила, главное меню
│   ├── dynamic_menu.py             # Динамическое меню из БД (MirrorMenuCategory)
│   ├── profile.py                  # Профиль, баланс, реферальная система, send money
│   ├── payment.py                  # Пополнение баланса (CryptoPay, Cryptomus)
│   ├── rules.py                    # Правила сервиса
│   ├── products.py                 # Товары (документы, fullz) — покупка из каталога
│   ├── banks.py                    # Банки (VCC, Personal, Business, Crypto, Merchant, Logs)
│   ├── cc.py                       # Кредитные карты (CC) — категории, покупка, feedback
│   ├── fullz.py                    # FULLZ (Personal, Business, Military, Young, Work&Travel)
│   ├── documents.py                # Документы (DL, Passport, SSN Card, Business Docs)
│   ├── credit_reports.py           # Кредитные отчёты (TU, EX, EQ, LN, WalletHub)
│   ├── esim.py                     # eSIM (SMS, Data, Configurator, Google Voice)
│   ├── accounts.py                 # Аккаунты (Background, Lookup)
│   ├── addinfo.py                  # Добавление информации в CR/BG
│   ├── education.py                # Обучение (подписки, мануалы)
│   ├── education_admin.py          # Админ-функции обучения
│   ├── seller_specials.py          # Товары продавцов (NFC, OTP, Enroll, Selfreg, Checks, Logs, Docs, Fullz)
│   ├── brute_bank.py               # Brute Bank (покупка brute-аккаунтов)
│   ├── buyer_chat.py               # Чат покупатель ↔ продавец
│   ├── buyer_orders.py             # Мои заказы (банки, CC)
│   ├── support.py                  # Поддержка (создание тикетов, просмотр)
│   ├── cart.py                     # Корзина (добавление, просмотр, checkout)
│   ├── wishlist.py                 # Список желаний
│   ├── checkout_coupons.py         # Применение купонов при оплате
│   ├── onboarding.py               # Онбординг нового пользователя
│   ├── catalog_search.py           # Поиск по каталогу
│   ├── another_services.py         # Раздел "Another Services" (динамические кнопки)
│   ├── vip_watchlist.py            # VIP Watchlist
│   ├── notification_settings.py    # Настройки уведомлений
│   ├── messages.py                 # Обработка текстовых сообщений (пустой роутер)
│   ├── fallback.py                 # Catch-all для неизвестных сообщений
│   └── lookup/                     # Подмодуль Lookup
│       ├── main.py                 # Главное меню Lookup
│       ├── ssn.py                  # SSN & DOB Lookup (single + bulk)
│       ├── phone.py                # Phone Lookup (Name, SSN, Full)
│       ├── bank_lookup.py          # Bank Account Lookup (AN+RN, Transactions, Balance, Name)
│       └── others.py               # DL, MVR, Full MVR, Credit Score, BG, MMN, EIN
│
├── keyboards/
│   ├── reply.py                    # Reply-клавиатура главного меню (из БД)
│   ├── inline.py                   # Все inline-клавиатуры (lookup, payment, esim, support...)
│   └── cc.py                       # Inline-клавиатуры раздела CC
│
├── middlewares/
│   ├── session.py                  # Инъекция AsyncSession из shared.database
│   ├── mirror_bot.py               # Инъекция mirror_bot_id
│   ├── user_update.py              # Обновление username при каждом запросе
│   ├── language.py                 # Определение языка → texts, buttons, ui_texts
│   ├── bot_status_check.py         # Проверка is_active бота
│   ├── ban_check.py                # Проверка бана пользователя
│   ├── reply_keyboard_cancel.py    # Сброс FSM при нажатии кнопки меню
│   └── debug_logger.py             # Логирование всех входящих событий
│
├── services/
│   ├── user_service.py             # CRUD пользователей, баланс, промо, рефералы
│   ├── order_service.py            # Создание заказов, списание баланса, уведомления
│   ├── payment_service.py          # Создание платёжных инвойсов
│   ├── payment_monitor.py          # Фоновый мониторинг статуса платежей
│   ├── crypto_pay.py               # Интеграция с CryptoBot API
│   ├── crypto_pay_models.py        # Pydantic-модели CryptoBot
│   ├── cryptomus.py                # Интеграция с Cryptomus API
│   ├── cryptomus_models.py         # Pydantic-модели Cryptomus
│   ├── product_service.py          # Работа с товарами (documents, fullz, accounts)
│   ├── product_delivery_service.py # Доставка товаров покупателю
│   ├── file_service.py             # Работа с файлами (PDF, фото)
│   ├── parser.py                   # Парсинг адресов и данных (smart_parse_address_data)
│   ├── validator.py                # Pydantic-модели валидации (SSN, DL, BG, Phone, Fullz...)
│   ├── support_service.py          # Создание/управление тикетами поддержки
│   ├── support_notification_service.py # Уведомления о тикетах
│   ├── checkout_coupon_service.py  # Применение купонов при checkout
│   ├── menu_counts_service.py      # Подсчёт товаров для меню (с Redis-кэшем)
│   ├── cs_automation.py            # Автоматизация Credit Score (API-based)
│   ├── cr_automation.py            # Автоматизация Credit Report (API-based)
│   ├── ssn_dl_automation.py        # Автоматизация SSN/DL (usfull.info API)
│   ├── usfull_service.py           # Клиент usfull.info API
│   ├── abandoned_cart_service.py   # Фоновый watcher брошенных корзин
│   ├── review_request_service.py   # Запрос отзыва через 24ч после покупки
│   └── wishlist_notifier.py        # Уведомления о снижении цен в вишлисте
│
├── states/
│   ├── order.py                    # OrderStates, TopupStates, SendMoneyStates, CouponStates,
│   │                               # ESIMStates, ESIMConfigStates, DocumentStates,
│   │                               # RandomFullzStates
│   ├── profile.py                  # ProfileStates (archive channel)
│   ├── accounts.py                 # AccountStates (quantity, bulk)
│   ├── banks.py                    # BankStates (quantity, custom qty, name input, brute search)
│   └── fullz.py                    # FullzStates (type, state, CS, age, gender, quantity...)
│
└── utils/
    ├── media_library.py            # Поиск фото в photo/ и media/ директориях
    ├── message_utils.py            # safe_edit_message, safe_answer_callback
    ├── multilang_helper.py         # Хелперы для мультиязычности
    └── product_translations.py     # Переводы названий продуктов (en/ru/zh)
```

---

## 3. Точка входа — bot.py

`create_mirror_bot(token, mirror_bot_id)` — фабричная функция, создающая экземпляр бота.

### Порядок инициализации:

```
1. Создание Bot(token) + Dispatcher(MemoryStorage)
2. Регистрация глобального error handler
3. Подключение middleware (в порядке выполнения):
   DebugLoggerMiddleware → DatabaseSessionMiddleware → GlobalErrorLoggingMiddleware
   → MirrorBotMiddleware → UserUpdateMiddleware → LanguageMiddleware
   → BotStatusCheckMiddleware → BanCheckMiddleware → ReplyKeyboardCancelMiddleware
4. Запуск automation runners (если не отключены через env):
   - CsAutomationRunner (Credit Score)
   - CrAutomationRunner (Credit Report)
   - SsnDlAutomationRunner (SSN / DL)
5. Запуск фоновых задач (только для mirror_bot_id == 1):
   - Abandoned Cart Watcher
   - Review Request Service
6. Подключение роутеров (handlers) в определённом порядке
   (fallback — ПОСЛЕДНИЙ)
```

### Порядок роутеров:

```
start → dynamic_menu → profile → rules → checkout_coupons → support → payment
→ lookup_main → ssn → phone → others → bank_lookup → credit_reports
→ banks → esim → accounts → addinfo → documents → fullz → products
→ cc → education → education_admin → another_services → seller_specials
→ brute_bank → buyer_chat → buyer_orders → wishlist → cart
→ catalog_search → onboarding → vip_watchlist → fallback
```

---

## 4. Конфигурация — config.py

| Параметр | Значение | Описание |
|----------|----------|----------|
| `referral_percent` | 4.0% | Процент реферальных начислений |
| `min_topup` | $10 | Минимальное пополнение |
| `max_topup` | $5000 | Максимальное пополнение |
| `max_bulk_items` | 20 | Макс. элементов в bulk-заказе |
| `min_bulk_items` | 2 | Мин. элементов в bulk-заказе |
| `crypto_pay_token` | env | Токен CryptoBot API |
| `crypto_pay_testnet` | env | Тестовая сеть CryptoBot |
| `cryptomus_merchant_id` | env | Merchant ID Cryptomus |
| `cryptomus_payment_key` | env | Payment Key Cryptomus |
| `payment_fee_percent` | 3.0% | Комиссия CryptoPay |
| `cryptomus_fee_percent` | 2.0% | Комиссия Cryptomus |
| `default_payment_method` | "cryptopay" | Метод оплаты по умолчанию |

---

## 5. Middleware (цепочка обработки)

Каждый входящий Update проходит через цепочку middleware в порядке регистрации:

### 5.1 DebugLoggerMiddleware
Логирует все входящие Message, CallbackQuery и Update для отладки.

### 5.2 DatabaseSessionMiddleware
Создаёт `AsyncSession` из `shared.database.session.async_session_maker` и помещает в `data["session"]`. Сессия автоматически закрывается после обработки.

### 5.3 GlobalErrorLoggingMiddleware (shared)
Перехватывает исключения, логирует в NocoDB (если включён).

### 5.4 MirrorBotMiddleware
Добавляет `data["mirror_bot_id"]` — ID текущего mirror-бота.

### 5.5 UserUpdateMiddleware
При каждом запросе проверяет, изменился ли `username` пользователя в Telegram, и обновляет его в БД.

### 5.6 LanguageMiddleware
Определяет язык пользователя из БД (`User.language`) и добавляет:
- `data["user_language"]` — код языка (en/ru/zh/es)
- `data["texts"]` — объект `BotTexts` для текущего языка
- `data["buttons"]` — объект `ButtonTexts` для текущего языка
- `data["ui_texts"]` — `UiTranslator` для динамических переводов из БД

### 5.7 BotStatusCheckMiddleware
Проверяет `MirrorBot.is_active` в БД. Если бот деактивирован — отправляет сообщение и блокирует обработку.

### 5.8 BanCheckMiddleware
Проверяет `User.is_banned` в БД. Если забанен — отправляет причину бана и блокирует.

### 5.9 ReplyKeyboardCancelMiddleware (только Message)
Если пользователь находится в FSM-состоянии и нажимает кнопку из Reply-клавиатуры главного меню — FSM state очищается, позволяя перейти в другой раздел.

---

## 6. FSM States (состояния)

### OrderStates
| State | Описание |
|-------|----------|
| `waiting_data` | Ожидание ввода данных для single-заказа |
| `waiting_bulk_data` | Ожидание ввода данных для bulk-заказа |
| `confirmation` | Подтверждение заказа |

### TopupStates
| State | Описание |
|-------|----------|
| `waiting_promo` | Ожидание промокода |
| `waiting_amount` | Ожидание суммы пополнения |
| `waiting_payment` | Ожидание оплаты |

### SendMoneyStates
| State | Описание |
|-------|----------|
| `waiting_user_id` | Ожидание ID получателя |
| `waiting_amount` | Ожидание суммы |
| `confirmation` | Подтверждение перевода |

### CouponStates
| State | Описание |
|-------|----------|
| `waiting_code` | Ожидание кода купона |

### ESIMStates
| State | Описание |
|-------|----------|
| `confirm_bulk_purchase` | **Используется** в `esim.py`: подтверждение опта (SMS/Data/Google Voice из `AccountItem`) |
| `selecting_type`, `selecting_operator`, `selecting_period_or_data`, `confirmation` | Объявлены в `order.py`; в текущем `esim.py` не выставляются |

### ESIMConfigStates
| State | Описание |
|-------|----------|
| `selecting_operator` | Выбор оператора |
| `selecting_state` | Выбор штата |
| `selecting_cs` | Выбор Credit Score |
| `selecting_report` | Выбор типа отчёта |
| `selecting_qty` | Выбор количества |
| `confirmation` | Подтверждение |

### DocumentStates
| State | Описание |
|-------|----------|
| `waiting_data` | Ожидание данных для документа |
| `confirmation` | Подтверждение |

### RandomFullzStates
| State | Описание |
|-------|----------|
| `confirmation` | Подтверждение покупки random fullz |

### ProfileStates
| State | Описание |
|-------|----------|
| `entering_archive_channel_id` | Ввод ID канала для архива |

### AccountStates
| State | Описание |
|-------|----------|
| `waiting_for_quantity` | Ожидание количества |
| `confirm_bulk_purchase` | Подтверждение bulk-покупки |

### BankStates
| State | Описание |
|-------|----------|
| `waiting_for_quantity` | Ожидание количества |
| `waiting_custom_qty` | Ввод произвольного количества |
| `confirm_bulk_purchase` | Подтверждение bulk-покупки |
| `waiting_name_input` | Ввод имени для банка (on-name order) |
| `confirm_on_name` | Подтверждение on-name заказа |
| `waiting_brute_search_query` | Поиск в Brute Bank |

### FullzStates
| State | Описание |
|-------|----------|
| `select_type` | Выбор типа FULLZ |
| `select_state` | Выбор штата |
| `select_credit_score` | Выбор диапазона CS |
| `select_age` | Выбор возраста |
| `select_gender` | Выбор пола |
| `select_report_group` | Выбор группы отчёта |
| `select_quantity` | Выбор количества |
| `waiting_custom_qty` | Произвольное количество |
| `select_company_type` | Тип компании (Business Fullz) |
| `select_loan_size` | Размер кредита |
| `confirmation` | Подтверждение |

---

## 7. Handlers (обработчики)

### 7.1 start.py

**Триггеры:** `/start`, `/menu`, callback `back_main`, `reorder:*`

**Логика:**
1. `/start` → проверка существования пользователя в БД
2. Если новый → создание User через `UserService.get_or_create_user()`
3. Обработка deep link (`/start ref_123`) → привязка реферала
4. Обработка промокода маркетолога (`/start promo_CODE`)
5. Показ выбора языка → `language_keyboard()`
6. После выбора языка → показ правил → `rules_accept_keyboard()`
7. При принятии правил → показ главного меню с Reply-клавиатурой
8. `back_main` → возврат в главное меню (загрузка категорий из БД через `MenuCategoryService`)
9. `reorder:*` → переход в соответствующий раздел для повторного заказа

**Таблицы:** `users`, `referrals`, `mirror_menu_categories`

### 7.2 dynamic_menu.py

**Триггеры:** Текстовые сообщения, совпадающие с кнопками меню из БД

**Логика:**
1. Загрузка `MirrorMenuCategory` из БД
2. Сопоставление текста сообщения с `route_key` категории
3. Маршрутизация на соответствующий handler (lookup, banks, credit_reports, etc.)
4. Подсчёт товаров через `MenuCountService` (с Redis-кэшем)

**Таблицы:** `mirror_menu_categories`, `bank_items`, `seller_banks`, `products`

### 7.3 profile.py

**Триггеры:** Кнопка "My Profile", callbacks `profile`, `send_money`, `ref_system`, `apply_coupon`, `choose_lang`, `setup_archive`

**Логика:**
- **Профиль:** Показ ID, баланса, даты регистрации, реферальной ссылки
- **Send Money:** FSM (ввод ID → сумма → подтверждение) → перевод между пользователями
- **Referral System:** Показ статистики рефералов и заработка
- **Apply Coupon:** FSM для ввода кода купона → активация через `CouponService`
- **Choose Language:** Смена языка → обновление в БД
- **Setup Archive:** Настройка канала для архивации заказов

**Таблицы:** `users`, `referrals`, `transactions`, `coupons`, `user_coupons`

### 7.4 payment.py

**Триггеры:** Кнопка "Top-up balance", callbacks `pay_cryptopay`, `pay_cryptomus`, `check_payment:*`, `cancel_payment:*`

**Логика:**
1. Показ выбора платёжной системы (CryptoPay / Cryptomus)
2. Ввод суммы ($10–$5000)
3. Создание инвойса через `CryptoPayService` или `CryptomusService`
4. Показ ссылки на оплату + кнопки "Check Status" / "Cancel"
5. Проверка статуса: `paid` → зачисление на баланс + реферальные + bot owner income
6. Запись транзакции в леджер

**Таблицы:** `users`, `transactions`, `referrals`, `bot_owners`, `bot_owner_stats`

### 7.5 Lookup (поиск данных)

#### 7.5.1 lookup/main.py
**Триггеры:** Кнопка "Search" (все языковые варианты), callback `back_lookup`, `lookup_phone`, `lookup_support`

**Логика:**
- Показ главного меню Lookup с фото
- Маршрутизация на подразделы: SSN, DL, MVR, CS, BG, MMN, EIN, Phone, Bank Account

#### 7.5.2 lookup/ssn.py — SSN & DOB Lookup
**Триггеры:** callback `lookup_ssn`, `bulk_order`, `confirm_yes_ssn`, `bulk_confirm_ssn`

**Flow:**
```
lookup_ssn → OrderStates.waiting_data
  → Ввод данных (имя, адрес, город, штат, ZIP, DOB)
  → Автоопределение: single (1 запись) или bulk (2-20 записей)
  → Парсинг через DataParser.smart_parse_address_data()
  → Валидация через SSNLookupData (Pydantic)
  → OrderStates.confirmation
  → Подтверждение → проверка баланса → списание
  → OrderService.create_order() → уведомление в support_bot
  → SsnDlAutomationRunner.enqueue_order() → автоматизация через usfull API
```

**Цены:** Single $2.80, Bulk $3.00/шт

#### 7.5.3 lookup/phone.py — Phone Lookup
**Триггеры:** callbacks `phone_name`, `phone_ssn`, `phone_full`

**3 типа:**
| Тип | Цена | Что возвращает |
|-----|------|----------------|
| NAME LOOKUP | $1.50 | Имя по номеру телефона |
| NAME DOB SSN | $4.00 | Имя + DOB + SSN |
| FULL LOOKUP | $5.00 | Имя + DOB + SSN + Credit Score |

**Flow:** Ввод номера → валидация PhoneSearchData → подтверждение → заказ

#### 7.5.4 lookup/bank_lookup.py — Bank Account Lookup
**Триггеры:** callback `lookup_ba`, `lookup_ba_item:*`

**5 типов проверок:**
| Тип | Цена | Описание |
|-----|------|----------|
| Check AN+RN | $5 | Проверка Account Number + Routing Number |
| Check Transactions | $5 | Транзакции за 15 дней |
| Check Balance | $5 | Текущий баланс |
| Check NAME | $3 | Имя владельца по AN+RN |
| Check AN+RN+NAME | $7 | Полная проверка |

**Flow:** Выбор типа → ввод AN/RN → подтверждение → заказ

#### 7.5.5 lookup/others.py — DL, MVR, CS, BG, MMN, EIN
**Триггеры:** callbacks `lookup_dl`, `lookup_mvr`, `lookup_fullmvr`, `lookup_credit`, `lookup_bg`, `lookup_mmn`, `lookup_ein`

**Универсальный обработчик** для всех остальных lookup-сервисов:

| Сервис | Single | Bulk | Валидация |
|--------|--------|------|-----------|
| DL Lookup | $7.00 | $6.50 | DLLookupData (имя, адрес, DOB) |
| MVR Lookup | $11.00 | $10.00 | Raw text (без валидации) |
| Full MVR | $22.00 | $20.00 | Raw text (без валидации) |
| Credit Score | $2.00 | $1.60 | CreditScoreLookupData (имя, адрес, DOB, SSN) |
| Background | $2.00 | $1.60 | BGLookupData (имя, адрес) |
| MMN | $9.00 | — | MMNLookupData (имя, адрес) |
| EIN | $11.00 | — | Raw text (без валидации) |

**Автоматизация:**
- `lookup_credit` → `CsAutomationRunner` (CS automation через API)
- `lookup_dl` → `SsnDlAutomationRunner` (через usfull API)
- Остальные → уведомление воркеров через support_bot

**CS Retry:** Кнопка повторного запуска CS automation для неудачных заказов

### 7.6 credit_reports.py

**Триггеры:** Кнопка "CREDIT REPORTS", callbacks `cr_transunion`, `cr_experian`, `cr_equifax`, `cr_lexisnexis`, `cr_wallet`

**5 типов отчётов:**
| Отчёт | Single | Bulk |
|-------|--------|------|
| TransUnion | $18 | $16 |
| Experian | $18 | $16 |
| Equifax | $18 | $16 |
| LexisNexis | $25 | $22 |
| WalletHub | $5 | $4 |

**Flow:**
```
Выбор типа → OrderStates.waiting_data
  → Ввод данных (имя, адрес, DOB, SSN)
  → Парсинг + валидация
  → OrderStates.confirmation
  → Подтверждение → списание → создание заказа
  → CrAutomationRunner.enqueue_order() (автоматизация)
```

**Автоматизация:** Все CR заказы автоматически обрабатываются через `CrAutomationRunner` (API-based).

### 7.7 banks.py

**Триггеры:** Кнопка "BANKS", callbacks `banks_main`, `bank_cat:*`, `bank_item:*`, `bank_buy:*`, `bank_qty:*`, `bank_on_name:*`

**6 категорий:**
| Категория | Описание |
|-----------|----------|
| VCC (💳) | Виртуальные карты (Chime, PayPal, Current, Wise...) |
| Personal (🏦) | Личные банки (Citi, Chase, Wells Fargo, TD...) |
| Business (🏢) | Бизнес банки (QuickBooks, BMO, BoA...) |
| Crypto (🪙) | Крипто (CashApp, Blockchain, Kraken...) |
| Merchant (🏪) | Мерчант аккаунты (Mercury, Stripe, Square...) |
| Logs (📋) | Банковские логи |

**Flow покупки банка:**
```
banks_main → bank_cat:{category}
  → Список банков (из БД BankItem, fallback на BankData)
  → bank_item:{category}:{bank_id}
  → Описание + цена + кнопки (Buy, Bulk, On-Name, Tutorial)
  → bank_buy:{bank_id} → подтверждение → создание SellerOrder
  → bank_qty:{bank_id}:{qty} → bulk-покупка (2-10 шт, скидки)
  → bank_on_name:{bank_id} → ввод имени → заказ на конкретное имя
```

**Источники товаров:**
1. **Seller Banks** (из `seller_banks` таблицы) — товары от продавцов
2. **Per-Order** (из `BankData` констант) — заказы, выполняемые воркерами

**Bulk скидки:** 3+ шт: -2%, 5+ шт: -3%, 10+ шт: -5%

**Таблицы:** `bank_items`, `seller_banks`, `seller_orders`, `orders`, `users`, `transactions`

### 7.8 cc.py

**Триггеры:** Кнопка "CC", callbacks `cc_main`, `cc_cat:*`, `cc_item:*`, `cc_buy:*`, `cc_enroll`, `cc_otp`, `cc_nfc`, `cc_selfreg_cc`

**Категории:**
- 🇺🇸 USA CC
- 🌍 ALL WORLD CC
- 🏦 Enroll
- 🔑 OTP
- 📱 NFC
- 🏧 Selfreg CC

**Flow:**
```
cc_main → cc_cat:{code} → список товаров из SellerCCItem
  → cc_item:{cat}:{id} → детали товара
  → cc_buy:{item_id}:{cat} → подтверждение → покупка
  → Мгновенная выдача данных CC + feedback keyboard
```

**Feedback:** После покупки — кнопки Like/Dislike + Report Issue (со скриншотом)

**Таблицы:** `cc_categories`, `cc_items`, `seller_cc_items`, `seller_cc_orders`

### 7.9 fullz.py

**Триггеры:** Кнопка "PROS & FULLZ", callbacks `fullz_main`, `fullz_type:*`, `fullz_state:*`, `fullz_cs:*`, `fullz_age:*`, `fullz_gender:*`, `fullz_qty:*`

**Типы FULLZ:**
| Тип | Цена | Описание |
|-----|------|----------|
| Personal Fullz | $10 | SSN + DOB + адрес + телефон + email |
| Personal + CS | $15 | + Credit Score |
| Business Fullz | $30 | EIN + Company + Owner info |
| Military Fullz | $20 | Военные данные |
| Young (18-25) | $15 | Молодые профили |
| Work & Travel | $25 | Рабочие визы |

**Flow (Personal Fullz):**
```
fullz_main → fullz_type:personal
  → Выбор штата (4 страницы, 50 штатов + Random)
  → Выбор Credit Score (Any, 300-500, 500-650, 650-750, 750+)
  → Выбор возраста (Any, 18-25, 25-35, 35-50, 50+)
  → Выбор пола (Any, Male, Female)
  → Выбор количества (1-10)
  → Подтверждение → списание → создание заказа
```

**Random Fullz:** Мгновенная выдача из `products` таблицы (если есть в наличии)

**Таблицы:** `products`, `product_purchases`, `orders`, `seller_fullz_items`

### 7.10 documents.py

**Триггеры:** Кнопка "DOCUMENTS", callbacks `docs_main`, `doc_type:*`, `doc_state:*`, `doc_confirm_*`

**Типы документов:**
| Тип | Цена | Описание |
|-----|------|----------|
| DL Front+Back | $50 | Водительское удостоверение |
| DL + Selfie | $80 | DL с селфи |
| Passport | $80 | Паспорт |
| SSN Card | $30 | Карта SSN |
| Business Docs | $100 | Бизнес документы |
| High-Quality DL | $150 | Высокое качество (рисование) |
| Robot Drawing | $200 | Роботизированное рисование |

**Flow:**
```
docs_main → doc_type:{type}
  → Ввод данных (DocumentStates.waiting_data)
  → Валидация → подтверждение → заказ
```

**Таблицы:** `orders`, `products`, `seller_document_items`

### 7.11 esim.py

**Триггеры:** кнопка «eSIM» (`F.text`), callbacks:
- `esim_back_main`, `esim_sms`, `esim_data`, `esim_configurator`, `esim_gv`
- Каталог и покупка: `esim_item:{id}`, `esim_iback:{id}`, `esim_ib:{id}:qty`, `esim_iq:{id}:qty`
- Bulk: `confirm_bulk_esim`, `cancel_bulk_esim`
- Configurator: `esim_cfg_*` (оператор, штат, CS, отчёт, qty, confirm, back, noop)
- **Удалено (не используется):** `esim_op:*`, `esim_period:*`, `esim_gb:*`, `esim_qty:*`, `esim_buy:*`, `gv_state:*`, `gv_confirm_*`

**4 раздела главного меню:**

| Раздел | Описание | Источник данных |
|--------|----------|-----------------|
| SMS eSIM | Каталог позиций (название + цена) → количество → оплата | `AccountItem` с `category_code = esim_sms` |
| Data eSIM | То же | `AccountItem` с `category_code = esim_data` |
| eSIM Configurator | Пошаговый заказ eSIM + CS/CR | Цены из `ServicePrices` / константы в коде |
| Google Voice | Каталог позиций (без выбора штата США) | `AccountItem` с `category_code = gv` |

**Засев и админка SMS/Data/GV:** `support_bot/handlers/esim.py` — категории `esim_sms`, `esim_data`, `gv` и кнопки seed.

**Защита:** в eSIM-флоу допускаются только `AccountItem` с `category_code ∈ {esim_sms, esim_data, gv}` (нельзя подставить `item_id` из другого каталога).

**Bulk скидки eSIM:** через `ServicePrices.get_bulk_discount` / `BulkDiscountTier` для категории `esim` — типично 3+ шт: -5%, 5+ шт: -10%, 10+ шт: -15%.

**Мгновенная выдача:** если у позиции есть строки в `account_inventory` (не проданы), после оплаты списываются и credentials отправляются в чат.

**eSIM Configurator Flow:**
```
Выбор оператора → Выбор штата → Выбор CS range
  → Выбор типа отчёта
  → Выбор количества → Подтверждение
  → Заказ `category=esim`, `service_name` вида `esim_cfg_{operator}_{state}`
```

**`reorder_keyboard` (eSIM):** к категории меню `esim` относятся `service_name` с префиксами  
`gv_`, `esim_cfg_`, `esim_sms_`, `esim_data_`, а также устаревшие `sms_`, `data_`.

**Таблицы:** `orders`, `account_items`, `account_inventory`, при необходимости `bulk_order_items`

### 7.12 accounts.py

**Триггеры:** Кнопка "Subscriptions / Accounts", callbacks `accounts_main`, `acc_cat:*`, `acc_item:*`, `acc_buy:*`, `acc_qty:*`

**2 категории:**
| Категория | Товары |
|-----------|--------|
| Background Accounts | BeenVerified, TruthFinder, InstantCheckmate, Intelius, WhitePages, MyLife (+ 30-day варианты) |
| Lookup Accounts | Monarch Money, Yodlee, Empower, PocketGuard, EveryDollar |

**Flow:**
```
accounts_main → acc_cat:{category}
  → Список аккаунтов с ценами
  → acc_item:{id} → описание + tutorial
  → acc_buy:{id} → подтверждение → заказ
  → acc_qty:{id}:{qty} → bulk-покупка
```

**Мгновенная выдача:** Если есть в `account_inventory` — выдаётся мгновенно. Иначе — заказ воркеру.

**Таблицы:** `account_categories`, `account_items`, `account_inventory`, `orders`

### 7.13 addinfo.py

**Триггеры:** Кнопка "Add info in CR", callbacks `addinfo_main`, `addinfo_cat:*`, `addinfo_item:*`, `addinfo_buy:*`

**4 категории:**
| Категория | Описание |
|-----------|----------|
| Add Info in CR | Добавление телефона/адреса/работодателя в кредитный отчёт |
| Add Info in BG | Добавление в Background Check |
| Add Employer | Добавление/обновление/удаление работодателя |
| Unfreeze CR | Разморозка кредитного отчёта (TU/EX) |

**Flow:**
```
addinfo_main → addinfo_cat:{category}
  → Список услуг с ценами
  → addinfo_item:{id} → описание
  → addinfo_buy:{id} → ввод данных (SSN + адрес/телефон)
  → Подтверждение → заказ
```

**Таблицы:** `orders`

### 7.14 education.py

**Триггеры:** Кнопка "Education", callbacks `edu_main`, `edu_cat:*`, `edu_item:*`, `edu_buy:*`

**2 типа:**
| Тип | Описание |
|-----|----------|
| Subscriptions | Подписки на время (7/30/90 дней) |
| Manuals | Одноразовые мануалы (PDF с watermark) |

**Flow:**
```
edu_main → edu_cat:{code}
  → Список товаров
  → edu_item:{code} → описание + цена
  → edu_buy:{code} → покупка
  → Для мануалов: выдача PDF с watermark через FileService
  → Для подписок: активация доступа на N дней
```

**Таблицы:** `education_categories`, `education_subscriptions`, `education_manuals`, `manual_deliveries`

### 7.15 seller_specials.py

**Триггеры:** callbacks `cc_enroll`, `cc_otp`, `cc_nfc`, `cc_selfreg_cc`, `seller_special_buy:*`, `seller_special_confirm:*`, `seller_dispute:*`

**Типы товаров продавцов:**
| Тип | Модель | Описание |
|-----|--------|----------|
| Enroll | SellerEnrollItem | Enroll-аккаунты с порталами |
| OTP | SellerOTPItem | OTP-карты с SMS |
| NFC | SellerNFCItem | NFC-токены (Apple/Google Pay) |
| Selfreg CC | SellerSelfregCCItem | Self-registered кредитные карты |
| Selfreg BA | SellerSelfregBAItem | Self-registered банковские аккаунты |
| Checks | SellerCheckItem | Чеки (personal/business/cashier) |
| Logs | SellerLogsItem | Банковские логи |
| Documents | SellerDocumentItem | Документы от продавцов |
| Fullz | SellerFullzItem | Fullz от продавцов |

**Flow покупки:**
```
Каталог → выбор товара → детали (цена, описание, seller score)
  → Подтверждение → проверка баланса → списание
  → Создание SellerOrder (escrow)
  → Мгновенная выдача данных (credentials)
  → Кнопки: Chat with Seller, Report Issue, Dispute
```

**Dispute Flow:**
```
seller_dispute:{order_id}
  → Ввод причины + evidence (скриншот)
  → Создание SellerOrderDispute
  → Уведомление продавца и админа
```

**Таблицы:** `seller_*_items`, `seller_*_orders`, `seller_order_disputes`, `seller_conversations`, `seller_chats`

### 7.16 brute_bank.py

**Триггеры:** callbacks `brute_main`, `brute_cat:*`, `brute_group:*`, `brute_item:*`, `brute_buy:*`, `brute_search`

**Flow:**
```
brute_main → brute_cat:{category}
  → Группы банков (BruteBankGroup)
  → brute_group:{group_id} → список товаров
  → brute_item:{item_id} → детали (банк, категория, цена)
  → brute_buy:{item_id} → подтверждение → покупка
  → Мгновенная выдача credentials
```

**Поиск:** `brute_search` → ввод запроса → поиск по bank_name/bank_code

**Таблицы:** `brute_bank_items`, `brute_bank_groups`, `brute_bank_orders`

### 7.17 buyer_chat.py

**Триггеры:** callbacks `buyer_chat:{conversation_id}`, `buyer_chat_send:*`, FSM для ввода сообщений

**Flow:**
```
Открытие чата → загрузка истории из seller_chats
  → Отображение сообщений (buyer/seller/system)
  → Ввод сообщения → сохранение в seller_chats
  → Уведомление продавца через seller_bot
```

**Фильтрация:** Текст фильтруется через `chat_filter` (удаление URL, email, телефонов)

**Таблицы:** `seller_conversations`, `seller_chats`

### 7.18 buyer_orders.py

**Триггеры:** callbacks `buyer_my_orders`, `buyer_my_cc_orders`, `buyer_order:{id}`, `buyer_cc_order:{id}`

**Flow:**
```
buyer_my_orders → список SellerOrder (банки)
  → buyer_order:{id} → детали заказа
  → Кнопки: Chat, Dispute, Reorder

buyer_my_cc_orders → список SellerCCOrder
  → buyer_cc_order:{id} → детали CC заказа
```

**Пагинация:** По 5 заказов на страницу

**Таблицы:** `seller_orders`, `seller_cc_orders`, `seller_banks`, `seller_cc_items`

### 7.19 support.py

**Триггеры:** Кнопка "Support", callbacks `support`, `support_category_*`, `my_tickets`, `ticket_*`, `reply_ticket_*`

**Категории тикетов:**
| Категория | Описание |
|-----------|----------|
| Payment | Проблемы с оплатой |
| Product | Проблемы с товаром |
| General | Общие вопросы |
| Partnership | Партнёрство |

**Flow создания тикета:**
```
support → support_category_{type}
  → Ввод темы → ввод описания
  → Создание SupportTicket через SupportService
  → Уведомление support_bot (API :8181)
```

**Flow просмотра:**
```
my_tickets → список тикетов (open + closed)
  → ticket_{id} → история сообщений
  → reply_ticket_{id} → ответ на тикет
```

**Таблицы:** `support_tickets`, `support_messages`, `support_ticket_messages`

### 7.20 cart.py

**Триггеры:** callbacks `cart_view`, `cart_add:*`, `cart_remove:*`, `cart_checkout`, `cart_clear`

**Flow:**
```
cart_add:{product_type}:{product_id}
  → Добавление в ShoppingCart (status=active)
  → CartItem с product_type, product_id, price

cart_view → отображение содержимого корзины
  → Кнопки: Remove, Checkout, Clear

cart_checkout → проверка баланса → покупка всех товаров
  → Создание заказов для каждого товара
  → ShoppingCart.status = "checked_out"
```

**Таблицы:** `shopping_carts`, `cart_items`

### 7.21 wishlist.py

**Триггеры:** callbacks `wishlist_view`, `wishlist_add:*`, `wishlist_remove:*`

**Flow:**
```
wishlist_add:{product_type}:{product_id}
  → Добавление WishlistItem с price_at_add

wishlist_view → список товаров в вишлисте
  → Если цена снизилась — показ уведомления
  → Кнопки: Buy Now, Remove
```

**Фоновое уведомление:** `WishlistNotifier` проверяет снижение цен и отправляет уведомления

**Таблицы:** `wishlist_items`

### 7.22 checkout_coupons.py

**Триггеры:** callbacks `checkout_apply_coupon`, `checkout_remove_coupon`, `checkout_select_coupon:*`

**Flow:**
```
При подтверждении заказа → кнопка "Apply Coupon"
  → checkout_apply_coupon → список доступных купонов
  → checkout_select_coupon:{coupon_id}
  → Пересчёт цены с учётом скидки
  → Обновление checkout_confirm_text
```

**Интеграция:** Работает с любым handler'ом, который сохраняет `checkout_*` данные в FSM state

**Таблицы:** `coupons`, `user_coupons`, `coupon_redemptions`

### 7.23 onboarding.py

**Триггеры:** callback `onboarding_start`, `onboarding_step:*`, `onboarding_skip`

**Flow:**
```
Первый вход → onboarding_start
  → Пошаговый тур по функциям бота
  → onboarding_step:1 → step:2 → ... → step:N
  → onboarding_skip → переход в главное меню
```

### 7.24 catalog_search.py

**Триггеры:** callback `catalog_search`, FSM для ввода поискового запроса

**Flow:**
```
catalog_search → ввод запроса
  → Поиск по bank_items, seller_banks, products, cc_items
  → Отображение результатов с кнопками перехода
```

### 7.25 another_services.py

**Триггеры:** Кнопка "Another Services", callback `another_services`

**Flow:**
```
another_services → загрузка AnotherServiceButton из БД
  → Отображение динамических кнопок (URL или callback)
  → Кнопки управляются через web_panel
```

**Таблицы:** `another_service_buttons`

### 7.26 vip_watchlist.py

**Триггеры:** callbacks `vip_watchlist`, `vip_add:*`, `vip_remove:*`

**Flow:**
```
vip_watchlist → список отслеживаемых товаров
  → Уведомление при появлении нового товара
  → vip_add:{type}:{criteria} → добавление в watchlist
```

### 7.27 notification_settings.py

**Триггеры:** callbacks `notif_settings`, `notif_toggle:*`

**Flow:**
```
notif_settings → текущие настройки уведомлений
  → notif_toggle:{type} → вкл/выкл уведомления
  → Типы: order_updates, price_drops, new_products, promotions
```

**Таблицы:** `users` (поля `notif_*`)

### 7.28 rules.py

**Триггеры:** callback `view_rules`

Показ правил сервиса на текущем языке пользователя.

### 7.29 fallback.py

**Триггеры:** Любое необработанное сообщение или callback

**Логика:**
- Для Message: отправка текста "I don't understand. Use the menu buttons."
- Для CallbackQuery: `callback.answer()`

---

## 8. Services (бизнес-логика)

### 8.1 user_service.py

| Метод | Описание |
|-------|----------|
| `get_or_create_user(session, user_id, mirror_bot_id)` | Создание/получение пользователя |
| `get_user(session, user_id, mirror_bot_id)` | Получение пользователя |
| `update_language(session, user_id, mirror_bot_id, lang)` | Смена языка |
| `apply_promo_code(session, user_id, mirror_bot_id, code)` | Применение промокода маркетолога |
| `get_referral_stats(session, user_id, mirror_bot_id)` | Статистика рефералов |
| `create_referral_link(session, user_id, mirror_bot_id)` | Генерация реферальной ссылки |
| `process_referral(session, referrer_id, referred_id, mirror_bot_id)` | Привязка реферала |
| `check_milestones(session, user_id, mirror_bot_id)` | Проверка достижений |
| `send_money(session, from_id, to_id, amount, mirror_bot_id)` | Перевод между пользователями |

### 8.2 order_service.py

| Метод | Описание |
|-------|----------|
| `create_order(session, ...)` | Создание заказа + bulk_items + уведомление support_bot |
| `deduct_balance(session, user_id, amount)` | Списание с баланса |
| `refund_balance(session, user_id, amount)` | Возврат на баланс |
| `complete_order(session, order_id, result_data)` | Завершение заказа |
| `mark_not_found(session, order_id)` | Пометка "не найдено" + возврат |
| `notify_support_bot(order)` | HTTP-уведомление support_bot:8181 |
| `notify_log_channel(order, bot)` | Уведомление в лог-канал |
| `process_referral_commission(session, order)` | Начисление реферальных |

**Уведомление support_bot:**
```python
POST http://support_bot:8181/api/new-order
{
    "order_id": 123,
    "mirror_bot_id": 1,
    "category": "lookup",
    "service_name": "ssn_dob",
    "input_data": {...},
    "price": 2.80
}
```

### 8.3 payment_service.py

| Метод | Описание |
|-------|----------|
| `create_crypto_pay_invoice(amount, user_id)` | Создание инвойса CryptoBot |
| `create_cryptomus_invoice(amount, user_id)` | Создание инвойса Cryptomus |
| `check_payment_status(method, invoice_id)` | Проверка статуса платежа |
| `process_successful_payment(session, user_id, amount)` | Зачисление + реферальные + bot owner |

### 8.4 payment_monitor.py

Фоновый сервис, который периодически проверяет статус незавершённых платежей:
- Интервал: каждые 30 секунд
- Проверяет `pending` инвойсы в CryptoBot и Cryptomus
- При `paid` → автоматическое зачисление

### 8.5 crypto_pay.py / cryptomus.py

**CryptoPayService:**
- Создание инвойсов через CryptoBot API (`/api/createInvoice`)
- Проверка статуса (`/api/getInvoices`)
- Поддержка: BTC, ETH, USDT, TON, LTC, USDC
- Webhook обработка

**CryptomusService:**
- Создание инвойсов через Cryptomus API (`/v1/payment`)
- Проверка статуса (`/v1/payment/info`)
- HMAC-SHA512 подпись запросов
- Поддержка: BTC, ETH, USDT, LTC, TRX

### 8.6 product_service.py

| Метод | Описание |
|-------|----------|
| `get_available_products(session, category, service)` | Список доступных товаров |
| `get_product_by_id(session, product_id)` | Товар по ID |
| `purchase_product(session, user_id, product_id)` | Покупка товара |
| `deliver_product(session, purchase_id)` | Доставка (файл/текст) |
| `get_random_fullz(session, state, cs_range, age, gender)` | Случайный FULLZ из стока |
| `rate_product(session, purchase_id, rating)` | Оценка товара |

### 8.7 product_delivery_service.py

Доставка товаров покупателю:
- **Текстовые данные:** Отправка в сообщении (credentials, fullz data)
- **Файлы:** Отправка через `bot.send_document()`
- **PDF с watermark:** Через `FileService` + `pdf_watermark`
- **Архивация:** Пересылка в канал архива (если настроен)

### 8.8 file_service.py

| Метод | Описание |
|-------|----------|
| `get_file_path(file_id)` | Получение пути к файлу |
| `download_file(bot, file_id)` | Скачивание файла из Telegram |
| `apply_watermark(pdf_path, user_id)` | Наложение watermark на PDF |
| `send_file(bot, chat_id, file_path)` | Отправка файла |

### 8.9 parser.py / validator.py

**DataParser (parser.py):**
| Метод | Описание |
|-------|----------|
| `smart_parse_address_data(text, require_dob)` | Умный парсинг адреса из свободного текста |
| `parse_bulk_entries(text)` | Разделение bulk-текста на записи (по двойному переносу) |
| `extract_ssn(text)` | Извлечение SSN из текста |
| `extract_dob(text)` | Извлечение даты рождения |
| `extract_phone(text)` | Извлечение телефона |

Использует библиотеки: `usaddress`, `nameparser`, `dateutil`

**Validator (validator.py) — Pydantic-модели:**
| Модель | Поля | Для чего |
|--------|------|----------|
| `SSNLookupData` | first_name, last_name, address, city, state, zip_code, dob, ssn | SSN Lookup |
| `DLLookupData` | + dl (номер DL) | DL Lookup |
| `BGLookupData` | first_name, last_name, address, city, state, zip_code | Background |
| `CreditScoreLookupData` | + ssn, dob | Credit Score |
| `MVRLookupData` | + dl, dob | MVR |
| `FullMVRLookupData` | + dl, dob | Full MVR |
| `MMNLookupData` | first_name, last_name, address, city, state, zip_code | MMN |
| `EINLookupData` | raw_input | EIN |
| `PhoneSearchData` | phone | Phone Lookup |
| `FullzOrderData` | state, cs_range, age_range, gender | FULLZ |
| `DocumentOrderData` | first_name, last_name, state, dob, ssn | Documents |
| `CreditReportData` | first_name, last_name, address, city, state, zip, ssn, dob | Credit Reports |

**parse_freeform_text()** — универсальный парсер свободного текста с автоопределением полей

### 8.10 support_service.py

| Метод | Описание |
|-------|----------|
| `create_ticket(session, user_id, mirror_bot_id, category, subject, message)` | Создание тикета |
| `get_user_tickets(session, user_id, mirror_bot_id)` | Список тикетов пользователя |
| `get_ticket_messages(session, ticket_id)` | Сообщения тикета |
| `add_message(session, ticket_id, sender_type, message)` | Добавление сообщения |
| `close_ticket(session, ticket_id)` | Закрытие тикета |

**SupportNotificationService:**
- HTTP POST на `support_bot:8181/api/new-ticket` при создании тикета
- HTTP POST на `support_bot:8181/api/ticket-reply` при ответе

### 8.11 checkout_coupon_service.py

| Метод | Описание |
|-------|----------|
| `get_checkout_pricing(session, telegram_user_id, state_data)` | Расчёт финальной цены с учётом купона |
| `get_available_coupons(session, user_id, category, amount)` | Доступные купоны для заказа |

**CouponApplication (результат):**
```python
@dataclass
class CouponApplication:
    original_amount: Decimal
    discount_amount: Decimal
    final_amount: Decimal
    code: str | None
    coupon_id: int | None
```

### 8.12 menu_counts_service.py

Подсчёт количества товаров для отображения в меню:

| Метод | Описание |
|-------|----------|
| `get_all_counts(session, mirror_bot_id)` | Все счётчики для меню |
| `get_bank_counts(session)` | Количество банков по категориям |
| `get_cc_counts(session)` | Количество CC по категориям |
| `get_product_counts(session)` | Количество товаров |

**Redis-кэш:** Ключ `mirror_bot:menu_counts:v1:{mirror_bot_id}`, TTL 5 минут

### 8.13 Automation

#### CsAutomationRunner (cs_automation.py)
Автоматизация Credit Score lookup через внешний API:
```
Заказ lookup_credit → enqueue_order(order_id)
  → Фоновая очередь (asyncio.Queue)
  → Запрос к API (с retry)
  → Результат → order.result_data
  → Уведомление покупателя
  → Если ошибка → fallback на воркеров
```

#### CrAutomationRunner (cr_automation.py)
Автоматизация Credit Report через API:
```
Заказ cr_* → enqueue_order(order_id)
  → Фоновая очередь
  → Запрос к API (TransUnion/Experian/Equifax/LexisNexis)
  → PDF результат → отправка покупателю
  → Если ошибка → fallback на воркеров
```

#### SsnDlAutomationRunner (ssn_dl_automation.py)
Автоматизация SSN и DL lookup через usfull.info API:
```
Заказ lookup_ssn/lookup_dl → enqueue_order(order_id, service_type)
  → UsfullService.lookup_ssn() / lookup_dl()
  → Результат → order.result_data
  → Уведомление покупателя
  → Если не найдено → fallback на воркеров (notify_workers=True)
```

**UsfullService (usfull_service.py):**
- Клиент для usfull.info API (или self-hosted)
- Методы: `lookup_ssn()`, `lookup_dl()`, `lookup_bg()`
- Авторизация: API key
- Retry: 3 попытки с exponential backoff

### 8.14 Фоновые сервисы

#### Abandoned Cart Watcher
```
Каждые 30 минут:
  → Поиск корзин с status="active" и updated_at < 24h ago
  → Отправка напоминания покупателю
  → Пометка abandoned_notified=True
```

#### Review Request Service
```
Каждые 15 минут:
  → Поиск покупок (product_purchases) старше 24ч без отзыва
  → Отправка запроса на отзыв (Like/Dislike)
  → Пометка review_requested=True
```

---

## 9. Keyboards (клавиатуры)

### Reply Keyboard (reply.py)
`main_menu_keyboard(menu_categories, counts)` — строится динамически из `MirrorMenuCategory` с подсчётом товаров.

### Inline Keyboards (inline.py)

| Клавиатура | Описание |
|------------|----------|
| `language_keyboard` | Выбор языка (RU/EN/ZH/ES) |
| `rules_accept_keyboard` | Принять/отклонить правила |
| `profile_keyboard` | Меню профиля (заказы, баланс, рефералы, купоны, язык) |
| `topup_keyboard` | Выбор платёжной системы |
| `payment_link_keyboard` | Ссылка на оплату + проверка статуса |
| `lookup_keyboard` | Меню Lookup (SSN, DL, MVR, CS, BG, MMN, EIN, Phone, BA) |
| `phone_search_keyboard` | Типы Phone Lookup |
| `credit_reports_keyboard` | Типы кредитных отчётов |
| `confirm_keyboard` | Подтверждение/отмена заказа |
| `bulk_confirmation_keyboard` | Подтверждение/редактирование/отмена bulk |
| `bulk_order_keyboard` | Кнопка перехода в bulk-режим |
| `esim_main_keyboard` | Меню eSIM (SMS / Data / Configurator / Google Voice) |
| *(в `esim.py`)* | Клавиатуры каталога и количества для SMS/Data/GV строятся динамически из `AccountItem` (не в `inline.py`) |
| `support_categories_keyboard` | Категории поддержки |
| `reorder_keyboard` | «Заказать ещё» — маршрутизация по `service_name` (в т.ч. префиксы eSIM, см. §7.11) |
| `cs_retry_keyboard` | Кнопка повтора CS automation |

### CC Keyboards (cc.py)

| Клавиатура | Описание |
|------------|----------|
| `cc_main_keyboard` | Категории CC + Enroll/OTP/NFC/Selfreg |
| `cc_catalog_keyboard` | Список товаров в категории |
| `cc_item_detail_keyboard` | Детали товара + Buy |
| `cc_buy_confirm_keyboard` | Подтверждение покупки CC |
| `cc_result_keyboard` | Результат + Report Issue |
| `cc_specials_keyboard` | Специальные товары (Enroll/OTP/NFC) |
| `cc_feedback_done_keyboard` | После отзыва |
| `cc_report_done_keyboard` | После жалобы |

---

## 10. Constants (константы и данные)

### prices.py
**SystemFees:** Комиссии платформы (3% CryptoPay, 2% Cryptomus, 4% реферальные)

**BulkDiscounts:** Скидки за количество (банки: 2-5%, eSIM: 5-15%)

**ServicePrices:** Все цены сервисов (~200 позиций):
- Lookup: SSN $2.80, DL $7, MVR $11, CS $2, BG $2, MMN $9, EIN $11
- CR: TU/EX/EQ $18, LN $25, WH $5
- FULLZ: Personal $10, +CS $15, Business $30, Military $20
- Documents: DL $50, DL+Selfie $80, Passport $80, SSN Card $30
- Banks: VCC $15-45, Personal $25-90, Business $35-100, Crypto $15-45
- eSIM Configurator / базовые SMS в конфигураторе: константы `ESIM_*` в `prices.py`
- eSIM SMS/Data/GV в mirror-боте: цены из поля `AccountItem.price` (категории `esim_sms`, `esim_data`, `gv`)
- Accounts: BG $3-12, Lookup $5-8
- AddInfo: $3-15

### language_loader.py
Кэширующий загрузчик текстов и кнопок:
- `LanguageLoader.get_texts(lang)` → `texts_{lang}.BotTexts`
- `LanguageLoader.get_buttons(lang)` → `buttons_{lang}.ButtonTexts`
- Поддержка: en, ru, zh, es
- Fallback на en при отсутствии перевода

### bank_data.py
Хардкодированный каталог банков (fallback когда `BankItem` в БД пуст):
- 14 VCC, 15 Personal, 10 Business, 6 Crypto, 9 Merchant, 10 Logs
- Методы: `get_bank_by_id()`, `get_category_items()`, `get_seller_bank_for_purchase()`

### service_eta.py
ETA для всех сервисов:
- Lookup: 10-90 минут
- CR: 4-30 минут
- FULLZ/Documents/Banks: 4-24 часа
- eSIM: 1-6 часов

---

## 11. Utils (утилиты)

### media_library.py
`resolve_bot_photo(*keys, fallback_path)` — поиск фото в `photo/` и `media/` директориях по ключу. Поддерживает: jpg, jpeg, png, webp, gif.

### message_utils.py
- `safe_edit_message(callback, text, reply_markup, parse_mode)` — безопасное редактирование сообщения (с fallback на delete+send)
- `safe_answer_callback(callback, text, show_alert)` — безопасный ответ на callback

### multilang_helper.py
- `get_multilang_texts_and_buttons(language)` — получение текстов и кнопок
- `format_error_message(texts, error_type, **kwargs)` — форматирование ошибок
- `get_example_for_service(texts, service, is_bulk)` — пример для сервиса

### product_translations.py
`ProductTranslations` — переводы названий продуктов на en/ru/zh:
- `get_category_name(category_id, language)` — название категории
- `get_service_name(service_id, language)` — название сервиса
- Покрывает все VCC, банки, lookup, CR, FULLZ, documents, eSIM, accounts, addinfo

---

## 12. Filters (фильтры)

### ServiceFilter
```python
class ServiceFilter(Filter):
    def __init__(self, service: Union[str, List[str]]):
        self.services = [service] if isinstance(service, str) else service
    
    async def __call__(self, message: Message, state: FSMContext) -> bool:
        data = await state.get_data()
        return data.get("service") in self.services
```

Используется для маршрутизации данных в FSM — когда пользователь в `OrderStates.waiting_data`, фильтр проверяет, какой именно сервис активен, и направляет на нужный handler.

---

## 13. Взаимодействие с shared модулем

| Shared модуль | Использование в mirror_bot |
|---------------|---------------------------|
| `shared.database.models` | Все ORM-модели (User, Order, MirrorBot, Seller*, Product*, etc.) |
| `shared.database.session` | `async_session_maker` для создания DB-сессий |
| `shared.middlewares.error_logging` | `GlobalErrorLoggingMiddleware` — логирование ошибок |
| `shared.services.bot_pool` | `get_mirror_bot_instance()` — получение экземпляра бота |
| `shared.services.coupon_service` | Логика купонов (создание, активация, применение) |
| `shared.services.menu_category_service` | `MirrorMenuCategory` — управление категориями меню |
| `shared.services.menu_count_cache_service` | Redis-кэш счётчиков меню |
| `shared.services.runtime_pricing_service` | Динамические цены из БД |
| `shared.services.ui_translation_service` | `UiTranslator` — переводы из БД |
| `shared.services.nocodb_service` | Логирование в NocoDB |
| `shared.services.seller_order_delivery_service` | Доставка seller-заказов |
| `shared.services.notification_service` | Отправка уведомлений |
| `shared.services.product_audit_service` | Аудит действий с товарами |
| `shared.catalog` | Каталог банков (DB + fallback) |
| `shared.cc_catalog` | Каталог CC (DB + fallback) |
| `shared.utils.chat_filter` | Фильтрация текста в чатах |
| `shared.utils.chat_render` | Рендеринг чатов (пагинация) |
| `shared.utils.seller_product_meta` | Метаданные товаров продавцов |

---

## 14. Потоки данных

### Flow 1: Lookup-заказ (SSN/DL/CS/BG/MVR/MMN/EIN)
```
Покупатель нажимает "Search" → lookup/main.py
  → Выбирает сервис (SSN/DL/CS/...)
  → Вводит данные → parser.py парсит → validator.py валидирует
  → Подтверждение → checkout_coupon_service проверяет купон
  → OrderService.deduct_balance() → списание с баланса
  → OrderService.create_order() → запись в orders + bulk_order_items
  → Automation:
    - lookup_ssn → SsnDlAutomationRunner → usfull API
    - lookup_dl → SsnDlAutomationRunner → usfull API
    - lookup_credit → CsAutomationRunner → CS API
    - Остальные → HTTP POST support_bot:8181 → воркер берёт заказ
  → Результат:
    - Автоматизация: result_data → уведомление покупателю
    - Воркер: worker_orders → выполнение → result_data → main_bot API → уведомление
  → Если NOT FOUND: refund на баланс
```

### Flow 2: Credit Report
```
Покупатель → "CREDIT REPORTS" → credit_reports.py
  → Выбор типа (TU/EX/EQ/LN/WH)
  → Ввод данных (имя, адрес, SSN, DOB)
  → Подтверждение → списание → создание заказа
  → CrAutomationRunner → API запрос
  → PDF результат → отправка покупателю
  → Если ошибка → fallback на воркеров
```

### Flow 3: Покупка банка (Seller)
```
Покупатель → "BANKS" → banks.py
  → Выбор категории → выбор банка
  → Если есть seller_bank (stock > 0):
    → Покупка → создание SellerOrder (escrow)
    → Мгновенная выдача credentials
    → Продавец получает уведомление
    → Через 24ч → auto_complete → escrow → seller.withdrawable_balance
  → Если per-order (из BankData):
    → Создание Order → воркер выполняет
```

### Flow 4: Покупка CC
```
Покупатель → "CC" → cc.py
  → Выбор категории → список SellerCCItem
  → Выбор товара → детали → подтверждение
  → Списание → создание SellerCCOrder
  → Мгновенная выдача данных CC
  → Feedback: Like/Dislike → seller_score обновляется
  → Report Issue → скриншот → тикет
```

### Flow 5: Пополнение баланса
```
Покупатель → "Top-up" → payment.py
  → Выбор: CryptoPay / Cryptomus
  → Ввод суммы ($10-$5000)
  → Создание инвойса → ссылка на оплату
  → Покупатель оплачивает в крипте
  → Проверка статуса (кнопка или payment_monitor)
  → При paid:
    → user.balance += amount
    → Transaction(type="deposit")
    → Referral: referrer.balance += amount * 4%
    → Bot Owner: bot_owner.balance += amount * 7%
    → bot_owner_stats обновляется
```

### Flow 6: Поддержка
```
Покупатель → "Support" → support.py
  → Выбор категории (Payment/Product/General/Partnership)
  → Ввод темы → ввод описания
  → SupportService.create_ticket()
  → HTTP POST support_bot:8181/api/new-ticket
  → Оператор отвечает в support_bot
  → Покупатель видит ответ в "My Tickets"
  → Может ответить → HTTP POST support_bot:8181/api/ticket-reply
```

### Flow 7: Корзина
```
Покупатель добавляет товары → cart.py
  → CartItem создаётся в shopping_carts/cart_items
  → "View Cart" → список товаров с ценами
  → "Checkout" → проверка баланса → покупка всех товаров
  → Создание отдельных заказов для каждого товара
  → Если корзина заброшена (24ч) → abandoned_cart_service → напоминание
```

---

## 15. Таблицы БД

### Таблицы, в которые mirror_bot ПИШЕТ:

| Таблица | Операции | Handler/Service |
|---------|----------|-----------------|
| `users` | CREATE, UPDATE (balance, language, username) | start, profile, payment, order_service |
| `orders` | CREATE | order_service |
| `bulk_order_items` | CREATE | order_service |
| `transactions` | CREATE | payment_service, order_service |
| `referrals` | CREATE | user_service |
| `seller_orders` | CREATE | banks, seller_specials |
| `seller_cc_orders` | CREATE | cc |
| `seller_nfc_orders` | CREATE | seller_specials |
| `seller_otp_orders` | CREATE | seller_specials |
| `seller_enroll_orders` | CREATE | seller_specials |
| `seller_selfreg_ba_orders` | CREATE | seller_specials |
| `seller_selfreg_cc_orders` | CREATE | seller_specials |
| `seller_check_orders` | CREATE | seller_specials |
| `seller_logs_orders` | CREATE | seller_specials |
| `brute_bank_orders` | CREATE | brute_bank |
| `seller_conversations` | CREATE | buyer_chat |
| `seller_chats` | CREATE | buyer_chat |
| `seller_order_disputes` | CREATE | seller_specials |
| `support_tickets` | CREATE | support_service |
| `support_messages` | CREATE | support_service |
| `shopping_carts` | CREATE, UPDATE | cart |
| `cart_items` | CREATE, DELETE | cart |
| `wishlist_items` | CREATE, DELETE | wishlist |
| `product_purchases` | CREATE | product_service |
| `product_ratings` | CREATE | products |
| `coupons` / `user_coupons` | UPDATE | profile, checkout_coupons |
| `coupon_redemptions` | CREATE | checkout_coupon_service |
| `manual_deliveries` | CREATE | education |
| `bot_owners` | UPDATE (balance) | payment |
| `bot_owner_stats` | UPDATE | payment |

### Таблицы, из которых mirror_bot ЧИТАЕТ:

| Таблица | Для чего |
|---------|----------|
| `mirror_bots` | Проверка is_active |
| `mirror_menu_categories` | Построение меню |
| `bank_items` | Каталог банков |
| `seller_banks` | Товары продавцов (банки) |
| `seller_cc_items` | Товары CC |
| `seller_nfc/otp/enroll/selfreg/check/logs/document/fullz_items` | Все типы товаров |
| `brute_bank_items` / `brute_bank_groups` | Brute Bank каталог |
| `products` | Товары (документы, fullz) |
| `product_catalog_services` | Каталог сервисов |
| `cc_categories` / `cc_items` | Каталог CC |
| `account_categories` / `account_items` / `account_inventory` | Аккаунты |
| `education_categories` / `education_subscriptions` / `education_manuals` | Обучение |
| `service_prices` / `pricing_config` | Цены |
| `coupons` / `user_coupons` | Купоны |
| `another_service_buttons` | Динамические кнопки |
| `system_settings` | Системные настройки |
| `sellers` | Информация о продавцах (score, status) |

---

## 16. Схема обработки запроса

```
Telegram Update
  │
  ▼
DebugLoggerMiddleware          ← логирование
  │
  ▼
DatabaseSessionMiddleware      ← data["session"] = AsyncSession
  │
  ▼
GlobalErrorLoggingMiddleware   ← try/except + NocoDB log
  │
  ▼
MirrorBotMiddleware            ← data["mirror_bot_id"] = N
  │
  ▼
UserUpdateMiddleware           ← обновление username в БД
  │
  ▼
LanguageMiddleware             ← data["texts"], data["buttons"], data["ui_texts"]
  │
  ▼
BotStatusCheckMiddleware       ← БЛОК если бот деактивирован
  │
  ▼
BanCheckMiddleware             ← БЛОК если пользователь забанен
  │
  ▼
ReplyKeyboardCancelMiddleware  ← сброс FSM при нажатии кнопки меню
  │
  ▼
Router matching                ← поиск подходящего handler
  │
  ├── start.router         (F.text == "/start", "/menu")
  ├── dynamic_menu.router  (F.text matches DB menu buttons)
  ├── profile.router       (F.text == "My Profile", callbacks)
  ├── payment.router       (F.text == "Top-up", callbacks)
  ├── lookup_main.router   (F.text == "Search", callbacks)
  ├── ssn.router           (callback "lookup_ssn", FSM states)
  ├── phone.router         (callback "phone_*", FSM states)
  ├── others.router        (callback "lookup_*", FSM states)
  ├── bank_lookup.router   (callback "lookup_ba*", FSM states)
  ├── credit_reports.router (F.text == "CREDIT REPORTS", callbacks)
  ├── banks.router         (F.text == "BANKS", callbacks)
  ├── esim.router          (F.text == "eSIM", callbacks)
  ├── accounts.router      (F.text == "Accounts", callbacks)
  ├── addinfo.router       (F.text == "Add info", callbacks)
  ├── documents.router     (F.text == "DOCUMENTS", callbacks)
  ├── fullz.router         (F.text == "FULLZ", callbacks)
  ├── products.router      (product callbacks)
  ├── cc.router            (F.text == "CC", callbacks)
  ├── education.router     (education callbacks)
  ├── seller_specials.router (seller special callbacks)
  ├── brute_bank.router    (brute callbacks)
  ├── buyer_chat.router    (chat callbacks)
  ├── buyer_orders.router  (order callbacks)
  ├── wishlist.router      (wishlist callbacks)
  ├── cart.router          (cart callbacks)
  ├── catalog_search.router (search callbacks)
  ├── onboarding.router    (onboarding callbacks)
  ├── vip_watchlist.router (VIP callbacks)
  └── fallback.router      (CATCH-ALL — последний)
```

---

## Сводная таблица: Handler → Service → Таблицы

| Handler | Service | Таблицы (запись) | Таблицы (чтение) |
|---------|---------|------------------|-------------------|
| start | UserService | users, referrals | users, mirror_menu_categories |
| profile | UserService, CouponService | users, transactions, user_coupons | users, referrals, coupons |
| payment | PaymentService, CryptoPayService | users, transactions, bot_owners | users |
| lookup/* | OrderService, Automation | orders, bulk_order_items | users |
| credit_reports | OrderService, CrAutomation | orders, bulk_order_items | users |
| banks | OrderService, ProductService | seller_orders, orders | bank_items, seller_banks, users |
| cc | OrderService | seller_cc_orders | cc_categories, seller_cc_items |
| fullz | OrderService, ProductService | orders, product_purchases | products, seller_fullz_items |
| documents | OrderService | orders | products, seller_document_items |
| esim | OrderService | orders, bulk_order_items | users |
| accounts | OrderService, ProductService | orders | account_items, account_inventory |
| addinfo | OrderService | orders | users |
| education | ProductService | manual_deliveries | education_*, users |
| seller_specials | OrderService | seller_*_orders, seller_order_disputes | seller_*_items |
| brute_bank | OrderService | brute_bank_orders | brute_bank_items, brute_bank_groups |
| buyer_chat | — | seller_chats | seller_conversations, seller_chats |
| buyer_orders | — | — | seller_orders, seller_cc_orders |
| support | SupportService | support_tickets, support_messages | support_tickets |
| cart | — | shopping_carts, cart_items | shopping_carts, cart_items |
| wishlist | — | wishlist_items | wishlist_items |
| checkout_coupons | CheckoutCouponService | coupon_redemptions | coupons, user_coupons |

---

*Документ сгенерирован на основе полного анализа кодовой базы mirror_bot и shared модулей.*
