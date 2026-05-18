# Полная структура меню бота

Редактируй этот файл — порядок строк = порядок кнопок. После изменений скажи — внесём в код.

---

## 1. Главная клавиатура (Reply Keyboard)

**Файл:** `mirror_bot/keyboards/reply.py` → `main_menu_keyboard()`

### Ряд 0
- [ ] education *(новый — handler нужен)*

### Ряд 1
- [ ] 👤 My profile
- [ ] 💳 Top-up balance

### Ряд 2
- [ ] 🔎 Search
- [ ] 📈 CREDIT REPORTS

### Ряд 3
- [ ] 📄 DOCUMENTS
- [ ] 🧰 PROS & FULLZ

### Ряд 4
- [ ] 🏦 BANKS
- [ ] 🧾 Subscriptions / Accounts

### Ряд 5
- [ ] CC будет 3-4 категории и внутри них будут товары они также закружаються через селлер панель и одобрение модерацией 

### Ряд 6
- [ ] 📶 eSIM
- [ ] ✍️ Add info in CR

### Ряд 7
- [ ] 📞 Support
- [ ] 🤝 Referrals +4%

### Ряд 8
- [ ] 📞 ANOTHER SERVICES *(новый — handler нужен)*

---

## 2. Детальная структура каждого раздела

---

### 2.1 👤 My profile

| Уровень | Кнопка | callback_data | Handler |
|---------|--------|---------------|---------|
| Вход | MY_PROFILE | — | `profile.py` F.text |

нужно сделать пордменю еще на cc 
логика подписок из обучения 
| Подменю | My Bank Orders | buyer_my_orders | buyer_orders.py |
| | Send money | send_money | profile.py |
| | Referral system | ref_system | profile.py |
| | View Rules | view_rules | profile.py |
| | Choose language | choose_lang | profile.py |
| | Back | back_main | start.py |

**Клавиатура:** `inline.py` → `profile_keyboard()`

---

### 2.2 💳 Top-up balance

| Уровень | Кнопка | callback_data | Handler |
|---------|--------|---------------|---------|
| Вход | TOP_UP_BALANCE | — | `profile.py` F.text |
| Подменю | BTC LTC XMR | pay_cryptopay | profile.py | инт еграция btcpay
| | Pay via Cryptomus | Another | profile.py | интеграция helecat
| | Back | back_main | start.py |

**Клавиатура:** `inline.py` → `topup_keyboard()`  
**FSM:** TopupStates (waiting_amount → waiting_payment)

---

### 2.3 🔎 Search (Lookup)

| Уровень | Кнопка | callback_data | Handler |
|---------|--------|---------------|---------|
| Вход | SEARCH | — | `lookup/main.py` F.text |
| Подменю | SSN & DOB | lookup_ssn | lookup/ssn.py |
| | Credit Score | lookup_credit | lookup/others.py |
| | DL | lookup_dl | lookup/others.py |
| | MVR | lookup_mvr | lookup/others.py |
| | Full MVR | lookup_fullmvr | lookup/others.py |
| | Phone Search | lookup_phone | lookup/main.py |
| | → Name Lookup | phone_name | lookup/phone.py |
| | → Name DOB SSN | phone_ssn | lookup/phone.py |
| | → Full Lookup | phone_full | lookup/phone.py |
| | BG | lookup_bg | lookup/others.py |
| | MMN | lookup_mmn | lookup/others.py |
| | EIN | lookup_ein | lookup/others.py |
тут добавляем lookup ba новый раздел там будут товары
Check AN+RN © $5/ one bank

Check Transactions [15 days] © $5/one bank Check Balance

Check NAME © $3/one bank Check AN+RN+NAME © $7 / one bank

© $5/one bank


| | Back | back_main | start.py |

**Клавиатура:** `inline.py` → `lookup_keyboard()`, `phone_search_keyboard()`  
**Поток:** сервис → Single/Bulk → ввод данных → Order

---

### 2.4 📈 CREDIT REPORTS

| Уровень | Кнопка | callback_data | Handler |
|---------|--------|---------------|---------|
| Вход | CREDIT_REPORTS | — | `credit_reports.py` F.text |
| Подменю | TransUnion | cr_transunion | credit_reports.py |
| | Experian | cr_experian | credit_reports.py |
| | Equifax | cr_equifax | credit_reports.py |
| | LexisNexis | cr_lexisnexis | credit_reports.py |
| | WalletHub | cr_wallet | credit_reports.py |
| | Back | back_main | start.py |

**Клавиатура:** `inline.py` → `credit_reports_keyboard()`  
**Поток:** выбор бюро → ввод данных → Order

---

### 2.5 📄 DOCUMENTS

| Уровень | Кнопка | callback_data | Handler |
|---------|--------|---------------|---------|
| Вход | DOCUMENTS | — | `documents.py` F.text |
| Подменю | Photo | doc_photo | documents.py |
| | → DL (Front & Back) | doc_photo_dl | documents.py |
| | → DL + Selfie | doc_photo_dl_selfie | documents.py |
| | → Passport | doc_photo_passport | documents.py |
| | → Business Docs | doc_photo_biz | documents.py |
| | High-Quality Drawing | doc_drawing_high | (SOON) |
| | Robot Drawing | doc_drawing_robot | (SOON) |
| | Back | back_main | start.py |

