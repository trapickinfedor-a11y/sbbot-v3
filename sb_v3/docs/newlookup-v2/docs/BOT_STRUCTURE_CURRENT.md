# Текущая структура Mirror Bot

## 1. Главное меню (Reply Keyboard)

**Файл:** `mirror_bot/keyboards/reply.py` → `main_menu_keyboard()`

```
Ряд 1: [👤 My profile]     [💳 Top-up balance]
Ряд 2: [🔎 Search]          [📈 CREDIT REPORTS]
Ряд 3: [📄 DOCUMENTS]      [🧰 PROS & FULLZ]
Ряд 4: [🏦 BANKS]          [🧾 Subscriptions / Accounts]
Ряд 5: [📶 eSIM]           [✍️ Add info in CR]
Ряд 6: [📞 Support]        [🤝 Referrals +4%]
Ряд 7: [📞 CALL SERVICE]
```

**Порядок кнопок (сверху вниз):**
1. Профиль, Пополнение
2. Search, Credit Reports
3. Documents, Fullz
4. Banks, Accounts
5. eSIM, Add Info
6. Support, Referrals
7. Call Service

---

## 2. Логика каждого раздела

### 2.1 🔎 Search (Lookup)

**Вход:** `F.text.in_(["🔎 Search", "🔎 Поиск", "🔎 搜索"])`  
**Handler:** `mirror_bot/handlers/lookup/main.py`

**Поток:**
```
Search (main) → lookup_keyboard
    ├── SSN & DOB, Credit Score
    ├── DL, MVR, Full MVR
    ├── Phone Search → phone_search_keyboard (Name, DOB+SSN, Full)
    ├── BG, MMN, EIN
    └── Back → main menu
```

**Особенности:**
- Каждый сервис: Single / Bulk Order
- Ввод данных (SSN, DL, phone и т.д.) → OrderStates.waiting_data
- Цены из ServicePrices, bulk из BulkDiscounts

---

### 2.2 📈 CREDIT REPORTS

**Вход:** `F.text.in_(["📈 CREDIT REPORTS", ...])`  
**Handler:** `mirror_bot/handlers/credit_reports.py`

**Поток:**
```
Credit Reports → credit_reports_keyboard
    ├── TransUnion, Experian, Equifax
    ├── LexisNexis, WalletHub
    └── Back → main menu
```

**Особенности:**
- Прямой выбор сервиса → ввод данных → заказ
- OrderStates.waiting_data

---

### 2.3 📄 DOCUMENTS

**Вход:** `F.text.in_(["📄 DOCUMENTS", ...])`  
**Handler:** `mirror_bot/handlers/documents.py`

**Поток:**
```
Documents → documents_main_keyboard
    ├── Photo → photo_catalog_keyboard
    │   ├── DL (Front & Back)
    │   ├── DL + Selfie
    │   ├── Passport
    │   └── Business Docs
    ├── High-Quality Drawing (SOON)
    ├── Robot Drawing (SOON)
    └── Back → main menu
```

**Для каждого типа документа:**
```
doc_photo_dl → выбор штата (4 страницы) → Product/Order
doc_photo_dl_selfie → ...
doc_photo_passport → ...
doc_photo_biz → ...
```

**Особенности:**
- Documents = файловые товары (Product) или заказы воркерам (Order)
- Штаты из STATES_PAGES (4 страницы по ~12 штатов)
- ProductService для docs, pros_fullz

---

### 2.4 🧰 PROS & FULLZ

**Вход:** `F.text.in_(["🧰 PROS & FULLZ", ...])`  
**Handler:** `mirror_bot/handlers/fullz.py`

**Поток:**
```
Fullz → fullz_personal / fullz_business
    ├── PERSONAL → fullz_prof (CUSTOM CS/CR, Military, Work&Travel, Young, Random)
    │   └── выбор штата (4 стр) → fullz_company / fullz_cs / fullz_loan / fullz_age / fullz_gender / fullz_report
    │       └── количество → подтверждение → заказ
    └── BUSINESS → fullz_prof (аналогично) + LLC/CORP
```

