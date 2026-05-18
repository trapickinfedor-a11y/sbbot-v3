# Полная архитектура системы NewLookup

> Автогенерированная документация — полная структура каталогов, потоков загрузки, модерации и навигации для всех ролей.

---

## Оглавление

1. [Покупатель (mirror_bot)](#1-покупатель-mirror_bot)
   - [Главное меню](#11-главное-меню)
   - [BANKS](#12-banks)
   - [CC](#13-cc)
   - [Brute Bank](#14-brute-bank)
   - [NFC](#15-nfc)
   - [OTP](#16-otp)
   - [Enroll](#17-enroll)
   - [Logs](#18-logs)
   - [Checks](#19-checks)
   - [Accounts](#110-subscriptionsaccounts)
   - [PROS & FULLZ](#111-pros--fullz)
   - [Documents](#112-documents)
   - [eSIM](#113-esim)
   - [Общий поток покупки](#114-общий-поток-покупки)
2. [Селлер (seller_bot + Mini App)](#2-селлер-seller_bot--mini-app)
   - [Регистрация селлера](#21-регистрация-селлера)
   - [Главное меню seller_bot](#22-главное-меню-seller_bot)
   - [Загрузка товаров — таблица](#23-загрузка-товаров--таблица)
   - [FSM-потоки загрузки](#24-fsm-потоки-загрузки)
   - [Mini App — вкладки](#25-mini-app--вкладки)
   - [Mini App — API эндпоинты](#26-mini-app--api-эндпоинты)
3. [Модератор / Поддержка (support_bot)](#3-модератор--поддержка-support_bot)
   - [Главное меню модератора](#31-главное-меню-модератора)
   - [Возможности модерации](#32-возможности-модерации)
   - [Поток модерации товара](#33-поток-модерации-товара)
4. [Worker Bot](#4-worker-bot)
5. [Структура файлов проекта](#5-структура-файлов-проекта)
   - [seller_bot/](#51-seller_bot)
   - [mirror_bot/](#52-mirror_bot)
   - [support_bot/](#53-support_bot)
   - [web_panel/ (Mini App)](#54-web_panel-mini-app)
   - [shared/](#55-shared)
6. [База данных — ключевые модели](#6-база-данных--ключевые-модели)
7. [Сводная таблица: кто что видит](#7-сводная-таблица-кто-что-видит)
8. [Pagination & UX — параметры по секциям](#8-pagination--ux--параметры-по-секциям)

---

## 1. Покупатель (mirror_bot)

### 1.1 Главное меню

Reply-клавиатура строится из БД (`MirrorMenuCategory`) через `MenuCategoryService.get_keyboard_payload()`.

```
┌──────────────────────────────────────────────┐
│  Education                                    │
│  My profile          │  Top-up balance         │
│  Search (Lookup)     │  CREDIT REPORTS         │
│  BANKS               │  Subscriptions/Accounts │
│  CC                                           │
│  PROS & FULLZ        │  DOCUMENTS              │
│  Add info in CR      │  eSIM                   │
│  Support             │  Referrals +12%         │
│  Other Services                               │
│  VIP Watchlist — $500                         │
└──────────────────────────────────────────────┘
```

| Позиция | Кнопки | Route Key |
|---------|--------|-----------|
| 5 | Education | `education` |
| 10 | My profile, Top-up balance | `my_profile`, `topup_balance` |
| 20 | Search, CREDIT REPORTS | `search`, `credit_reports` |
| 30 | BANKS, Subscriptions/Accounts | `banks`, `accounts` |
| 40 | CC | `cc` |
| 50 | PROS & FULLZ, DOCUMENTS | `pros_fullz`, `documents` |
| 60 | Add info in CR, eSIM | `add_info_cr`, `esim` |
| 70 | Support, Referrals +12% | `support`, `referrals` |
| 80 | Other Services | `another_services` |
| 90 | VIP Watchlist — $500 | `vip_watchlist` |

---

### 1.2 BANKS

```
BANKS Main (banks_main)
│
├── VCC / Personal / Business / Crypto
│   ├── Available [n] / Per Order [n]
│   │
│   ├── Available:
│   │   └── Подкатегории по bank_name [count]  (15/стр)
│   │       └── Items (10/стр, сортировка по цене ↑↓)
│   │           └── Карточка товара
│   │               └── Кол-во → Покупка → Confirm → Reveal
│   │                   └── Feedback / Report
│   │
│   └── Per Order:
│       └── Items → bank_qty → confirm_bulk_bank
│
├── Merchant
│   └── bank_name подкатегории → items → buy
│
├── Brute Bank → (см. раздел 1.4)
│
└── Logs BA → (см. раздел 1.8)
```

**Callback-цепочка Banks:**
- `banks_main` → `banks_vcc` / `banks_personal` / `banks_business` / `banks_crypto` / `banks_merchant`
- `banks_section:{category}:{section}` → `banks_bnpage:{cat}:{section}:{page}`
- `banks_pick:{cat}:{section}:{idx}` → `banks_pick_page:{cat}:{section}:{idx}:{page}:{sort}`
- `banks_sort:{cat}:{section}:{idx}:{sort_next}`
- `bank_item:{section}:{id}` → `bank_qty` → `bank_buy` → `bank_reveal` → `bank_feedback`

---

### 1.3 CC

```
CC Main (cc_main)
│
├── 🇺🇸 USA CC (cc_cat:usa)
├── 🌍 ALL WORLD CC (cc_cat:world)
├── ⛔ NON VBV (cc_cat:non_vbv)
│   │   NON VBV фильтрует is_non_vbv=True через ВСЕ категории
│   │
│   ├── 🔍 BIN поиск (6 цифр) — cc_ask_bin
│   ├── 🔍 ZIP поиск — cc_ask_zip
│   ├── ✖ Clear filters
│   └── Items (10/стр, сортировка ↑↓)
│       Кнопка: "Chase Visa ***4521 | $25.00"
│       └── Детали (full description) → cc_buy → cc_buy_confirm
│           └── cc_reveal (15 мин) → Report Issue
│
├── 🏦 Enroll → (см. раздел 1.7)
├── 🔑 OTP → (см. раздел 1.6)
├── 📱 NFC → (см. раздел 1.5)
└── 🏧 Selfreg CC → Items → Buy → Confirm → Reveal
```

**Callback-цепочка CC:**
- `cc_main` → `cc_cat:{code}` → `cc_listpg:{cat}:{page}:{sort}:{bin}:{zip}`
- `cc_ask_bin:{cat}:{sort}:{zip}` / `cc_ask_zip:{cat}:{sort}:{bin}`
- `cc_item:{cat}:{id}:{bin}:{zip}` → `cc_buy:{seller_item_id}:{category_code}` → `cc_buy_confirm:{item_id}`

**FSM-состояния CC:** `CCFilterStates.waiting_bin`, `CCFilterStates.waiting_zip`

---

### 1.4 Brute Bank

```
Brute Bank (banks_brute)
│
├── 🔎 Поиск по банку (brute_search)
├── ✖ Очистить поиск (brute_clear_search)
│
└── Группы (8/стр) — "GTE [AN:RN+INST YODLEE] [355]"
    │   brute_group:{id}:{page}:{mode}:{sort}
    │
    └── Варианты (сортировка по цене ↑↓)
        "$500-$1000 Checking $35 [12]"
        │   brute_variant:{gid}:{range}:{type}:{price}:{page}:{mode}:{sort}
        │
        └── Детали (Range, Type, Price, Available, Your balance)
            └── ⚡ Buy Now — brute_buy → brute_buy_confirm
                └── Reveal (60 мин) → Like / Dislike / Report
```

**Callback-цепочка Brute:**
- `banks_brute` → `brute_page:{page}:{mode}` → `brute_group:{id}:{page}:{mode}:{sort}`
- `brute_variant:{gid}:{range}:{type}:{price}:{page}:{mode}:{sort}`
- `brute_buy:{...}` → `brute_buy_confirm:{...}` → `brute_reveal:{order_id}`

---

### 1.5 NFC

```
NFC (через CC Main → 📱 NFC или Specials)
│
├── 🍎 Apple Pay [count]  (seller_specials_nfc:ap:0:price_asc)
├── 🤖 Google Pay [count] (seller_specials_nfc:gp:0:price_asc)
└── 📎 Other [count]      (seller_specials_nfc:other:0:price_asc)
    │
    └── Items (10/стр, сортировка ↑↓)
        Кнопка: "Chase US | $120.00"
        └── seller_specials_detail:nfc:{id}
            └── Buy → Confirm → Reveal
```

Запрос к БД: `func.lower(SellerNFCItem.nfc_type) == nfc_type.lower()` (case-insensitive).

---

### 1.6 OTP

```
OTP (через CC Main → 🔑 OTP или Specials)
│
└── Единый список (без подкатегорий)
    Items (10/стр, сортировка ↑↓)
    Кнопка: "Chase $5,000 | $85.00 ·seller"
    │   sms_access_type: ·seller = seller_mediated, ·acct = account_access
    │
    └── seller_specials_detail:otp:{id}
        └── Buy → Confirm → Reveal
```

---

### 1.7 Enroll

```
Enroll (через CC Main → 🏦 Enroll или Specials)
│
├── Предзагруженные категории-порталы (15/стр):
│   FDECS [12] │ DIGITALCARDSERVICE [8] │ MYCARDINFO [5]
│   CARD SUITE LIGHT │ CardNav │ FIREFIGHTERS
│   COAST CENTRAL │ WEB ACCESS │ Card Suite
│   Myaccountaccess │ CENTRESUITE (minik)
│
└── Внутри категории — плоский список (12/стр, сортировка ↑↓)
    Кнопка: "Chase $2,400 | $45.00"
    │   Показывает bank_name (или portal), balance, price
    │
    └── seller_specials_detail:enroll:{id}
        └── Buy → Confirm → Reveal
```

**Callback-цепочка Enroll:**
- `seller_specials_list:enroll` → `seller_specials_enroll_cat:{code}:{page}:{sort}`
- `seller_specials_detail:enroll:{id}` → `seller_specials_buy:enroll:{id}` → `seller_specials_buy_confirm:enroll:{id}`

---

### 1.8 Logs

```
Logs (через BANKS → Logs BA или Specials)
│
├── Фильтры по цене:
│   All $ │ $0–25 │ $25–50 │ $50–100 │ $100+
│
└── Items (10/стр, сортировка ↑↓)
    Кнопка: "Chase | $35.00"
    │
    └── seller_specials_detail:logs:{id}
        └── Buy → Confirm → Reveal
```

**Callback-цепочка Logs:**
- `seller_specials_list:logs` → `seller_specials_logs_pg:{page}:{sort}:{price_filter}`

---

### 1.9 Checks

```
Checks (через Documents → Checks или Specials)
│
├── Подкатегории по check_type с [count]:
│   All checks │ Personal │ Business │ Payroll │ Cashier
│
└── Items (10/стр, сортировка ↑↓)
    Кнопка: "Personal Chase $500 CA | $15.00"
    │
    └── seller_specials_detail:checks:{id}
        └── Buy → Confirm → Reveal (скан-фото + данные)
```

**Callback-цепочка Checks:**
- `seller_specials_list:checks` → `seller_specials_checks_type:{type}:{page}:{sort}`
- Запрос `.join(Seller)` с фильтром `Seller.is_approved == True, Seller.is_active == True`

---

### 1.10 Subscriptions/Accounts

```
Accounts Main (accounts_main)
│
└── Категории из AccountCategory
    └── Items (acc_page)
        └── acc_item → acc_buy / acc_custom (custom qty)
            └── confirm_bulk_account → покупка
```

**FSM-состояния:** `AccountStates.waiting_for_quantity`, `waiting_custom_qty`, `confirm_bulk_purchase`

---

### 1.11 PROS & FULLZ

```
Fullz Main
│
├── Personal
│   ├── With CS/CR → fullz_state → fullz_cs → fullz_age →
│   │   fullz_gender → fullz_carrier → fullz_bank → fullz_report →
│   │   fullz_qty → fullz_confirm
│   ├── Fixed profiles (700plus и т.д.) → fullz_fixed_state → confirm
│   └── Random → fullz_state → ...
│
└── Business
    └── fullz_company → fullz_cs → fullz_loan → fullz_qty → fullz_confirm
```

**FSM-состояния:** `FullzStates` — 16 состояний (select_type, select_state, select_credit_score, select_age, select_gender, select_carrier_exclusion, select_bank_exclusion, select_report_group, select_quantity, waiting_custom_qty, select_company_type, select_loan_size, select_fixed_quantity, waiting_fixed_custom_qty, fixed_confirmation, confirmation)

---

### 1.12 Documents

```
Documents Main
│
├── DL / Passport / Business Docs
│   └── doc_{type}_state → doc_{type}_page → выбор штата
│       └── заказ документа
│
└── Checks → seller_specials (см. раздел 1.9)
```

---

### 1.13 eSIM

```
eSIM Main
│
├── SMS / Data / Google Voice
│
└── Items (esim_item) → Qty (esim_iq) → Buy (esim_ib)
    └── Confirm → доставка → фидбек
```

---

### 1.14 Общий поток покупки

```
Main Menu → Секция (BANKS / CC / ...)
  → Подсекция (VCC / USA CC / ...)
    → Подкатегория (bank_name / portal / nfc_type / ...)
      → Список товаров (пагинация + сортировка)
        → Карточка товара (описание, цена, наличие)
          → Количество (для банков) или сразу Buy
            → Подтверждение (цена, вычет с баланса)
              → Оплата (списание баланса)
                → Reveal / Open Product
                  → Feedback (Like/Dislike) / Report Issue / Ask Seller
```

**Гарантийные окна:**
- CC: 15 минут
- Brute Bank: 60 минут
- Banks / NFC / OTP / Enroll / Logs / Checks: по настройкам `guarantee_policy`

---

## 2. Селлер (seller_bot + Mini App)

### 2.1 Регистрация селлера

```
/start → Выбор языка (EN / RU / ZH / ES)
  → Принятие правил (seller_rules_accept)
    → Ожидание активации:
      │
      ├── Вариант 1: Админ approve (admin_approve_seller:{id})
      │   → SellerService.approve_seller()
      │
      └── Вариант 2: BTCPay депозит
          → Выбор пакета (seller_deposit_package:bank / cc)
            → BTCPay invoice → seller_deposit_check
              → SellerDepositService.process_paid_invoice()
                → activate_seller_access()
```

**Middleware (`SellerAuthMiddleware`):**
- Admins (`ADMIN_IDS`): `is_admin=True`, `is_seller=True`
- Active seller: `is_seller=True`, `seller`, `seller_actor`
- Pending approval: `pending_approval=True`, `is_seller=False`
- New user: `is_seller=False`, `seller=None`

**Helpers:**
- Owner может пригласить помощников с ролями: `upload_helper`, `support_helper`, `manager_helper`
- Доступ контролируется через `seller_actor.can_upload()`, `can_manage_finance()` и т.д.

---

### 2.2 Главное меню seller_bot

```
┌────────────────────────────────────────────────┐
│  🏦 My Banks              │  📤 Universal Upload │
│  ➕ Add Bank / Enrol      │  📋 My Uploads       │
│  💳 My CC                 │  ➕ Add CC Item       │
│  📱 Add NFC               │  🔑 Add OTP Card     │
│  🏧 Add Selfreg CC        │  🏦 Add Enroll       │
│  📄 Add Check             │                       │
│  📁 My Documents          │  ➕ Add Document      │
│  👤 My Fullz              │  ➕ Add Fullz         │
│  🔓 Brute Bank                                    │
│  📊 My Listings           │  📦 My Orders         │
│  💬 Messages (N)                                   │
│  🌴 Enable / Disable Vacation                     │
│  🖥 Mini App (WebApp кнопка)                      │
│  👥 Helpers  │  💸 Withdraw  │  🚪 Leave System   │
│  👤 Profile                                        │
└────────────────────────────────────────────────┘
```

| Кнопка | callback_data | Доступ |
|--------|---------------|--------|
| My Banks | `seller_my_banks` | Все |
| Universal Upload | `seller_upload_product` | can_upload |
| Add Bank / Enrol | `seller_add_bank` | can_upload |
| My Uploads | `seller_uploads` | Все |
| My CC | `seller_my_cc` | Все |
| Add CC Item | `seller_add_cc` | can_upload |
| Add NFC | `seller_add_nfc` | can_upload |
| Add OTP Card | `seller_add_otp` | can_upload |
| Add Selfreg CC | `seller_add_selfreg_cc` | can_upload |
| Add Enroll | `seller_add_enroll` | can_upload |
| Add Check | `seller_add_check` | can_upload |
| My Documents | `seller_my_docs` | Все |
| Add Document | `seller_add_doc` | can_upload |
| My Fullz | `seller_my_fullz` | Все |
| Add Fullz | `seller_add_fullz` | can_upload |
| Brute Bank | `seller_brute_bank` | can_upload |
| My Listings | `seller_my_listings` | Все |
| My Orders | `seller_orders` | Все |
| Messages (N) | `seller_messages` | Все |
| Vacation toggle | `seller_vacation_toggle` | Все |
| Mini App | WebApp URL | Все (если `SELLER_MINI_APP_URL` задан) |
| Helpers | `seller_helpers` | Owner only |
| Withdraw | `seller_withdraw` | Owner only |
| Leave System | `seller_leave_system` | Owner only |
| Profile | `seller_profile` | Все |

---

### 2.3 Загрузка товаров — таблица

| Товар | Seller Bot | Mini App | Обязательные поля при загрузке |
|-------|-----------|----------|-------------------------------|
| **Bank** (VCC/Personal/Business/Crypto/Merchant) | `Add Bank` — wizard | Bank tab (форма) | Категория, product_type, product_subtype, bank_name, цена, описание, инструкция, кол-во, тип поддержки |
| **CC** | `Add CC` — single/bulk | Нет | Категория (USA/WORLD), NON VBV флаг, данные карты (NUMBER\|EXP\|CVV\|...), цена |
| **Brute Bank** | `Brute Bank` — single/bulk | Brute tab (single/bulk + file parse) | bank_name, bank_code, **attributes**, balance_range, account_type, credentials, balance, цена |
| **NFC** | `Add NFC` | API `item_type=nfc` | nfc_type (AP/GP/**Other**), bank_name, country, state, zip, цена, ZIP-файл |
| **OTP** | `Add OTP` | API `item_type=otp` | bank_name, balance, has_fullz, sms_access_type (seller_mediated/account_access), цена |
| **Enroll** | `Add Enroll` | Нет | Категория-портал (из списка или **запрос нового** 1-6ч), bank_name, balance, ZIP, state, цена, card_type (credit/debit) |
| **Selfreg CC** | `Add Selfreg CC` | API `item_type=selfreg_cc` | bank_name, card_name, limits, state, zip, email, phone, online_access, цена |
| **Checks** | `Add Check` | Нет | check_type (Personal/Business/Payroll/Cashier), bank_name, amount, state, цена, скан-фото |
| **Logs** | Universal Upload | Нет | Paste / .txt файл |
| **Selfreg BA** | Universal Upload | Нет | Paste / .txt файл |
| **Documents** | `Add Document` | Нет | doc_type (DL/Passport/Business), state, quality, hologram, selfie, description, цена, sample |
| **Fullz** | `Add Fullz` | Нет | fullz_type, state, credit_score, age, gender, company_type, loan_size, report_group, quantity, description, цена, файл данных |
| **Bulk Banks** | Bulk Import | Нет | CSV/JSON файл |

**Требование депозита:** `SellerDepositService.has_upload_access(seller, package_code)`
- **Bank** пакет: bank, enrol, brute, logs, nfc, otp, checks
- **CC** пакет: cc, selfreg_cc

---

### 2.4 FSM-потоки загрузки

#### Bank (Add Bank / Enrol)

```
AddBankStates:
waiting_product_type → waiting_product_subtype → waiting_category →
waiting_add_mode → waiting_bank_type → waiting_name → waiting_price →
waiting_description → waiting_instruction → waiting_extra_text →
waiting_extra_bool → waiting_support_mode → waiting_number_access →
waiting_rental_days → waiting_number_change_allowed →
waiting_auto_unpublish → waiting_listing_duration_days →
waiting_stock_count → confirmation
```

#### CC (Add CC)

```
AddCCStates:
waiting_category → waiting_non_vbv → waiting_add_mode →
waiting_cc_type → waiting_name → waiting_price →
waiting_description → waiting_instruction →
waiting_upload_mode → waiting_extra_data → waiting_bulk_lines
```

#### Brute Bank

```
BruteUploadStates:
waiting_upload_mode → waiting_bank_name → waiting_bank_code →
waiting_attributes → 
  ├── single: waiting_balance_range → waiting_account_type →
  │   waiting_credentials → waiting_balance → waiting_price → confirmation
  └── bulk: waiting_bulk_price → waiting_bulk_items → confirmation
```

Группы создаются автоматически (`bank_code` + `attributes` → `group_key`). Новые группы — `is_active=False`, ждут одобрения админа.

#### NFC

```
AddNFCStates:
waiting_type (AP/GP/Other) → waiting_bank_name → waiting_country →
waiting_state → waiting_zip → waiting_price → waiting_file (ZIP)
```

#### OTP

```
AddOTPStates:
waiting_bank_name → waiting_balance → waiting_has_fullz →
waiting_sms_access (seller_mediated / account_access) → waiting_price
```

#### Enroll

```
AddEnrollStates:
[Выбор категории или запрос нового портала]
  ├── Существующая: → state.update_data(enroll_category_id, portal)
  │   → waiting_bank_name → waiting_balance → waiting_zip →
  │     waiting_state_field → waiting_price → waiting_card_type (credit/debit)
  └── Новый портал: waiting_request_name →
      EnrollCategoryRequest (status=pending) → state.clear()
```

#### Checks

```
AddCheckStates:
waiting_check_type (Personal/Business/Payroll/Cashier) →
waiting_bank_name → waiting_amount → waiting_state →
waiting_price → waiting_scan (фото)
```

#### Documents

```
AddDocumentStates:
waiting_doc_type → waiting_state → waiting_quality →
waiting_has_hologram → waiting_has_selfie →
waiting_description → waiting_price → waiting_sample
```

#### Fullz

```
AddFullzStates:
12 состояний: fullz_type → state → credit_score → age → gender →
company_type → loan_size → report_group → quantity →
description → price → data_file
```

#### Universal Upload

```
UploadFSM:
waiting_template → waiting_category → waiting_type →
waiting_data → waiting_price → waiting_preview
```

Поддерживает: CC, Debit, Logs, Selfreg BA, Brute, NFC, Checks (через template/category flow).

---

### 2.5 Mini App — вкладки

| Вкладка | Описание |
|---------|----------|
| **Chats** | Список покупателей, выбор чата, отправка сообщений / файлов (.txt, .pdf, .zip, .csv, .json) |
| **Orders** | Фильтры: Active / All / Done / Disputed. Список заказов селлера |
| **Uploads** | Подвкладки: **Bank** (форма product_type, category, stock, prices), **Brute** (single/bulk + file parse), **Batches** (список загрузок), **Listings** (bulk reprice, сохранённые шаблоны) |
| **Analytics** | Воронка конверсии, топ товары, брошенные корзины |
| **Finance** | Баланс, форма вывода, экспорт CSV |
| **Settings (More)** | Vacation mode, auto-payout, quiet hours, информация об аккаунте |

---

### 2.6 Mini App — API эндпоинты

| Группа | Эндпоинт | Метод | Описание |
|--------|----------|-------|----------|
| Auth | `/api/seller-mini-app/me` | GET | Информация о селлере |
| Chats | `/conversations` | GET | Список чатов |
| | `/messages` | GET | Сообщения чата |
| | `/send` | POST | Отправка сообщения |
| Settings | `/settings/vacation` | POST | Vacation mode toggle |
| | `/settings/auto-payout` | POST | Auto-payout settings |
| | `/settings/quiet-hours` | POST | Quiet hours |
| Analytics | `/analytics/summary` | GET | Общая аналитика |
| | `/analytics/funnel` | GET | Воронка конверсии |
| | `/analytics/abandoned-carts` | GET | Брошенные корзины |
| Finance | `/finance/summary` | GET | Баланс и статистика |
| | `/finance/export.csv` | GET | Экспорт CSV |
| | `/finance/withdraw` | POST | Заявка на вывод |
| Orders | `/orders` | GET | Список заказов |
| Listings | `/listings` | GET | Активные листинги |
| | `/listings/market-comparison` | GET | Сравнение с рынком |
| | `/listings/bulk-price` | POST | Массовое изменение цен |
| Uploads | `/uploads/batches` | GET | Список загрузок |
| | `/uploads/batches/{id}` | GET | Детали загрузки |
| | `/uploads/preview` | POST | Предпросмотр загрузки |
| | `/uploads/parse-file` | POST | Парсинг файла загрузки |
| | `/uploads/submit` | POST | Отправка загрузки (nfc, otp, selfreg_cc и др.) |
| Templates | `/templates` | GET/POST | CRUD шаблонов |
| | `/templates/{id}` | DELETE | Удаление шаблона |

---

## 3. Модератор / Поддержка (support_bot)

### 3.1 Главное меню модератора

```
┌──────────────────────────────────────────┐
│  📋 Moderation Queue                      │
│  📦 Orders Management                     │
│  👤 User Info                             │
│  📊 Statistics                            │
│  📢 Mass Broadcast                        │
│  💰 Manual Balance                        │
│  📁 Files                                 │
│  📤 Upload Products                       │
│  💳 Accounts Management                   │
│  💵 Accountant Panel                      │
│  🎫 Tickets                              │
└──────────────────────────────────────────┘
```

---

### 3.2 Возможности модерации

| Область | Возможности |
|---------|------------|
| **Товары** | Approve / Reject / Request Changes для ВСЕХ типов: Banks, CC, NFC, OTP, Enroll, Selfreg BA, Logs, Selfreg CC, Checks, Documents, Fullz. Наценки: Logs +15%, Checks +15% и т.д. |
| **Селлеры** | `/seller_ban <id> <reason>` — бан + отключение всех листингов. `/seller_leak_ban` — бан + удержание депозита |
| **Диспуты** | Решить в пользу покупателя / продавца, перезапустить окно гарантии, просмотр деталей заказа и истории чата |
| **Жалобы** | Создание (Ban Request, Invalid Data, Abuse, Other). Просмотр через `/my_complaints` |
| **Тикеты** | Ответ / эскалация / закрытие тикетов. SLA по приоритету. CSAT рейтинг. KB-подсказки перед созданием тикета |
| **Аккаунты** | Просмотр инвентаря: категории, товары, stock counts |
| **Загрузка** | Воркеры с `can_load_products`: PROS & FULLZ, Subscriptions/Accounts, eSIM/GV. Админы с `can_upload_catalogs` тоже |
| **Финансы** | Ручная корректировка баланса пользователей, вывод средств воркеров |
| **Broadcast** | Массовая рассылка всем пользователям / селлерам |

**Callback-паттерны модерации:**
- `mod_banks_list` → `mod_bank:{id}` → `mod_bank_approve:{id}` / `mod_bank_reject:{id}` / `mod_bank_changes:{id}`
- Аналогично для: `mod_cc`, `mod_nfc`, `mod_otp`, `mod_enroll`, `mod_selfreg_ba`, `mod_logs`, `mod_selfreg_cc`, `mod_check`, `mod_doc`, `mod_fullz`

---

### 3.3 Поток модерации товара

```
Селлер загружает товар
  ↓
moderation_status = "pending_moderation"
  ↓
Модератор видит в Moderation Queue
  │
  ├── ✅ Approve → moderation_status = "approved"
  │   → товар виден покупателям в каталоге
  │
  ├── ❌ Reject → moderation_status = "rejected"
  │   → селлер видит причину отказа
  │
  └── 📝 Request Changes → moderation_status = "changes_requested"
      → селлер дорабатывает и перезагружает
```

**Фильтрация на стороне покупателя:**
Все каталоги фильтруют:
```python
item.moderation_status == "approved"
item.is_active == True
item.is_in_stock == True
Seller.is_approved == True
Seller.is_active == True
```

---

## 4. Worker Bot

Worker bot — для исполнения заказов (per-order товары):

```
Worker Bot
├── /start → Главное меню
│
├── 📋 Взять заказ → статусы:
│   ├── In Progress
│   ├── Searching Data
│   └── Problem
│
├── ✅ Завершить заказ:
│   ├── DONE + файлы/текст результата
│   └── NF (Not Found)
│
├── 📝 "Add Info" / "Write Client"
│   └── Окна: 24h / 48h / 72h
│
├── 📊 KPI Dashboard:
│   ├── Score
│   ├── Success rate
│   ├── Avg time
│   └── Earnings
│
├── ⚠️ Жалобы на покупателей
│   └── Ban Request / Invalid Data / Abuse / Other
│
├── 📤 Upload Products (если can_load_products)
│   └── PROS & FULLZ, Subscriptions/Accounts, eSIM/GV
│
└── 💸 Вывод баланса
```

**Внутренний API:** `api_server.py` на порту 8181

---

## 5. Структура файлов проекта

### 5.1 seller_bot/

```
seller_bot/
├── bot.py                    # Dispatcher, роутеры, middleware
├── config.py                 # Конфигурация (BOT_TOKEN, ADMIN_IDS, etc.)
├── run.py                    # Точка входа
├── utils.py
├── constants/
│   ├── buttons_en.py, buttons_es.py, buttons_ru.py, buttons_zh.py
│   ├── texts_en.py, texts_es.py, texts_ru.py, texts_zh.py
│   └── language_loader.py
├── handlers/
│   ├── start.py              # /start, /register, язык, правила, депозит
│   ├── stock.py              # Banks/Enrol: add/edit/delete, toggle stock
│   ├── orders.py             # Заказы, complete, dispute
│   ├── chat.py               # Buyer-seller чаты
│   ├── profile.py            # Профиль, vacation, leave
│   ├── upload_fsm.py         # Universal Upload
│   ├── cc_stock.py           # CC items: single/bulk
│   ├── brute_bank.py         # Brute Bank upload
│   ├── special_products.py   # NFC, OTP, Enroll, Selfreg CC, Checks
│   ├── uploads.py            # Upload batches list
│   ├── withdrawal.py         # Вывод средств
│   ├── broadcast.py          # Admin broadcast
│   ├── listings.py           # Listings, bulk repricing
│   ├── bulk_import.py        # CSV/JSON bulk import (banks)
│   ├── documents.py          # Documents upload
│   ├── fullz.py              # Fullz upload
│   └── helpers.py            # Helper roles, invites
├── keyboards/
│   └── inline.py             # Все inline-клавиатуры
├── middlewares/
│   ├── database.py           # DB session middleware
│   ├── language.py           # Language middleware
│   └── seller_auth.py        # Auth + role resolution
└── services/
    ├── stock_service.py
    ├── cc_stock_service.py
    ├── special_stock_service.py
    ├── seller_service.py
    ├── auto_payout_service.py
    └── weekly_report_service.py
```

---

### 5.2 mirror_bot/

```
mirror_bot/
├── bot.py                    # Dispatcher, роутеры
├── config.py
├── run.py
├── constants/
│   ├── buttons_en.py         # ButtonTexts (with_count, BACK, etc.)
│   ├── texts_en.py
│   ├── prices.py             # ServicePrices
│   └── bank_data.py          # BankData (категории, банки, запросы к БД)
├── handlers/
│   ├── start.py              # /start, back_main, язык, правила
│   ├── banks.py              # BANKS каталог (categories → bank_name → items)
│   ├── brute_bank.py         # Brute Bank каталог (groups → variants → buy)
│   ├── cc.py                 # CC каталог (USA/WORLD/NON VBV, BIN/ZIP search)
│   ├── seller_specials.py    # NFC/OTP/Enroll/Logs/Checks/Selfreg каталог + buy
│   ├── accounts.py           # Subscriptions/Accounts
│   ├── fullz.py              # PROS & FULLZ
│   ├── documents.py          # Documents
│   ├── esim.py               # eSIM
│   └── products.py           # My Purchases, Setup Archive
├── keyboards/
│   ├── reply.py              # Main menu reply keyboard (из БД)
│   ├── inline.py             # Profile, topup, payment, language
│   └── cc.py                 # CC keyboards (catalog, detail, buy)
├── states/
│   ├── banks.py              # BankStates
│   ├── cc.py                 # CCFilterStates
│   ├── accounts.py           # AccountStates
│   ├── fullz.py              # FullzStates
│   ├── order.py              # OrderStates
│   └── profile.py            # ProfileStates
├── services/
│   ├── menu_counts_service.py
│   ├── order_service.py
│   ├── user_service.py
│   └── checkout_coupon_service.py
├── utils/
│   ├── catalog_pagination.py # paginated_keyboard(), clamp_page()
│   └── message_utils.py      # safe_edit_message()
└── middlewares/
    ├── database.py
    └── language.py
```

---

### 5.3 support_bot/

```
support_bot/
├── bot.py, run.py, config.py
├── handlers/
│   ├── start.py              # /start, main menu
│   ├── seller_moderation.py  # Approve/reject all product types
│   ├── orders.py, bulk_orders.py, seller_orders.py, work_orders.py
│   ├── complaints.py         # Worker complaints
│   ├── tickets.py            # Support tickets
│   ├── upload_product.py     # Worker product uploads
│   ├── uploader_panel.py     # Upload management
│   ├── accounts.py           # Account inventory
│   ├── accountant_panel.py   # Finance management
│   ├── user_info.py          # User lookup
│   ├── statistics.py         # Analytics
│   ├── manual_balance.py     # Manual balance adjustments
│   ├── mass_broadcast.py     # Broadcasts
│   ├── worker_withdrawal.py  # Worker payouts
│   ├── files.py, esim.py, history.py, profile.py
├── services/
│   ├── moderation_service.py
│   ├── order_service.py
│   └── ...
├── keyboards/inline.py
├── middlewares/
│   ├── worker_auth.py
│   └── database.py
└── constants/
    ├── buttons_accounts.py
    ├── buttons_esim.py
    └── service_names.py
```

---

### 5.4 web_panel/ (Mini App)

```
web_panel/
├── app.py                    # Flask app
├── config.py
├── api/
│   ├── seller_mini_app.py    # Seller Mini App API
│   ├── admin.py              # Admin API
│   └── ...
├── templates/
│   ├── seller_mini_app.html  # Seller Mini App SPA
│   ├── admin/                # Admin panel templates
│   └── ...
└── static/
    ├── css/
    ├── js/
    └── img/
```

---

### 5.5 shared/

```
shared/
├── database/
│   ├── models.py             # Все SQLAlchemy модели
│   └── session.py            # Engine + inline migrations + seeds
├── services/
│   ├── seller_upload_pipeline_service.py  # Upload validation + auto-create groups
│   ├── seller_upload_batch_service.py     # Batch management
│   ├── seller_deposit_service.py          # Deposit + access control
│   ├── seller_conversation_service.py     # Buyer-seller chats
│   ├── guarantee_policy_service.py        # Guarantee windows
│   ├── nocodb_service.py                  # NocoDB logging
│   └── ...
├── utils/
│   ├── seller_product_meta.py      # Badges, labels
│   └── seller_card_renderers.py    # Description renderers for all types
├── cc_catalog.py                   # CC catalog queries (BIN/ZIP/NON VBV)
└── brute_bank_group_key.py         # make_brute_group_key()
```

---

## 6. База данных — ключевые модели

| Модель | Таблица | Назначение |
|--------|---------|-----------|
| `User` | `users` | Покупатели (telegram_id, balance, language) |
| `Seller` | `sellers` | Продавцы (is_approved, is_active, access_status, deposits) |
| `SellerBank` | `seller_banks` | Банковские товары (Available / Per Order) |
| `SellerCCItem` | `seller_cc_items` | CC товары (+`card_bin` String(6), `is_non_vbv` Boolean) |
| `CCCategory` | `cc_categories` | Категории CC (usa, world, **non_vbv**) |
| `BruteBankGroup` | `brute_bank_groups` | Группы brute (+`group_key` unique, `attributes`) |
| `BruteBankItem` | `brute_bank_items` | Товары brute (balance_range, account_type, credentials) |
| `SellerNFCItem` | `seller_nfc_items` | NFC товары (nfc_type: ap/gp/**other**) |
| `SellerOTPItem` | `seller_otp_items` | OTP товары (sms_access_type) |
| `SellerEnrollItem` | `seller_enroll_items` | Enroll товары (+`enroll_category_id`, `bank_name`, `card_zip`, `card_state`, `card_type`) |
| `EnrollCategory` | `enroll_categories` | Предзагруженные порталы (FDECS, DIGITALCARDSERVICE, ...) |
| `EnrollCategoryRequest` | `enroll_category_requests` | Заявки селлеров на новые порталы |
| `SellerLogsItem` | `seller_logs_items` | Logs товары |
| `SellerCheckItem` | `seller_check_items` | Check товары (check_type, scan_photo) |
| `SellerSelfregCCItem` | `seller_selfreg_cc_items` | Selfreg CC товары |
| `SellerSelfregBAItem` | `seller_selfreg_ba_items` | Selfreg BA товары |
| `SellerDocumentItem` | `seller_document_items` | Documents |
| `SellerFullzItem` | `seller_fullz_items` | Fullz |
| `SellerUploadBatch` | `seller_upload_batches` | Батчи загрузок |
| `*Order` | `seller_*_orders` | Заказы для каждого типа товара |

---

## 7. Сводная таблица: кто что видит

| Секция | Покупатель (mirror_bot) | Селлер (seller_bot) | Модератор (support_bot) | Mini App |
|--------|------------------------|--------------------|-----------------------|----------|
| **Banks** | Категории → bank_name → items → buy | Add Bank wizard, My Banks | Approve / Reject / Changes | Bank tab (форма) |
| **CC** | USA / WORLD / NON VBV → BIN/ZIP → buy | Add CC (single/bulk), My CC | Approve / Reject | Нет |
| **Brute** | Группы → варианты → buy | Brute upload (single/bulk) | Approve группы | Brute tab |
| **NFC** | AP / GP / Other → items → buy | Add NFC (тип + файл) | Approve / Reject | API submit |
| **OTP** | Единый список → buy | Add OTP (bank, balance, SMS) | Approve / Reject | API submit |
| **Enroll** | Порталы → items → buy | Add Enroll (портал, bank, zip...) | Approve + одобрение категорий | Нет |
| **Logs** | Список + фильтр цены → buy | Universal Upload | Approve / Reject | Нет |
| **Checks** | Types → items → buy | Add Check (тип, bank, скан) | Approve / Reject | Нет |
| **Documents** | DL/Passport/Biz → state → buy | Add Document | Approve / Reject | Нет |
| **Fullz** | Personal/Biz → фильтры → buy | Add Fullz | Approve / Reject | Нет |
| **Selfreg CC** | Items → buy | Add Selfreg CC | Approve / Reject | API submit |
| **Accounts** | Categories → items → qty → buy | — (worker upload) | Inventory management | Нет |
| **eSIM** | SMS/Data/GV → items → buy | — (worker upload) | Inventory management | Нет |

---

## 8. Pagination & UX — параметры по секциям

| Секция | Items/page | Кнопка товара (формат) | Сортировка | Фильтры |
|--------|-----------|----------------------|-----------|---------|
| Banks subcategories | **15** | `Chase [24]` | — | — |
| Banks items | **10** | `Chase VCC — $45 [3]` | Price ↑↓ | — |
| CC items | **10** | `Chase Visa ***4521 \| $25.00` | Price ↑↓ | BIN, ZIP |
| Brute groups | **8** | `GTE [AN:RN+INST YODLEE] [355]` | — | Search по имени |
| Brute variants | **10** | `$500-$1000 Checking $35 [12]` | Price ↑↓ | — |
| NFC items | **10** | `Chase US \| $120.00` | Price ↑↓ | Тип (AP/GP/Other) |
| OTP items | **10** | `Chase $5,000 \| $85.00 ·seller` | Price ↑↓ | — |
| Enroll categories | **15** | `FDECS [12]` | — | — |
| Enroll items | **12** | `Chase $2,400 \| $45.00` | Price ↑↓ | — |
| Logs items | **10** | `Chase \| $35.00` | Price ↑↓ | Цена: $0-25, $25-50, $50-100, $100+ |
| Checks subcategories | **15** | `Personal [8]` | — | — |
| Checks items | **10** | `Personal Chase $500 CA \| $15.00` | Price ↑↓ | — |

**Общая утилита пагинации:** `mirror_bot/utils/catalog_pagination.py`
```python
def paginated_keyboard(
    items, page, items_per_page,
    item_text_fn, item_callback_fn,
    nav_prefix, back_callback,
    sort_callback=None, current_sort="default",
    extra_top_rows=None, nav_extra=""
) -> InlineKeyboardMarkup
```

---

## 9. Детальные параметры каждого товара: кнопка, карточка, категории

### 9.1 Banks

#### Категории (верхний уровень)
| Код | Название | Эмодзи |
|-----|----------|--------|
| `vcc` | PERSONAL VCC | 💳 |
| `personal` | PERSONAL BANKS | 🏦 |
| `business` | BUSINESS BANKS | 🏢 |
| `crypto` | CRYPTO BANKS | 🪙 |
| `merchant` | MERCHANT ACCOUNTS | 🏪 |
| `logs` | LOGS | 📋 |

#### Подкатегории (bank_name)
Формат кнопки: `{bank_name (до 28 символов)} [{available_count}]`

Пример: `Chase [24]`, `WellsFargo [12]`, `Chime VCC [8]`

#### Кнопка товара в списке
- **Available:** `{name} — ${price} [{available_count}]`
- **Per Order:** `{name} — ${price} [∞]`

Примеры: `🤩 Chime VCC — $35 [8]`, `🏦 Chase — $120 [∞]`

#### Карточка товара (detail)
```
🏛️ {product_name}
📦 Category: {category}
💵 Price: ${price}
🕒 Delivery: {delivery}    (из PRODUCT_DATA или "1-6 Hours")
📝 Description: [{description}]({tutorial_link})

✅ Status: Available
Once payment is confirmed, the goods will be delivered automatically.

Select quantity or buy 1 piece:

✅ In Stock / ❌ Out of Stock
```

---

### 9.2 CC

#### Категории
| Код | Название | Фильтр |
|-----|----------|--------|
| `usa` | 🇺🇸 USA CC | `category_code == "usa"` |
| `world` | 🌍 ALL WORLD CC | `category_code == "world"` |
| `non_vbv` | ⛔ NON VBV | `is_non_vbv == True` (через все категории) |

#### Кнопка товара в списке
Формат: `{bank_name (до 20 символов)} {card_brand (до 16)} ***{last4} | ${buyer_price:.2f}`

Примеры: `Chase Visa ***4521 | $25.00`, `Citi Mastercard ***8834 | $18.50`

Обрезается до 58 символов + `…`

#### Карточка товара (detail)
```
💳 **{item_name}**

Price: ${buyer_price}

💳 {card_brand} {BIN} — {bank_name}
━━━━━━━━━━━━━━━━━━━
BIN: {bin} | Exp: {exp_mm}/{exp_yyyy}
Type: {card_type} {card_level} | NON-VBV: ✅/❌
Country: {flag} {country} | State: {state} | ZIP: {zip}
[Address: {address}, {city}]        ← если есть
[Holder: {fname} {lname}]           ← если есть
[Phone: {phone}]                    ← если есть
[Email: {email}]                    ← если есть
[SSN: {ssn}]                        ← если есть
[DOB: {dob}]                        ← если есть
[Info: {extra.info}]                ← если есть
[Ref: {extra.ref}]                  ← если есть
━━━━━━━━━━━━━━━━━━━
```

Поля из `extra_data` (JSON): `bin`, `card`, `exp`, `cvc`, `type`, `level`, `bank`, `country`, `billing`, `shipping`

---

### 9.3 Brute Bank

#### Группы (верхний уровень)
Формат кнопки: `{bank_name} [{attributes}] [{available_count}]`

Примеры: `GTE [AN:RN+INST YODLEE] [355]`, `Chase [12]`

Если `attributes` пусто — показывается без квадратных скобок атрибутов.

#### Варианты внутри группы
Формат кнопки: `{balance_range} {display_price}$ {account_type} [{quantity}]`

Примеры: `$500-$1000 50$ Checking [12]`, `$1000-$5000 35$ Savings [3]`

Если `balance_range` не задан → `NoRange`. Если `account_type` не задан → `NO TYPE`.

#### Карточка варианта (detail)
```
🔓 *{bank_name}*

📊 *Range:* {balance_range}
🏷 *Type:* {account_type}
💰 *Price:* ${price:.2f}
📦 *Available:* {quantity}
💳 *Your balance:* ${user_balance:.2f}
```

#### Подтверждение покупки
```
⚠️ Confirm purchase?

🏦 {bank_name}
📊 Range: {balance_range}
🏷 Type: {account_type}
💵 ${price:.2f} will be deducted.
🛡 Verify window: 60 minutes
```

#### После покупки
```
✅ *Purchase #{order_id} successful!*

🏦 *Bank:* {bank_name}
📊 *Range:* {balance_range}
🏷 *Type:* {account_type}
💰 *Paid:* ${price:.2f}
💳 *Your balance:* ${new_balance:.2f}

⚠️ Press the button below to open your product.
You will have 60 minutes to verify.
After that, payment is finalized to the seller.
```
Кнопки: `📦 Open Product` | `🏠 Main Menu`

---

### 9.4 NFC

#### Подкатегории
| Кнопка | Код | callback |
|--------|-----|----------|
| 🍎 Apple Pay [n] | `ap` | `seller_specials_nfc:ap:0:price_asc` |
| 🤖 Google Pay [n] | `gp` | `seller_specials_nfc:gp:0:price_asc` |
| 📎 Other [n] | `other` | `seller_specials_nfc:other:0:price_asc` |

#### Кнопка товара в списке
Формат: `{bank_name} {country} | ${price:.2f}`

Примеры: `Chase US | $120.00`, `Citi GB | $95.00`

Обрезается до 64 символов.

#### Карточка товара (detail)
```
📱 NFC

📱 {Apple Pay / Google Pay} — {bank_name}
━━━━━━━━━━━━━━━━━━━
Country: {flag} {country}
State: {state} | ZIP: {zip}
Archive: ✅ / ❌
━━━━━━━━━━━━━━━━━━━

Price: ${price:.2f}
```

**Поля в модели `SellerNFCItem`:** `nfc_type`, `bank_name`, `country`, `state`, `zip`, `seller_price`, `buyer_price`, `data_file_path`

---

### 9.5 OTP

#### Подкатегории
Нет — единый плоский список.

#### Кнопка товара в списке
Формат: `{bank_name} ${balance:,.0f} | ${price:.2f}{sms_hint}`

`sms_hint`:
- ` ·seller` если `sms_access_type == "seller_mediated"`
- ` ·acct` если `sms_access_type == "account_access"`
- пусто если не задано

Примеры: `Chase $5,000 | $85.00 ·seller`, `BankOfAmerica $12,000 | $120.00 ·acct`

Обрезается до 64 символов.

#### Карточка товара (detail)
```
📲 OTP Card

📲 OTP | {bank_name}
━━━━━━━━━━━━━━━━━━━
Balance: ${balance}
Fullz: ✅ / ❌
SMS access: {sms_access_type}
Notes: {description}
━━━━━━━━━━━━━━━━━━━

Price: ${price:.2f}
```

**Поля в модели `SellerOTPItem`:** `bank_name`, `balance`, `has_fullz`, `sms_access_type` (seller_mediated / account_access), `description`, `seller_price`, `buyer_price`

---

### 9.6 Enroll

#### Категории (порталы)
Формат кнопки: `{category_name (до 35 символов)} [{item_count}]`

Примеры: `FDECS [12]`, `DIGITALCARDSERVICE [8]`, `CENTRESUITE (minik) [3]`

Предзагруженные порталы (seed в `enroll_categories`):
| Код | Название |
|-----|----------|
| `fdecs` | FDECS |
| `digitalcardservice` | DIGITALCARDSERVICE |
| `mycardinfo` | MYCARDINFO |
| `card_suite_light` | CARD SUITE LIGHT |
| `cardnav` | CardNav |
| `firefighters` | FIREFIGHTERS |
| `coast_central` | COAST CENTRAL |
| `web_access` | WEB ACCESS |
| `card_suite` | Card Suite |
| `myaccountaccess` | Myaccountaccess |
| `centresuite_minik` | CENTRESUITE (minik) |

#### Кнопка товара в списке
Формат: `{bank_name или portal} ${balance:,.0f} | ${price:.2f}`

Примеры: `Chase $2,400 | $45.00`, `Citi $8,500 | $65.00`

Обрезается до 64 символов.

#### Карточка товара (detail)
```
🏦 Enroll

🔐 Enroll | {portal или bank_name} | ${balance}

📋 SSN: ✅/❌  |  DOB: ✅/❌
🏠 Address: ✅/❌  |  Docs: ✅/❌
🌐 Online Access: ✅/❌

💰 Price: ${price:.2f}

Price: ${price:.2f}
```

**Поля в модели `SellerEnrollItem`:** `enroll_category_id`, `portal`, `bank_name`, `balance`, `card_zip`, `card_state`, `card_type` (credit/debit), `has_ssn`, `has_dob`, `has_address`, `has_docs`, `online_access`, `price`

> **Примечание:** `card_zip`, `card_state`, `card_type` хранятся в модели, но в `render_enroll_description` **не отображаются** на карточке покупателя. Они видны в детальном описании заказа после покупки.

---

### 9.7 Logs

#### Подкатегории
Нет — единый список с фильтрами по цене:

| Кнопка | Фильтр |
|--------|--------|
| All $ | Все товары |
| $0–25 | `price >= 0 AND price <= 25` |
| $25–50 | `price > 25 AND price <= 50` |
| $50–100 | `price > 50 AND price <= 100` |
| $100+ | `price > 100` |

#### Кнопка товара в списке
Формат: `{bank} | ${price:.2f}`

Примеры: `Chase | $35.00`, `WellsFargo | $48.00`

Обрезается до 60 символов.

#### Карточка товара (detail)
```
📋 Logs

📋 {bank} — Bank Log

💰 Total balance: ${total_balance}

🏷 Flags: {CVV | BT | Promo | Zelle | Wire | SafePass}
📧 Email Valid: ✅/❌
🍪 Cookies: ✅/❌  |  Screenshot: ✅/❌

💰 Price: ${price:.2f}

Price: ${price:.2f}
```

**Флаги** (показываются только если `True`):
- `has_cvv` → CVV
- `bt_available` → BT
- `promo_available` → Promo
- `zelle_enroll` → Zelle
- `wire_available` → Wire
- `safepass_unlocked` → SafePass

**Поля в модели `SellerLogsItem`:** `bank`, `total_balance`, `has_cvv`, `bt_available`, `promo_available`, `zelle_enroll`, `wire_available`, `safepass_unlocked`, `email_valid`, `has_cookies`, `has_screenshot`, `price`

---

### 9.8 Checks

#### Подкатегории (check_type)
| Кнопка | Код |
|--------|-----|
| All checks [total] | `all` |
| Personal [n] | `personal` |
| Business [n] | `business` |
| Payroll [n] | `payroll` |
| Cashier [n] | `cashier` |

Неизвестные типы из БД отображаются как `Title Case` (подчёркивания → пробелы).

#### Кнопка товара в списке
Формат: `{item_name или bank_name} | ${price:.2f}`

Примеры: `Chase Personal Check | $15.00`, `WellsFargo | $22.00`

#### Карточка товара (detail)
```
📄 Checks

🖊 {bank_name} {Check_Type} Check
━━━━━━━━━━━━━━━━━━━
Amount: ${amount}
State: {state} | ZIP: {zip}
Holder: ✅/❌ | Address: ✅/❌
Status: {status}
Scan: ✅/❌ | Template: ✅/❌
━━━━━━━━━━━━━━━━━━━

Price: ${price:.2f}
```

**Поля в модели `SellerCheckItem`:** `check_type`, `bank_name`, `amount`, `state`, `zip`, `has_holder_name`, `has_address`, `status`, `scan_file_path`, `template_file_path`, `price`

---

### 9.9 Selfreg CC

#### Подкатегории
Нет — единый список.

#### Кнопка товара
Формат: `{item_name или bank_name} | ${price:.2f}`

#### Карточка товара
Отображается через `render_selfreg_cc_description()` — поля: `bank_name`, `card_name`, `daily_limit`, `monthly_limit`, `state`, `zip`, `email_access`, `phone_access`, `online_access`, `price`

---

### 9.10 Сводная таблица: что показывается в кнопке

| Раздел | Формат кнопки товара | Пример |
|--------|---------------------|--------|
| **Banks subcategory** | `{bank_name} [{count}]` | `Chase [24]` |
| **Banks item** | `{name} — ${price} [{stock}]` | `🤩 Chime VCC — $35 [8]` |
| **CC** | `{bank} {brand} ***{last4} \| ${price}` | `Chase Visa ***4521 \| $25.00` |
| **Brute group** | `{bank_name} [{attrs}] [{count}]` | `GTE [AN:RN] [355]` |
| **Brute variant** | `{range} {price}$ {type} [{qty}]` | `$500-$1000 50$ Checking [12]` |
| **NFC** | `{bank_name} {country} \| ${price}` | `Chase US \| $120.00` |
| **OTP** | `{bank_name} ${balance} \| ${price} {sms}` | `Chase $5,000 \| $85.00 ·seller` |
| **Enroll category** | `{portal_name} [{count}]` | `FDECS [12]` |
| **Enroll item** | `{bank_name} ${balance} \| ${price}` | `Chase $2,400 \| $45.00` |
| **Logs** | `{bank} \| ${price}` | `Chase \| $35.00` |
| **Checks type** | `{type_label} [{count}]` | `Personal [8]` |
| **Checks item** | `{item_name} \| ${price}` | `Chase Personal Check \| $15.00` |
| **Selfreg CC category** | `{cat_name} [{count}]` | `Citi [5]` |
| **Selfreg CC item** | `{bank_name} \| ${price}` | `Citi \| $40.00` |

---

## 10. Полный справочник: параметры всех товаров

### 10.1 Banks (VCC / Personal / Business / Crypto / Merchant)

**Категории:** VCC, Personal, Business, Crypto, Merchant, Logs  
**Подкатегории (Available):** группировка по `bank_name` — `{bank_name} [{count}]` (15 шт/стр)  
**Per Order:** плоский список, без подкатегорий

**Кнопка в списке:**
```
{bank_name} [{product_type} / {product_subtype}] — ${price} [{count}]
```
Пример: `Chime VCC [Bank / Log] — $50 [3]`

**Карточка описания (после клика):**
- Product Name
- Category
- Price
- Delivery (1-6 hours)
- Description (со ссылкой на tutorial)
- Status: Available / Out of Stock

**Что задаёт Seller:**

| Поле | Как задаёт | Обязательно |
|------|-----------|-------------|
| `product_type` | Выбор: Bank / Enrol | ✅ |
| `product_subtype` | Выбор: Log / Selfreg | ✅ |
| `category` | Выбор: vcc/personal/business/crypto/merchant | ✅ |
| `bank_name` | Из каталога или свободный текст | ✅ |
| `bank_code` | Из каталога или авто | ✅ |
| `seller_price` | Число (USD) | ✅ |
| `description` | Текст или `-` | ❌ |
| `instruction` | Текст или `-` | ❌ |
| `has_chat` | chat / nochat | ✅ |
| `number_access_available` | Yes / No | ✅ |
| `stock_count` | 0-1000 | ✅ |

Доп. поля для `enrol`:
- `portal`, `card_type`, `state`, `zip`, `has_ssn`, `has_dob`, `has_name`, `has_address`, `has_email`, `has_security_qa`, `has_docs`, `doc_type`, `phone_area_code`

Доп. поля для `selfreg`:
- `state`, `zip`, `has_ssn`, `has_docs`, `doc_type`

Доп. поля для `log`:
- `details_text` (многострочный)

---

### 10.2 CC (Credit Cards)

**Категории:** USA CC, ALL WORLD CC, NON VBV  
**Фильтры:** поиск по BIN, поиск по ZIP, сортировка по цене  
**Пагинация:** 10 шт/стр

**Кнопка в списке:**
```
{bank_name} {card_brand} ***{last4} | ${buyer_price}
```
Пример: `Chase VISA ***4521 | $25.00`

**Карточка описания:**
```
💳 {card_brand} BIN:{bin} {bank_name}
━━━━━━━━━━━━━━━━━━━
BIN: {bin} | EXP: {mm/yyyy}
Type: {card_type} | Level: {card_level}
NON VBV: ✅/❌
Country: {country} | State: {state} | ZIP: {zip}
Address: {address}, {city}
Holder: {fname} {lname}
Phone: {phone} | Email: {email}
SSN: {ssn} | DOB: {dob}
Info: {info} | Ref: {ref}
```

**Что задаёт Seller:**

| Поле | Как задаёт | Обязательно |
|------|-----------|-------------|
| `category_code` | Выбор: usa / world | ✅ |
| `is_non_vbv` | Yes / No | ✅ |
| `item_name` | Текст или из каталога | ✅ |
| `seller_price` | Число (USD) | ✅ |
| `description` | Текст или `-` | ❌ |
| `instruction` | Текст или `-` | ❌ |
| Карточные данные (single/bulk) | Формат строки: | ✅ |

**Формат строки CC:**
```
NUMBER|EXP|CVV|TYPE|BRAND|LVL|BANK|COUNTRY|HOLDER|ADDR|STATE|CITY|ZIP|Info|REF|PRICE
```
- `EXP`: `10/26` или `10/2026`
- Поля после CVV опциональны
- `PRICE` в конце строки перезаписывает цену batch

---

### 10.3 Brute Bank

**Категории:** нет (один плоский список групп)  
**Пагинация групп:** 12 шт/стр, поиск по банку, сортировка A→Z / Z→A  
**Пагинация вариантов:** нет (все варианты на одной странице)

**Кнопка группы:**
```
{bank_name} [{attributes}] [{available_count}]
```
Пример: `Chase Bank [AN:RN+INST YODLEE] [5]`

**Кнопка варианта:**
```
{balance_range} {price}$ {account_type} [{quantity}]
```
Пример: `9-12k 25$ CHECKING [3]`

**Карточка варианта (перед покупкой):**
```
🔓 {bank_name}
📊 Range: {balance_range}
🏷 Type: {account_type}
💰 Price: ${price}
📦 Available: {quantity}
💳 Your balance: ${balance}
```

**После покупки (Reveal):**
```
🔐 Brute Bank Order #{id} — {bank_name}
⏱ 60 минут на проверку
🔑 Credentials:
  {key}: {value}
  ...
```

**Что задаёт Seller (single):**

| Поле | Как задаёт | Обязательно |
|------|-----------|-------------|
| `bank_name` | Свободный текст | ✅ |
| `bank_code` | Текст (lowercase, a-z0-9_) | ✅ |
| `attributes` | Текст или `-` для пропуска | ❌ |
| `balance_range` | Текст (e.g. `9-12k`) | ✅ |
| `account_type` | Выбор: CHECKING/SAVINGS/BUSINESS/MONEY MARKET | ✅ |
| `credentials` | Формат `key: value` построчно | ✅ |
| `balance_info` | Текст или `/skip` | ❌ |
| `price` | Число (USD) | ✅ |

**Bulk формат:**
```
BANK|LOGIN|PASS|ACCOUNT_NUMBER|ROUTING|BALANCE|STATE|NAME|ADDRESS
```

---

### 10.4 Selfreg CC

**Категории:** предзагруженные (Citi, Chase, Wells Fargo, ONEPAY, BOA) — 8 шт/стр  
**Подкатегории:** нет — внутри категории все товары в кучу  
**Пагинация товаров:** 15 шт/стр, сортировка по цене

**Кнопка категории:**
```
{category_name} [{count}]
```
Пример: `Chase [12]`

**Кнопка товара:**
```
{bank_name} | ${buyer_price}
```
Пример: `Chase | $40.00`

**Карточка описания:**
```
💳 {bank_name} — {card_name}
━━━━━━━━━━━━━━━━━━━
Credit Limit: ${credit_limit}
VCC Limit: ${vcc_limit} | State: {state} | ZIP: {zip}
Email: ✅/❌ | Phone: ✅/❌ | Online Access: ✅/❌
━━━━━━━━━━━━━━━━━━━
```

**Что задаёт Seller:**

| Поле | Как задаёт | Обязательно |
|------|-----------|-------------|
| Категория | Выбор из списка SelfregCCCategory + запрос новой | ✅ |
| `card_name` | Свободный текст | ✅ |
| `credit_limit` | Число или `-` | ❌ |
| `vcc_limit` | Число или `-` | ❌ |
| `state` | Текст | ✅ |
| `zip` | Текст | ✅ |
| `has_email` | Yes / No | ✅ |
| `has_phone` | Yes / No | ✅ |
| `phone_days_remaining` | Число (если has_phone) | Условно |
| `phone_renewable` | Yes / No (если has_phone) | Условно |
| `phone_change_allowed` | Yes / No (если has_phone) | Условно |
| `online_access` | Yes / No | ✅ |
| `seller_price` | Число (USD) | ✅ |

Seller может запросить новую категорию → модерация 1-6 часов → `SelfregCCCategoryRequest`.

---

### 10.5 NFC

**Категории:** Apple Pay, Google Pay, Other  
**Пагинация:** 10 шт/стр, сортировка по цене

**Кнопка типа:**
```
🍎 Apple Pay [{count}]
🤖 Google Pay [{count}]
📎 Other [{count}]
```

**Кнопка товара:**
```
{bank_name} {country} | ${price}
```
Пример: `Chase US | $120.00`

**Карточка описания:**
```
📱 Apple Pay — {bank_name}
━━━━━━━━━━━━━━━━━━━
Country: 🇺🇸 {country}
State: {state} | ZIP: {zip}
Archive: ✅/❌
━━━━━━━━━━━━━━━━━━━
```

**Что задаёт Seller:**

| Поле | Как задаёт | Обязательно |
|------|-----------|-------------|
| `nfc_type` | Выбор: Apple Pay / Google Pay / Other | ✅ |
| `bank_name` | Свободный текст | ✅ |
| `country` | Код страны (US, UK...) | ✅ |
| `state` | Текст или `-` | ❌ |
| `zip` | Текст или `-` | ❌ |
| `seller_price` | Число (USD) | ✅ |
| Файл (.txt/.zip) | Загрузка | ✅ |

---

### 10.6 OTP

**Категории:** нет — все в одном списке  
**Пагинация:** 10 шт/стр, сортировка по цене

**Кнопка товара:**
```
{bank_name} ${balance} | ${price} {sms_hint}
```
- `sms_hint`: `·seller` (Via Me) или `·acct` (Direct Account Access)
- Пример: `Chase $5,000 | $85.00 ·seller`

**Карточка описания:**
```
📲 OTP | {bank_name}
━━━━━━━━━━━━━━━━━━━
Balance: ${balance}
Fullz: ✅/❌
SMS access: {sms_access_type}
Notes: {description}
━━━━━━━━━━━━━━━━━━━
```

**Что задаёт Seller:**

| Поле | Как задаёт | Обязательно |
|------|-----------|-------------|
| `bank_name` | Свободный текст | ✅ |
| `balance` | Число (USD) | ✅ |
| `has_fullz` | Yes / No | ✅ |
| `sms_access_type` | Выбор: Via Me (seller_mediated) / Direct Account Access | ✅ |
| `seller_price` | Число (USD) | ✅ |

---

### 10.7 Enroll

**Категории:** предзагруженные порталы (FDECS, DIGITALCARDSERVICE, MYCARDINFO, CARD SUITE LIGHT, CardNav, FIREFIGHTERS, COAST CENTRAL, WEB ACCESS, Card Suite, Myaccountaccess, CENTRESUITE (minik))  
**Пагинация:** 12 шт/стр, сортировка по цене

**Кнопка категории:**
```
{portal_name} [{count}]
```
Пример: `FDECS [12]`

**Кнопка товара:**
```
{bank_name or portal} ${balance} | ${price}
```
Пример: `Chase $2,400 | $45.00`

**Карточка описания:**
```
🔐 Enroll | {portal} | ${balance}

📋 SSN: yes/no | DOB: yes/no
🏠 Address: yes/no | Docs: yes/no
🌐 Online Access: yes/no

💰 Price: ${price}
```

**Что задаёт Seller:**

| Поле | Как задаёт | Обязательно |
|------|-----------|-------------|
| Категория (portal) | Выбор из EnrollCategory + запрос новой | ✅ |
| `bank_name` | Свободный текст | ✅ |
| `balance` | Число (USD) | ✅ |
| `card_zip` | Текст | ✅ |
| `card_state` | 2-буквенный код штата | ✅ |
| `card_type` | Выбор: Credit / Debit | ✅ |
| `seller_price` | Число (USD) | ✅ |

Seller может запросить новую категорию → модерация 1-6 часов.

---

### 10.8 Logs

**Категории:** нет — все в одном списке  
**Фильтры по цене:** All / $0-25 / $25-50 / $50-100 / $100+  
**Пагинация:** 10 шт/стр, сортировка по цене

**Кнопка товара:**
```
{bank} | ${price}
```
Пример: `Chase | $35.00`

**Карточка описания:**
```
📋 {bank} — Bank Log
━━━━━━━━━━━━━━━━━━━
💰 Total balance: ${total_balance}

🏷 Flags: CVV | BT | Promo | Zelle | Wire | SafePass (только если true)
📧 Email Valid: ✅/❌
🍪 Cookies: ✅/❌ | Screenshot: ✅/❌

━━━━━━━━━━━━━━━━━━━
💰 Price: ${price}
```

**Что задаёт Seller:**
Загружается через Universal Upload в seller_bot.  
Формат строки: `SITE|LOGIN|PASS|COOKIES|BALANCE|STATE|ROUTING|NAME|...`

---

### 10.9 Checks

**Категории:** Personal, Business, Payroll, Cashier  
**Пагинация:** 10 шт/стр, сортировка по цене

**Кнопка типа:**
```
{type_label} [{count}]
```
Пример: `Personal [8]`

**Кнопка товара:**
```
{item_name} | ${price}
```

**Карточка описания:**
```
🖊 {bank_name} {check_type} Check
━━━━━━━━━━━━━━━━━━━
Amount: ${amount}
State: {state} | ZIP: {zip}
Holder: ✅/❌ | Address: ✅/❌
Status: {status}
Scan: yes/no | Template: yes/no
━━━━━━━━━━━━━━━━━━━
```

**Что задаёт Seller:**

| Поле | Как задаёт | Обязательно |
|------|-----------|-------------|
| `check_type` | Выбор: Personal/Business/Payroll/Cashier | ✅ |
| `bank_name` | Свободный текст | ✅ |
| `amount` | Число (USD) | ✅ |
| `state` | 2-буквенный код штата | ✅ |
| `seller_price` | Число (USD) | ✅ |
| Скан файл | Загрузка изображения/документа | ✅ |

---

### 10.10 Selfreg BA

**Категории:** нет — в общем списке specials  
**Пагинация:** через generic list (до 30 шт)

**Кнопка товара:**
```
{item_name or bank_name} | ${price}
```

**Карточка описания:**
```
🏦 {bank} Bank — Selfreg Account
━━━━━━━━━━━━━━━━━━━
Balance: ${balance} | State: {state} | ZIP: {zip}
━━━━━━━━━━━━━━━━━━━

📱 Phone: ✅ Active — {phone_days_remaining} days left / ❌
📧 Email: ✅/❌
SSN: ✅/❌ | Docs: ✅/❌

━━━━━━━━━━━━━━━━━━━
💰 Price: ${price}
```

**Что задаёт Seller:**
Загружается через Universal Upload.  
Формат: `BANK|LOGIN|PASS|ACCOUNT_NUMBER|ROUTING|BALANCE|STATE|NAME|ADDRESS|ZIP|...`

---

### 10.11 Documents (только админка)

**Категории:** DL Front&Back, DL+Selfie, DL+KYC Video, Passport, Business Docs  
**Фильтр:** по штату

**Кнопка товара:**
```
{emoji} {product_name} - ${price}
```
- emoji: 📄 txt, 📋 pdf, 📦 zip, 🖼️ jpg/png

**Карточка:**
```
🛍️ {product_name}
{description}
Price: ${price}
Category: {service_display}
State: {state}
{emoji} File type: {file_type}
```

**Загрузка:** только через worker_bot/admin (модель Product). Seller НЕ загружает.

---

### 10.12 Fullz (только админка + воркеры)

**Категории Personal:** 700+ CS, 800+ CS, Under 18, Immigrant, Zero Bank, Random, Custom  
**Категории Business:** by Company Type → Loan Size → Credit Score

**Кнопка в каталоге (фиксированные профили):**
```
{label} — ${price}
```
Пример: `700+ CS — $45`

**Фильтры:** штат, credit score, age, gender, carrier exclusion, bank exclusion, report group

**Загрузка:** только worker/admin через support_bot → модель Product (category=`pros_fullz`).  
Seller НЕ загружает (кнопки убраны из seller_bot).

---

### 10.13 Сводная таблица: кто загружает

| Товар | Seller bot | Worker/Admin | Mini App |
|-------|-----------|-------------|----------|
| Banks | ✅ | ❌ | ✅ |
| CC | ✅ | ❌ | ✅ |
| Brute Bank | ✅ | ❌ | ✅ |
| Selfreg CC | ✅ (по категориям) | ❌ | ✅ |
| NFC | ✅ | ❌ | ❌ |
| OTP | ✅ | ❌ | ❌ |
| Enroll | ✅ (по категориям) | ❌ | ❌ |
| Logs | ✅ (Universal Upload) | ❌ | ❌ |
| Checks | ✅ | ❌ | ❌ |
| Selfreg BA | ✅ (Universal Upload) | ❌ | ❌ |
| Documents | ❌ | ✅ | ❌ |
| Fullz | ❌ | ✅ | ❌ |

---

## 11. Lookup API — Self-Hosted SSN/DL/CR Search

### 11.1 Обзор

Lookup API — это self-hosted сервис для поиска SSN, Driver License и Credit Reports, полностью совместимый с интерфейсом usfull.info. Позволяет использовать собственную базу данных вместо внешнего платного API.

**Архитектура:**

```
┌─────────────┐
│ Mirror Bot  │──┐
└─────────────┘  │
                 │  HTTP (X-API-KEY)
┌─────────────┐  │
│ Worker Bot  │──┼──► ┌──────────────┐      ┌──────────────┐
└─────────────┘  │    │ Lookup API   │─────►│  SQLite DB   │
                 │    │ (port 8082)  │      │ (lookup.db)  │
┌─────────────┐  │    └──────────────┘      └──────────────┘
│ Support Bot │──┘
└─────────────┘
```

### 11.2 Основные компоненты

**Файлы:**
- `lookup_api/app.py` — FastAPI сервер с эндпоинтами
- `lookup_api/importer.py` — импорт данных из CSV
- `lookup_api/manage_keys.py` — управление API ключами
- `lookup_api/Dockerfile` — Docker образ
- `data/lookup.db` — SQLite база данных

**Таблицы БД:**
- `api_keys` — API ключи и балансы пользователей
- `billing_log` — история биллинга
- `persons` — SSN записи (firstname, lastname, ssn, dob, address, city, st, zip, phone)
- `persons_fts` — FTS5 индекс для быстрого поиска
- `licenses` — Driver License записи
- `cr_records` — Credit Report записи

### 11.3 API Endpoints

| Метод | Endpoint | Описание | Auth |
|-------|----------|----------|------|
| POST | `/api/create_token/` | Создать API ключ | username/password |
| GET | `/api/get_balance/` | Проверить баланс | X-API-KEY |
| POST | `/api/search/` | SSN/DOB поиск | X-API-KEY |
| POST | `/api/dl/` | Driver License поиск | X-API-KEY |
| POST | `/api/cr/` | Credit Report поиск | X-API-KEY |
| GET | `/api/cr/download/{id}` | Скачать CR PDF | X-API-KEY |
| GET | `/health` | Health check | - |
| POST | `/api/admin/add_balance` | Пополнить баланс | X-Admin-Token |
| GET | `/api/admin/users` | Список пользователей | X-Admin-Token |
| GET | `/api/admin/stats` | Статистика | X-Admin-Token |

### 11.4 Интеграция с ботами

Боты используют `UsfullClient` из `mirror_bot/services/usfull_service.py`, который автоматически определяет backend по переменной окружения `LOOKUP_API_BASE_URL`:

```python
# В .env
LOOKUP_API_BASE_URL=http://lookup_api:8082  # self-hosted
# или
LOOKUP_API_BASE_URL=https://usfull.pro      # внешний API
```

**Поток данных:**

1. Пользователь отправляет данные в бот (имя, адрес, DOB)
2. Бот парсит в `SSNLookupData` / `DLLookupData`
3. `ssn_dl_automation.py` загружает `UsfullClient` из таблицы `api_keys`
4. `UsfullClient` отправляет HTTP запрос в Lookup API
5. Lookup API ищет в SQLite через FTS5 индекс
6. Результаты возвращаются боту
7. Бот форматирует и отправляет пользователю

**Автоматическая загрузка ключа:**

```python
from mirror_bot.services.ssn_dl_automation import _load_usfull_client

async with get_session() as session:
    client = await _load_usfull_client(session)
    if client:
        result = await client.search_ssn(
            firstname="JOHN",
            lastname="DOE",
            st="NY"
        )
```

### 11.5 Биллинг

Каждый запрос автоматически списывает средства с баланса:

| Операция | Найдено | Не найдено |
|----------|---------|------------|
| SSN | $0.40 | $0.01 |
| DL | $1.00 | $0.00 |
| CR | $0.40 | $0.01 |

История биллинга сохраняется в таблице `billing_log`.

### 11.6 Управление API ключами

**Через manage_keys.py:**

```bash
# Создать ключ
LOOKUP_DB_PATH=../data/lookup.db python3 manage_keys.py create bot_user password --balance 1000

# Список ключей
LOOKUP_DB_PATH=../data/lookup.db python3 manage_keys.py list

# Пополнить баланс
LOOKUP_DB_PATH=../data/lookup.db python3 manage_keys.py add-balance bot_user 500
```

### 11.7 Импорт данных

**Формат CSV для SSN:**

```csv
firstname,lastname,middlename,ssn,dob,address,city,st,zip,phone,name_suff
JOHN,DOE,M,123456789,19900115,123 MAIN ST,NEW YORK,NY,10001,2125551234,
```

**Импорт:**

```bash
python3 importer.py persons data.csv --db ../data/lookup.db
python3 importer.py rebuild-fts --db ../data/lookup.db
```

### 11.8 Производительность

- **FTS5 индекс** для быстрого полнотекстового поиска по имени/адресу
- **B-tree индексы** для SSN, DOB, ZIP, State
- **WAL режим** для параллельных чтений
- **Batch импорт** (5000 записей за раз)
- **Типичное время ответа:** <50ms на запрос

### 11.9 Документация

Полная документация в `lookup_api/`:

- **README.md** — быстрый старт
- **SETUP_GUIDE.md** — полное руководство по настройке
- **INTEGRATION_GUIDE.md** — интеграция с ботами
- **CHEATSHEET.md** — шпаргалка с командами
- **STATUS.md** — текущий статус и тестовые данные
- **SUMMARY.md** — итоговый отчёт

### 11.10 Docker Compose

Lookup API настроен в `docker-compose.yml`:

```yaml
lookup_api:
  build:
    context: ./lookup_api
    dockerfile: Dockerfile
  container_name: newlookup_lookup_api
  environment:
    - LOOKUP_DB_PATH=/app/data/lookup.db
    - LOOKUP_API_PORT=8082
    - LOOKUP_ADMIN_TOKEN=${LOOKUP_ADMIN_TOKEN}
  expose:
    - "8082"
  volumes:
    - ./data:/app/data
  networks:
    - bot_network
  restart: unless-stopped
```

**Запуск:**

```bash
# Только Lookup API
docker compose up lookup_api -d

# Весь стек
docker compose up -d
```

---

**Конец документа.**