**Для каждого типа:** выбор штата (4 стр) → Product или Order  
**Клавиатура:** `documents.py` → `documents_main_keyboard()`, `photo_catalog_keyboard()`, `doc_states_keyboard()`

---

### 2.6 🧰 PROS & FULLZ

| Уровень | Кнопка | callback_data | Handler |
|---------|--------|---------------|---------|
| Вход | PROS_FULLZ | — | `fullz.py` F.text |
| Подменю | PERSONAL | fullz_personal | fullz.py |
| | BUSINESS | fullz_business | fullz.py |
| | Back | back_main | start.py |

**PERSONAL / BUSINESS → профиль:**
| | CUSTOM CS/CR | fullz_prof:cscr | fullz.py |
| | MILITARY | fullz_prof:military | fullz.py |
| | WORK & TRAVEL | fullz_prof:worktravel | fullz.py |
| | YOUNG | fullz_prof:young | fullz.py |
| | RANDOM | fullz_prof:random | fullz.py |

**→ штат (4 стр)** → company/cs/loan/age/gender/report → **количество** → confirm → Order

**Клавиатура:** `fullz.py` — inline функции  
**FSM:** FullzStates, RandomFullzStates

---

### 2.7 🏦 BANKS

добавляем логику в нутрь кадого 
PERSONAL BUSINESS CRYPTO категории in stocks смотри из селлер панели, per order(заказы как раньше), on name(заказы как раньше)

Brute BANK для буртбанк нуно удобная селлер панель тоже и удобная inline клавиатура

| Уровень | Кнопка | callback_data | Handler |
|---------|--------|---------------|---------|
| Вход | BANKS | — | `banks.py` F.text |
| Подменю | 💳 PERSONAL VCC | banks_vcc | banks.py |
| | 🏦 PERSONAL BANKS | banks_personal | banks.py |
| | 🏢 BUSINESS BANKS | banks_business | banks.py |
| | 🪙 CRYPTO BANKS | banks_crypto | banks.py |
| | 🔓 Brute BANK (SOON) | lookup_support:banks_main | lookup/main.py |
| | Back | back_main | start.py |

**Для vcc/personal/business/crypto:**
```
banks_{cat} → каталог (BankItem/BankData)
    → bank_item:{id} → описание
        → bank_qty:{id}:2/3/5/10
        → bank_custom:{id}
        → bank_buy:{id}:1
        → bank_back:{id}
```

**Логика:** In Stock → SellerOrder | Out of Stock → Order (воркерам)

**Клавиатура:** `inline.py` → `banks_main_keyboard()`, `banks_catalog_keyboard()`, `bank_item_keyboard()`  
**Данные:** `bank_data.py` BankData.CATEGORIES, БД BankItem

---

### 2.8 Banks — подкатегории (порядок можно менять)

**Файл:** `mirror_bot/keyboards/inline.py` → `banks_main_keyboard()`

| # | Кнопка | callback | Описание |
|---|--------|----------|----------|
| 1 | 💳 PERSONAL VCC | banks_vcc | Chime, PayPal, Current, Venmo... |
| 2 | 🏦 PERSONAL BANKS | banks_personal | Citi, Chase, Wells, BoA... |
| 3 | 🏢 BUSINESS BANKS | banks_business | QuickBooks, Chase Biz, Wells Biz... |
| 4 | 🪙 CRYPTO BANKS | banks_crypto | Cash App, Coinbase, Binance... |
| 5 | 🔓 Brute BANK (SOON) | lookup_support:banks_main | Инфо, не каталог |
| 6 | ⬅️ Back | back_main | Главное меню |

---

### 2.9 🧾 Subscriptions / Accounts

| Уровень | Кнопка | callback_data | Handler |
|---------|--------|---------------|---------|
| Вход | SUBSCRIPTIONS_ACCOUNTS | — | `accounts.py` F.text |
| Подменю | *динамические категории из БД* | acc_cat:\<code\> | accounts.py |
| | Back | back_main | start.py |
| Каталог | *товары категории, пагинация* | acc_page:\<code\>:\<page\> | accounts.py |
| Товар | *деталь товара* | acc_item:\<id\> | accounts.py |
| Покупка | *количество* | acc_buy:\<id\>:\<qty\> | accounts.py |
| Custom | *ввод количества* | acc_custom:\<id\> | accounts.py |

**Категории и товары:** из БД (`AccountCategory`, `AccountItem`), управляются через web_panel CRUD + drag-and-drop  
**Клавиатура:** `accounts.py` → `accounts_main_keyboard()`, `accounts_catalog_keyboard()`  
**Instant delivery:** из `AccountInventory`, поддержка частичной доставки

---