**Особенности:**
- Сложный FSM: profile → state → company/cs/loan/age/gender/report → qty → confirm
- Random fullz: ANY STATE, без выбора штата
- Bulk скидки из BulkDiscounts

---

### 2.5 🏦 BANKS

**Вход:** `F.text.in_(["🏦 BANKS", "🏦 БАНКИ", "🏦 银行"])`  
**Handler:** `mirror_bot/handlers/banks.py`

**Поток:**
```
Banks → banks_main_keyboard
    ├── 💳 PERSONAL VCC (banks_vcc)
    ├── 🏦 PERSONAL BANKS (banks_personal)
    ├── 🏢 BUSINESS BANKS (banks_business)
    ├── 🪙 CRYPTO BANKS (banks_crypto)
    ├── 🔓 Brute BANK (SOON) → lookup_support:banks_main (инфо + Back)
    └── Back → main menu
```

**Для каждой категории (vcc, personal, business, crypto):**
```
banks_{cat} → banks_catalog_keyboard (список из BankItem/BankData)
    └── bank_item:{id} → описание + bank_item_keyboard
        ├── 2, 3, 5, 10 шт (скидки)
        ├── Custom Quantity
        ├── Buy 1
        └── Back to List
```

**Логика покупки:**
- **In Stock:** bank_buy → SellerOrder (pending_admin) → уведомление админу
- **Out of Stock:** bank_qty → Order (воркерам) или bank_oos_alert

**Особенности:**
- BankData.CATEGORIES: vcc, personal, business, crypto
- BankItem из БД или fallback на bank_data.py
- BRUTE_BANK_SOON ведёт на lookup_support (текст LOOKUP_SUPPORT_BANKS), Back → banks_main

---

### 2.6 🧾 Subscriptions / Accounts

**Вход:** `F.text.in_(["🧾 Subscriptions / Accounts", ...])`  
**Handler:** `mirror_bot/handlers/accounts.py`

**Поток:**
```
Accounts → accounts_main_keyboard (динамические категории из БД)
    ├── <Категория 1> (acc_cat:<code>)
    ├── <Категория 2> (acc_cat:<code>)
    ├── ...
    └── Back → main menu
```

**acc_cat:<code> → Каталог категории:**
```
→ accounts_catalog_keyboard (из AccountCategory / AccountItem, пагинация по 5)
→ acc_item:{id} → количество (1,2,3,5,10, custom) → подтверждение → заказ
```

**Особенности:**
- Категории и товары из БД (AccountCategory, AccountItem), управляются через web_panel
- Цены из AccountItem.price + BulkDiscounts
- Instant delivery из AccountInventory (полная + частичная)
- При частичной доставке — остаток передаётся воркеру
- Пагинация (ITEMS_PER_PAGE = 5)
- CRUD + drag-and-drop порядок в web_panel

---

### 2.7 📶 eSIM

**Вход:** `F.text == "📶 eSIM"`  
**Handler:** `mirror_bot/handlers/esim.py`

**Поток:**
```
eSIM → esim_main_keyboard
    ├── eSIM for SMS → операторы (Verizon, AT&T, T-Mobile)
    │   └── период (1/3/6 мес) → количество → заказ
    └── eSIM for Data → операторы
        └── объём (5/10/15 GB) → количество → заказ
```

**Особенности:**
- ESIMStates для FSM
- Цены: OPERATOR_PRICES, DATA_PRICES
- service_name: sms_verizon, data_att и т.д.

---

### 2.8 ✍️ Add info in CR

**Вход:** `F.text.in_(["✍️ Add info in CR", ...])`  
**Handler:** `mirror_bot/handlers/addinfo.py`

**Поток:**
```
Add Info → addinfo_main_keyboard
    ├── Add Info in CR (addinfo_addcr)
    ├── Add Info in BG (addinfo_addbg)
    ├── Add Employer (addinfo_employer)
    ├── Unfreeze CR (addinfo_unfreeze)
    └── Back → main menu
```

**Для каждой подкатегории:**
```
→ addinfo_catalog_keyboard (из AddInfoData)
→ addinfo_item:{id} → addinfo_buy → ввод данных → confirm → заказ
```

**Особенности:**
- AddInfoData: addcr_*, addbg_*, addemp_*, unfreeze_*
- Некоторые требуют wait_time_hours (24, 48)

---

### 2.9 📞 Support

**Вход:** кнопка Support  
**Handler:** `mirror_bot/handlers/support.py`

**Поток:**
```
Support → support_categories_keyboard
    ├── Payment, Product, General, Partnership
    ├── My tickets
    └── Back → main menu
```

**Тикеты:** SupportTicket, SupportMessage

---

### 2.10 Прочие (Profile, Top-up, Rules, Referrals, Call Service)

- **Profile:** MY_PROFILE → profile_keyboard (Bank Orders, Send money, Referrals, Rules, Language)
- **Top-up:** PAY_VIA_CRYPTOBOT / CRYPTOMUS → сумма → оплата
- **Rules:** Service rules, Call service, Referrals — отдельные handlers в rules.py

---

## 3. Banks — текущий порядок подкатегорий

**Файл:** `mirror_bot/keyboards/inline.py` → `banks_main_keyboard()`

| # | Кнопка | callback_data | Логика |
|---|--------|---------------|--------|
| 1 | 💳 PERSONAL VCC | banks_vcc | Каталог VCC банков |
| 2 | 🏦 PERSONAL BANKS | banks_personal | Каталог Personal |
| 3 | 🏢 BUSINESS BANKS | banks_business | Каталог Business |
| 4 | 🪙 CRYPTO BANKS | banks_crypto | Каталог Crypto |
| 5 | 🔓 Brute BANK (SOON) | lookup_support:banks_main | Инфо, Back в Banks |
| 6 | ⬅️ Back | back_main | Главное меню |

**BRUTE_BANK_SOON:** не ведёт в каталог, а показывает текст LOOKUP_SUPPORT_BANKS (Bank Brute Force Integration, Bank Logins Brute Force, Card Brute Force) и кнопку Back.

---

## 4. Маппинг категорий (Order.category)

| Раздел | Order.category | Примеры service_name |
|--------|----------------|---------------------|
| Search | lookup, credit | ssn_dob, lookup_dl, cr_transunion |
| Documents | documents | doc_dl, doc_passport |
| Fullz | fullz | fullz_personal, fullz_military |
| Banks | banks | vcc_chime, pers_chase, biz_quickbooks |
| Accounts | accounts | bg_beenverified, lookup_monarch |
| eSIM | esim | sms_verizon, data_att |
| Add Info | addinfo | addcr_all, addemp_tu |

---

## 5. Файлы для изменения порядка/логики

| Что менять | Файл |
|------------|------|
| Порядок главного меню | `mirror_bot/keyboards/reply.py` |
| Порядок Banks подкатегорий | `mirror_bot/keyboards/inline.py` → banks_main_keyboard |
| Обработка banks_brute | `mirror_bot/handlers/banks.py` |
| Данные банков | `mirror_bot/constants/bank_data.py` |
| Тексты кнопок | `mirror_bot/constants/buttons_*.py` |
| reorder category mapping | `mirror_bot/handlers/start.py` → reorder_handler |
| reorder category mapping | `mirror_bot/keyboards/inline.py` → reorder_keyboard |

---

## 6. Диаграмма навигации Banks

```
                    ┌─────────────────┐
                    │   🏦 BANKS      │
                    │   (main menu)   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │ banks_vcc   │ │banks_personal│ │banks_business│
    │ (VCC)       │ │ (Personal)  │ │ (Business)  │
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           │               │               │
           └───────────────┼───────────────┘
                           ▼
                  ┌─────────────────┐
                  │ banks_crypto    │
                  │ (Crypto)        │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ BRUTE_BANK_SOON │
                  │ → lookup_support │
                  │   (инфо, не каталог)│
                  └─────────────────┘
```