### 2.10 📶 eSIM
| Уровень | Кнопка | callback_data | Handler |
|---------|--------|---------------|---------|
| Вход | ESIM | — | `esim.py` F.text |
| Подменю | eSIM for SMS | esim_sms | esim.py → каталог `AccountItem` (`esim_sms`) |
| | eSIM for Data | esim_data | esim.py → каталог `AccountItem` (`esim_data`) |
| | eSIM with CS/CR | esim_configurator | esim.py (Configurator, цены `ServicePrices`) |
| | Google Voice | esim_gv | esim.py → каталог `AccountItem` (`gv`) |
| | Back | back_main | start.py |

**Каталог (SMS / Data / GV):** динамические кнопки `esim_item:{id}` → карточка → `esim_ib` / `esim_iq` → при qty>1: `confirm_bulk_esim` / `cancel_bulk_esim` (FSM `ESIMStates.confirm_bulk_purchase`).  
**Засев цен/позиций SMS·Data:** `support_bot/handlers/esim.py` + web `ServicePrice` (legacy сид для матрицы). Позиции mirror-бота для SMS/Data — **`account_items`** с `category_code` `esim_sms` / `esim_data`.

**Клавиатура:** `inline.py` → `esim_main_keyboard`; списки товаров и qty — в `esim.py`  
**Данные:** БД `account_items` / `account_inventory`; Configurator — `OPERATOR_PRICES` + `ServicePrices` в `esim.py`

---

### 2.11 ✍️ Add info in CR
| Уровень | Кнопка | callback_data | Handler |
|---------|--------|---------------|---------|
| Вход | ADD_INFO_CR | — | `addinfo.py` F.text |
| Подменю | Add Info in CR | addinfo_addcr | addinfo.py |
| | Add Info in BG | addinfo_addbg | addinfo.py |
| | Add Employer | addinfo_employer | addinfo.py |
| | Unfreeze CR | addinfo_unfreeze | addinfo.py |
| | Back | back_main | start.py |

**addcr:** addcr_all, addcr_phone_addr, addcr_phone_all, addcr_addr_all, addcr_phone_ex, addcr_addr_ex, addcr_phone_tu, addcr_addr_tu  
**addbg:** addbg_phone_addr, addbg_phone, addbg_addr  
**employer:** addemp_tu, addemp_update, addemp_remove  
**unfreeze:** unfreeze_tu, unfreeze_ex

**Клавиатура:** `addinfo.py` → addinfo_*_keyboard()  
**Данные:** `addinfo_data.py` AddInfoData

---

### 2.12 📞 Support

| Уровень | Кнопка | callback_data | Handler |
|---------|--------|---------------|---------|
| Вход | SUPPORT | — | `support.py` F.text |
| Подменю | Payment | support_category_payment | support.py |
| | Product | support_category_product | support.py |
| | General | support_category_general | support.py |
| | Partnership | support_category_partnership | support.py |
| | My tickets | my_tickets | support.py |
| | Back | back_main | start.py |

**Клавиатура:** `inline.py` → `support_categories_keyboard()`  
**Модель:** SupportTicket, SupportMessage

---

### 2.13 🤝 Referrals

| Уровень | Кнопка | callback_data | Handler |
|---------|--------|---------------|---------|
| Вход | REFERRALS | — | `rules.py` F.text |

Ведёт на referral_system (текст + ссылка).

---

### 2.14 📞 CALL SERVICE

| Уровень | Кнопка | callback_data | Handler |
|---------|--------|---------------|---------|
| Вход | CALL_SERVICE | — | `rules.py` F.text |

Показывает контакт/ссылку сервиса.

---

## 3. Схема главного меню (текущая в коде)

```
Ряд 1: [👤 My profile]     [💳 Top-up balance]
Ряд 2: [🔎 Search]         [📈 CREDIT REPORTS]
Ряд 3: [📄 DOCUMENTS]      [🧰 PROS & FULLZ]
Ряд 4: [🏦 BANKS]          [🧾 Subscriptions / Accounts]
Ряд 5: [📶 eSIM]           [✍️ Add info in CR]
Ряд 6: [📞 Support]        [🤝 Referrals +4%]
Ряд 7: [📞 CALL SERVICE]
```

---

## 4. Файлы для правок

| Что менять | Файл |
|------------|------|
| Главное меню | `mirror_bot/keyboards/reply.py` |
| Banks подменю | `mirror_bot/keyboards/inline.py` → banks_main_keyboard |
| Тексты кнопок (en/ru/zh) | `mirror_bot/constants/buttons_*.py` |
| Handlers для новых кнопок | `mirror_bot/handlers/*.py` |
| reorder (Заказать ещё) | `mirror_bot/handlers/start.py`, `inline.py` → reorder_keyboard |



нужно продумать логики всех селер панелей и сделать удобную навигацию во всем
нужно сделать все разделы адаптивными и захардкожены одновремено 
нужно продумать стуруктуру для управления подписками и мануалами (разделы новой категории)
в них нужно подписками на определеное время выдаються как заказ я добавляю и все
мануалами просто каталог 