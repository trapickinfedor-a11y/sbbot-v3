# База данных товаров Seller Bot — Полная схема

## Оглавление

1. [CC (Credit Cards)](#1-cc-credit-cards)
2. [Bank Selfregs](#2-bank-selfregs)
3. [Brute Bank](#3-brute-bank)
4. [Selfreg CC](#4-selfreg-cc)
5. [NFC](#5-nfc)
6. [OTP](#6-otp)
7. [Enroll](#7-enroll)
8. [Logs](#8-logs)
9. [Checks](#9-checks)
10. [Общие правила](#10-общие-правила)

---

## 1. CC (Credit Cards)

**Модель:** `SellerCCItem`  
**Таблица:** `seller_cc_items`

| Поле | Тип | Обязательное | Примечание |
|------|-----|:------------:|------------|
| `id` | Integer | ✅ | Primary Key, Auto |
| `seller_id` | Integer | ✅ | FK → sellers |
| `category_code` | String(50) | ✅ | usa / world |
| `number` | String(255) | ✅ | **🔒 Encrypted** |
| `exp` | String(10) | ✅ | **🔒 Encrypted** |
| `cvv` | String(10) | ✅ | **🔒 Encrypted** |
| `card_bin` | String(6) | ✅ | Первые 6 цифр номера |
| `card_brand` | String(50) | ❌ | Visa/Mastercard/Amex/Discover |
| `card_level` | String(50) | ❌ | Classic/Gold/Platinum/Signature |
| `card_type` | String(20) | ❌ | CREDIT/DEBIT/PREPAID |
| `bank_name` | String(255) | ❌ | Название банка |
| `country` | String(10) | ❌ | US/GB/CA/etc |
| `state` | String(10) | ❌ | Штат (2 буквы) |
| `city` | String(100) | ❌ | Город |
| `zip` | String(20) | ❌ | Почтовый индекс |
| `address` | String(500) | ❌ | Адрес |
| `fname` | String(100) | ❌ | Имя держателя |
| `lname` | String(100) | ❌ | Фамилия держателя |
| `is_non_vbv` | Boolean | ✅ | default: False |
| `seller_price` | Decimal(10,2) | ✅ | Цена от селлера |
| `buyer_price` | Decimal(10,2) | ✅ | Цена для покупателя |
| `moderation_status` | String(50) | ✅ | pending_moderation/approved/rejected |
| `is_active` | Boolean | ✅ | default: True |
| `extra_data` | JSON | ❌ | phone, email, ssn, dob, dl, info, ref |
| `seller_price_non_vbv` | Decimal(10,2) | ❌ | Цена для NON VBV карт |
| `buyer_price_non_vbv` | Decimal(10,2) | ❌ | Цена для покупателя (NON VBV) |
| `created_at` | DateTime | ✅ | Auto |

**extra_data структура:**
```json
{
  "bin": "443264",
  "exp": "10/26",
  "card_type": "DEBIT",
  "brand": "Visa",
  "level": "CLASSIC",
  "bank": "U.S. BANK N.A.",
  "country": "US",
  "holder": "Jesse Van Der Sluis",
  "phone": "+1234567890",
  "email": "test@example.com",
  "ssn": "123-45-6789",
  "dob": "01/15/1990",
  "dl": "D1234567",
  "info": "base01",
  "ref": "14"
}
```

### Предзагруженные категории

**Категории CC:**

| Код | Название | Поле в БД |
|-----|----------|-----------|
| `usa` | USA CC | `category_code = "usa"` |
| `world` | World CC | `category_code = "world"` |
| `non_vbv` | NON VBV | `is_non_vbv = True` (виртуальная категория) |

**Примечание:** 
- Если `is_non_vbv = True`, карта показывается ТОЛЬКО в категории NON VBV, независимо от `category_code`
- Для NON VBV карт используются поля `seller_price_non_vbv` и `buyer_price_non_vbv`
- Если NON VBV цены не указаны, используются обычные цены

**Bulk Format (Mini App v2):**
```
NUMBER|EXP|CVV|NAME|ZIP|STATE|COUNTRY|BANK|TYPE|NON_VBV
```

**Legacy Bulk Format:**
```
NUMBER|EXP|CVV|TYPE|BRAND|LVL|BANK|COUNTRY|HOLDER|ADDR|STATE|CITY|ZIP|Info|REF|PRICE
```

Оба формата поддерживаются парсером.

---

## 2. Banks (Universal Bank Products)

**Модель:** `SellerBankItem` (ранее `SellerBankSelfregItem`)  
**Таблица:** `seller_bank_items` (ранее `seller_bank_selfreg_items`)

**Включает:**
- Bank Selfregs (самостоятельная регистрация банковских аккаунтов)
- Selfreg BA (объединено с Banks — та же функциональность)
- Все категории: VCC, Personal, Business, Crypto, Merchant

| Поле | Тип | Обязательное | Примечание |
|------|-----|:------------:|------------|
| `id` | Integer | ✅ | Primary Key, Auto |
| `seller_id` | Integer | ✅ | FK → sellers |
| `category` | String(20) | ✅ | vcc/personal/business/crypto/merchant |
| `bank_code` | String(50) | ❌ | vcc_chime, pers_chase, etc. |
| `bank_name` | String(120) | ✅ | Название банка |
| `product_type` | String(100) | ❌ | "Checking Account", "Virtual Card", etc. |
| `registration_date` | Date | ✅ | Дата регистрации аккаунта |
| `balance` | Decimal(10,2) | ❌ | Баланс аккаунта (может быть > 0) |
| `state` | String(10) | ✅ | Штат (2 буквы) |
| `zip` | String(20) | ✅ | Почтовый индекс |
| `has_phone` | Boolean | ✅ | default: False |
| `phone_days_remaining` | Integer | ❌ | Дней осталось на телефоне |
| `phone_renewable` | Boolean | ❌ | Телефон продлеваемый |
| `phone_can_swap` | Boolean | ❌ | Можно менять номер |
| `has_email` | Boolean | ✅ | default: False |
| `email_access` | Boolean | ✅ | default: False |
| `has_ssn` | Boolean | ✅ | default: False |
| `has_docs` | Boolean | ✅ | default: False |
| `online_access` | Boolean | ✅ | default: True |
| `return_item_enabled` | Boolean | ❌ | Можно вернуть товар |
| `return_days` | Integer | ❌ | Дней на возврат |
| `credentials_file_path` | String(500) | ✅ | Путь к файлу с credentials |
| `seller_price` | Decimal(10,2) | ✅ | Цена от селлера |
| `buyer_price` | Decimal(10,2) | ✅ | Цена для покупателя |
| `moderation_status` | String(30) | ✅ | pending_moderation/approved/rejected |
| `is_active` | Boolean | ✅ | default: True |
| `created_at` | DateTime | ✅ | Auto |

### Предзагруженные категории

**Категории Banks:**

| Код | Название | Количество банков |
|-----|----------|-------------------|
| `vcc` | VCC | 14 |
| `personal` | Personal | 15 |
| `business` | Business | 10 |
| `crypto` | Crypto | 6 |
| `merchant` | Merchant | 9 |

**Product Types по категориям:**

**VCC:**
- Virtual Card, Prepaid Card, Gift Card

**Personal:**
- Checking Account, Savings Account, Money Market, CD Account

**Business:**
- Business Checking, Business Savings, Merchant Account, LLC Account, Corp Account

**Crypto:**
- Spot Account, Futures Account, Wallet, Exchange Account

**Merchant:**
- Merchant Account, Business Account, Payment Gateway, LLC Account

**Примечание:** Баланс теперь может быть любым значением (не только 0)

---

## 3. Brute Bank

### 3.1 Группы (BruteBankGroup)

**Модель:** `BruteBankGroup`  
**Таблица:** `brute_bank_groups`

| Поле | Тип | Обязательное | Примечание |
|------|-----|:------------:|------------|
| `id` | Integer | ✅ | Primary Key, Auto |
| `seller_id` | Integer | ✅ | FK → sellers |
| `group_key` | String(100) | ✅ | Auto-generated, для группировки |
| `bank_name` | String(255) | ✅ | Название банка |
| `balance_range` | String(100) | ✅ | $1K-$5K, $5K-$10K, etc |
| `account_type` | String(50) | ✅ | CHECKING/SAVINGS/BUSINESS/MONEY MARKET |
| `display_price` | Decimal(10,2) | ✅ | Цена за 1 combo |
| `moderation_status` | String(50) | ✅ | pending_moderation/approved/rejected |
| `is_active` | Boolean | ✅ | default: True |
| `created_at` | DateTime | ✅ | Auto |

### 3.2 Отдельные комбо (BruteBankItem)

**Модель:** `BruteBankItem`  
**Таблица:** `brute_bank_items`

| Поле | Тип | Обязательное | Примечание |
|------|-----|:------------:|------------|
| `id` | Integer | ✅ | Primary Key, Auto |
| `group_id` | Integer | ✅ | FK → brute_bank_groups |
| `login` | String(255) | ✅ | **🔒 Encrypted** |
| `password` | String(255) | ✅ | **🔒 Encrypted** |
| `exact_balance` | String(50) | ❌ | Точный баланс (например, "$4,820") |
| `account_number` | String(255) | ❌ | **🔒 Encrypted** - номер счета |
| `routing_number` | String(255) | ❌ | **🔒 Encrypted** - routing number |
| `holder_name` | String(200) | ❌ | Имя держателя счета |
| `address` | String(500) | ❌ | Адрес |
| `state` | String(10) | ❌ | Штат (2 буквы) |
| `zip` | String(20) | ❌ | Почтовый индекс |
| `additional_info` | Text | ❌ | Дополнительная информация |
| `has_docs` | Boolean | ❌ | Есть документы |
| `is_sold` | Boolean | ✅ | default: False |
| `created_at` | DateTime | ✅ | Auto |

### Предзагруженные категории и банки

**Категории Brute Bank:**

| Код | Название |
|-----|----------|
| `vcc` | VCC Banks |
| `personal` | Personal Banks |
| `business` | Business Banks |
| `crypto` | Crypto Banks |
| `general` | General (по умолчанию) |

**Предзагруженные банки (54 шт):**

**VCC Banks (14):**
- Chime VCC, PayPal VCC, One Pay VCC, Current VCC
- Neteller VCC, Wise Personal VCC, Netspend VCC, GreenFi VCC
- QuickBooks VCC, Go2Bank + VCC, Venmo, Kikoff, Shopify, Varo + VCC

**Personal Banks (15):**
- Citi Personal, Citi Gold Bank, Usalliance, US Bank, Ally Bank
- Regions Bank, Chase, WellsFargo, Charles Schwab, Citizens Bank
- Huntington Bank, TD bank, BankOFAmerica, Alliant Cu, Pnc Bank

**Business Banks (10):**
- QuickBooks (LLC/CORP), Bmo Business, BankOFAmerica Business
- Us Business, North One (LLC/Corp), Lili Business Vcc
- Pnc Business, Capital One Business, Chase Business, Wells Fargo Business

**Crypto Banks (6):**
- Cash App + BTC, Blockchain Gold, Kraken
- CoinBase, Crypto.com, Binance

**Merchant Banks (9):**
- Mercury LLC, Rho LLC, Relay LLC Europe/USA Owner
- Revolut Business LLC, Blue Vine LLC, Novobank LLC
- Wise Business LLC, Payoneer LLC, Revolut Personal on EMU

**Источник:** `shared/catalog_banks.py`

**Атрибуты (attributes):**
- `AN:RN` - Account Number + Routing Number
- `AN:RN+INST YODLEE` - + интеграция Yodlee
- `CHECKING` - Чековый счет
- `SAVINGS` - Сберегательный счет
- `BUSINESS` - Бизнес счет
- `MONEY MARKET` - Money Market счет
- `$1K-$5K`, `$5K-$10K` - Диапазоны баланса

---

## 4. Selfreg CC

**Модель:** `SellerSelfregCCItem`  
**Таблица:** `seller_selfreg_cc_items`

| Поле | Тип | Обязательное | Примечание |
|------|-----|:------------:|------------|
| `id` | Integer | ✅ | Primary Key, Auto |
| `seller_id` | Integer | ✅ | FK → sellers |
| `selfreg_cc_category_id` | Integer | ❌ | FK → selfreg_cc_categories |
| `item_name` | String(200) | ✅ | Название товара |
| `bank_name` | String(120) | ✅ | Название банка |
| `card_name` | String(120) | ❌ | Название карты |
| `credit_limit` | Decimal(10,2) | ❌ | Кредитный лимит (USD) |
| `vcc_limit` | Decimal(10,2) | ❌ | VCC лимит (USD) |
| `state` | String(50) | ❌ | Штат |
| `zip` | String(20) | ❌ | Почтовый индекс |
| `has_email` | Boolean | ✅ | default: False |
| `has_phone` | Boolean | ✅ | default: False |
| `phone_days_remaining` | Integer | ❌ | Дней осталось на телефоне |
| `phone_renewable` | Boolean | ❌ | Телефон продлеваемый |
| `phone_change_allowed` | Boolean | ❌ | Можно сменить телефон |
| `online_access` | Boolean | ✅ | default: False |
| `seller_price` | Decimal(10,2) | ✅ | Цена от селлера |
| `buyer_price` | Decimal(10,2) | ✅ | Цена для покупателя |
| `moderation_status` | String(30) | ✅ | pending_moderation/approved/rejected |
| `is_active` | Boolean | ✅ | default: True |
| `registration_date` | Date | ❌ | Дата регистрации карты |
| `vcc_bin` | String(6) | ❌ | BIN виртуальной карты |
| `return_item_enabled` | Boolean | ❌ | Можно вернуть товар |
| `return_days` | Integer | ❌ | Дней на возврат |
| `created_at` | DateTime | ✅ | Auto |

### Предзагруженные категории

**Selfreg CC Categories (банки):**

| Код | Название |
|-----|----------|
| `citi` | CITI |
| `chase` | Chase |
| `wells` | Wells Fargo |
| `onepay` | ONEPAY |
| `boa` | BOA (Bank of America) |
| `capital_one` | Capital One |
| `discover` | Discover |
| `amex` | American Express |
| `usbank` | US Bank |
| `pnc` | PNC Bank |
| `td` | TD Bank |
| `barclays` | Barclays |
| `synchrony` | Synchrony |

**Всего:** 13 банков (5 базовых + 8 расширенных)

**Card Names (таблица `selfreg_cc_card_names`):**

Для каждого банка хранится список названий карт. Примеры:

**Chase:**
- Chase Freedom Unlimited
- Chase Freedom Flex
- Chase Sapphire Preferred
- Chase Sapphire Reserve
- Chase Ink Business Cash
- Chase Ink Business Unlimited

**Citi:**
- Citi Double Cash
- Citi Custom Cash
- Citi Premier
- Citi Rewards+
- Citi Simplicity

**Capital One:**
- Capital One Venture X
- Capital One Venture
- Capital One Quicksilver
- Capital One SavorOne
- Capital One Savor

(Полный список в Mini App: 6-12 карт на банк)

**Запрос новых категорий:**
- Seller может запросить добавление нового банка
- Модель: `SelfregCCCategoryRequest`
- Время модерации: 1-6 часов
- После одобрения создается `SelfregCCCategory` с `is_custom = True`

---

## 5. NFC

**Модель:** `SellerNFCItem`  
**Таблица:** `seller_nfc_items`

| Поле | Тип | Обязательное | Примечание |
|------|-----|:------------:|------------|
| `id` | Integer | ✅ | Primary Key, Auto |
| `seller_id` | Integer | ✅ | FK → sellers |
| `item_name` | String(200) | ✅ | Название товара |
| `nfc_type` | String(10) | ✅ | ap (Apple Pay) / gp (Google Pay) / other |
| `bank_name` | String(120) | ✅ | Название банка |
| `country` | String(10) | ✅ | US/GB/CA/etc |
| `state` | String(50) | ❌ | Штат |
| `zip` | String(20) | ❌ | Почтовый индекс |
| `data_file_path` | String(500) | ✅ | Путь к файлу с данными NFC |
| `description` | Text | ❌ | Описание |
| `instruction` | Text | ❌ | Инструкция |
| `seller_price` | Decimal(10,2) | ✅ | Цена от селлера |
| `buyer_price` | Decimal(10,2) | ✅ | Цена для покупателя |
| `moderation_status` | String(30) | ✅ | pending_moderation/approved/rejected |
| `is_active` | Boolean | ✅ | default: True |
| `created_at` | DateTime | ✅ | Auto |

### Предзагруженные типы

**NFC Types:**

| Код | Название | Emoji |
|-----|----------|-------|
| `ap` | Apple Pay | 🍎 |
| `gp` | Google Pay | 🤖 |
| `other` | Other NFC | 📎 |

**Примечание:** Seller выбирает тип при загрузке. Категории отображаются покупателю как отдельные разделы.

---

## 6. OTP

**Модель:** `SellerOTPItem`  
**Таблица:** `seller_otp_items`

| Поле | Тип | Обязательное | Примечание |
|------|-----|:------------:|------------|
| `id` | Integer | ✅ | Primary Key, Auto |
| `seller_id` | Integer | ✅ | FK → sellers |
| `item_name` | String(200) | ✅ | Название товара |
| `bank_name` | String(120) | ✅ | Название банка |
| `balance` | Decimal(10,2) | ✅ | Баланс (USD) |
| `has_fullz` | Boolean | ✅ | default: False |
| `sms_access_type` | String(30) | ✅ | seller_mediated / account_access |
| `data_file_path` | String(500) | ✅ | Путь к файлу с данными доступа |
| `description` | Text | ❌ | Описание |
| `instruction` | Text | ❌ | Инструкция |
| `seller_price` | Decimal(10,2) | ✅ | Цена от селлера |
| `buyer_price` | Decimal(10,2) | ✅ | Цена для покупателя |
| `moderation_status` | String(30) | ✅ | pending_moderation/approved/rejected |
| `is_active` | Boolean | ✅ | default: True |
| `state` | String(10) | ❌ | Штат |
| `zip` | String(20) | ❌ | Почтовый индекс |
| `fullz_first_name` | String(100) | ❌ | Имя (Fullz) |
| `fullz_last_name` | String(100) | ❌ | Фамилия (Fullz) |
| `fullz_dob` | Date | ❌ | Дата рождения (Fullz) |
| `fullz_ssn` | String(20) | ❌ | **🔒 Encrypted** - SSN (Fullz) |
| `fullz_address` | String(500) | ❌ | Адрес (Fullz) |
| `fullz_city` | String(100) | ❌ | Город (Fullz) |
| `fullz_state` | String(10) | ❌ | Штат (Fullz) |
| `fullz_zip` | String(20) | ❌ | ZIP (Fullz) |
| `fullz_phone` | String(50) | ❌ | Телефон (Fullz) |
| `fullz_email` | String(200) | ❌ | Email (Fullz) |
| `created_at` | DateTime | ✅ | Auto |

### Предзагруженные типы

**SMS Access Types:**

| Код | Название | Emoji | Описание |
|-----|----------|-------|----------|
| `seller_mediated` | Via Seller | 👤 | SMS через seller (медиация) |
| `account_access` | Direct Access | 🔓 | Прямой доступ к аккаунту |

**Mini App использует:** `in_chat` (= seller_mediated) и `file` (= account_access)

**Fullz Fields:**
- Если `has_fullz = True`, заполняются поля `fullz_*`
- Все Fullz поля опциональные
- SSN шифруется при сохранении

**Примечание:** Seller выбирает тип доступа при загрузке. Это влияет на отображение и цену товара.

---

## 7. Enroll

**Модель:** `SellerEnrollItem`  
**Таблица:** `seller_enroll_items`

| Поле | Тип | Обязательное | Примечание |
|------|-----|:------------:|------------|
| `id` | Integer | ✅ | Primary Key, Auto |
| `seller_id` | Integer | ✅ | FK → sellers |
| `enroll_category_id` | Integer | ❌ | FK → enroll_categories |
| `portal` | String(100) | ✅ | Название портала |
| `bank_name` | String(120) | ❌ | Название банка |
| `card_zip` | String(20) | ❌ | ZIP код карты |
| `card_state` | String(50) | ❌ | Штат карты |
| `card_type` | String(20) | ❌ | Credit/Debit |
| `balance` | Float | ✅ | Баланс (USD) |
| `data_file_path` | String(500) | ✅ | Путь к файлу с данными |
| `has_ssn` | Boolean | ✅ | default: False |
| `has_dob` | Boolean | ✅ | default: False |
| `has_address` | Boolean | ✅ | default: False |
| `has_docs` | Boolean | ✅ | default: False |
| `online_access` | Boolean | ✅ | default: True |
| `price` | Float | ✅ | Цена |
| `moderation_status` | String(20) | ✅ | pending_moderation/approved/rejected |
| `is_active` | Boolean | ✅ | default: True |
| `first_name` | String(100) | ❌ | Имя |
| `last_name` | String(100) | ❌ | Фамилия |
| `dob` | Date | ❌ | Дата рождения |
| `ssn` | String(20) | ❌ | **🔒 Encrypted** - SSN |
| `address` | String(500) | ❌ | Адрес |
| `city` | String(100) | ❌ | Город |
| `state` | String(10) | ❌ | Штат |
| `zip` | String(20) | ❌ | Почтовый индекс |
| `phone` | String(50) | ❌ | Телефон |
| `email` | String(200) | ❌ | Email |
| `additional_info` | Text | ❌ | Дополнительная информация |
| `created_at` | DateTime | ✅ | Auto |

### Предзагруженные порталы

**Enroll Categories (порталы):**

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
| `centresuite` | CENTRESUITE (minik) |
| `elan` | Elan |

**Всего:** 12 порталов (11 базовых + 1 новый)

**Детальные поля:**
- Все персональные данные (имя, адрес, DOB, SSN, телефон, email) теперь хранятся в отдельных полях
- Флаги `has_*` указывают на наличие данных
- SSN шифруется при сохранении

**Запрос новых порталов:**
- Seller может запросить добавление нового портала
- Модель: `EnrollCategoryRequest`
- Время модерации: 1-6 часов
- После одобрения создается `EnrollCategory` с `is_custom = True`

---

## 8. Logs

**Модель:** `SellerLogsItem`  
**Таблица:** `seller_logs_items`

| Поле | Тип | Обязательное | Примечание |
|------|-----|:------------:|------------|
| `id` | Integer | ✅ | Primary Key, Auto |
| `seller_id` | Integer | ✅ | FK → sellers |
| `bank` | String(100) | ✅ | Название банка |
| `total_balance` | Float | ✅ | Общий баланс (USD) |
| `log_file_path` | String(500) | ✅ | Путь к файлу с логами |
| `description_en` | Text | ✅ | Описание на английском |
| `has_cvv` | Boolean | ✅ | default: False |
| `bt_available` | Boolean | ✅ | default: False |
| `promo_available` | Boolean | ✅ | default: False |
| `zelle_enroll` | Boolean | ✅ | default: False |
| `wire_available` | Boolean | ✅ | default: False |
| `safepass_unlocked` | Boolean | ✅ | default: False |
| `email_valid` | Boolean | ✅ | default: False |
| `has_cookies` | Boolean | ✅ | default: False |
| `has_screenshot` | Boolean | ✅ | default: False |
| `price` | Float | ✅ | Цена |
| `moderation_status` | String(20) | ✅ | pending_moderation/approved/rejected |
| `is_active` | Boolean | ✅ | default: True |
| `raw_data` | Text | ❌ | Сырые данные |
| `created_at` | DateTime | ✅ | Auto |

### Предзагруженные категории

**Logs не имеет предзагруженных категорий.**

Seller может указать любое название банка (`bank`). Группировка не используется.

**Флаги (boolean поля):**

| Флаг | Описание |
|------|----------|
| `has_cvv` | Есть CVV |
| `bt_available` | Bank Transfer доступен |
| `promo_available` | Промо доступно |
| `zelle_enroll` | Zelle подключен |
| `wire_available` | Wire доступен |
| `safepass_unlocked` | SafePass разблокирован |
| `email_valid` | Email валидный |
| `has_cookies` | Есть cookies |
| `has_screenshot` | Есть скриншот |

**Примечание:** Флаги показываются покупателю только если `True`.

---

## 9. Checks

**Модель:** `SellerCheckItem`  
**Таблица:** `seller_check_items`

| Поле | Тип | Обязательное | Примечание |
|------|-----|:------------:|------------|
| `id` | Integer | ✅ | Primary Key, Auto |
| `seller_id` | Integer | ✅ | FK → sellers |
| `item_name` | String(200) | ✅ | Название товара |
| `check_type` | String(30) | ✅ | Personal/Business/Payroll/Cashier |
| `bank_name` | String(120) | ✅ | Название банка |
| `amount` | Decimal(10,2) | ✅ | Сумма чека (USD) |
| `state` | String(50) | ❌ | Штат |
| `zip` | String(20) | ❌ | Почтовый индекс |
| `has_holder_name` | Boolean | ✅ | default: False |
| `has_address` | Boolean | ✅ | default: False |
| `check_date` | Date | ❌ | Дата чека |
| `seller_description` | Text | ❌ | Описание от seller |
| `scan_file_path` | String(500) | ✅ | Путь к скану чека |
| `template_file_path` | String(500) | ❌ | Путь к шаблону |
| `seller_price` | Decimal(10,2) | ✅ | Цена от селлера |
| `buyer_price` | Decimal(10,2) | ✅ | Цена для покупателя |
| `moderation_status` | String(30) | ✅ | pending_moderation/approved/rejected |
| `is_active` | Boolean | ✅ | default: True |
| `created_at` | DateTime | ✅ | Auto |

### Предзагруженные типы

**Check Types:**

| Код | Название |
|-----|----------|
| `personal` | Personal |
| `business` | Business |
| `payroll` | Payroll |
| `cashier` | Cashier |

**Примечание:** Seller выбирает тип чека при загрузке. Покупатель видит категории как отдельные разделы.

---

## 10. Общие правила

### 10.1 Обязательные поля для всех типов

| Поле | Описание |
|------|----------|
| `id` | Primary Key, Auto-increment |
| `seller_id` | Foreign Key → sellers |
| `seller_price` | Цена от селлера (USD) |
| `buyer_price` | Цена для покупателя (USD, после markup) |
| `moderation_status` | pending_moderation / approved / rejected |
| `is_active` | Boolean, default: True |
| `created_at` | DateTime, Auto |

### 10.2 Статусы модерации

| Статус | Описание |
|--------|----------|
| `pending_moderation` | Ожидает проверки |
| `approved` | Одобрено, показывается покупателям |
| `rejected` | Отклонено |

### 10.3 Шифрование данных

**Поля, которые шифруются:**

| Тип товара | Зашифрованные поля |
|------------|-------------------|
| CC | `number`, `exp`, `cvv` |
| Brute Bank | `login`, `password` |

**Метод:** AES-256 или аналогичный

### 10.4 Условия показа покупателю

Товар показывается покупателю только если:

```python
item.is_active == True
AND item.moderation_status == "approved"
AND seller.is_approved == True
AND seller.is_active == True
```

### 10.5 Ценообразование

**Формула:**
```python
buyer_price = seller_price + markup

# Markup может быть:
# 1. Процентный: markup = seller_price * (markup_percent / 100)
# 2. Фиксированный: markup = markup_fixed
# 3. Комбинированный
```

### 10.6 Индексы (рекомендуемые)

Для оптимизации запросов рекомендуется создать индексы на:

- `seller_id` (все таблицы)
- `moderation_status` (все таблицы)
- `is_active` (все таблицы)
- `card_bin` (seller_cc_items)
- `bank_name` (все таблицы с bank_name)
- `group_key` (brute_bank_groups)
- `group_id` (brute_bank_items)
- `is_sold` (brute_bank_items)

### 10.7 Связи между таблицами

```
sellers (1) ──→ (N) seller_cc_items
sellers (1) ──→ (N) seller_bank_selfreg_items
sellers (1) ──→ (N) brute_bank_groups
brute_bank_groups (1) ──→ (N) brute_bank_items
sellers (1) ──→ (N) seller_selfreg_cc_items
sellers (1) ──→ (N) seller_nfc_items
sellers (1) ──→ (N) seller_otp_items
sellers (1) ──→ (N) seller_enroll_items
sellers (1) ──→ (N) seller_logs_items
sellers (1) ──→ (N) seller_check_items
```

---

## 11. Сводная таблица предзагруженных категорий

### 11.1 По типам товаров

| Тип товара | Предзагруженные категории/типы | Количество | Можно запросить новые |
|------------|-------------------------------|------------|----------------------|
| **CC** | usa, world, non_vbv | 3 | ❌ |
| **Banks** | vcc, personal, business, crypto, merchant | 5 категорий + 54 банка | ✅ (через админ) |
| **Brute Bank** | vcc, personal, business, crypto, general | 5 + 54 банка | ✅ (через админ) |
| **Selfreg CC** | 13 банков + списки карт | 13 | ✅ (запрос 1-6ч) |
| **NFC** | Apple Pay, Google Pay, Other | 3 | ❌ |
| **OTP** | seller_mediated, account_access | 2 | ❌ |
| **Enroll** | 12 порталов (FDECS, DIGITALCARDSERVICE, Elan и др.) | 12 | ✅ (запрос 1-6ч) |
| **Logs** | Нет (любой bank) | ∞ | ✅ (автоматически) |
| **Checks** | Personal, Business, Payroll, Cashier | 4 | ❌ |

### 11.2 Детальный список всех предзагруженных значений

#### CC Categories
```
1. usa          → USA CC
2. world        → World CC
3. non_vbv      → NON VBV (виртуальная, флаг is_non_vbv=True)
```

#### Brute Bank Categories
```
1. vcc          → VCC Banks (14 банков)
2. personal     → Personal Banks (15 банков)
3. business     → Business Banks (10 банков)
4. crypto       → Crypto Banks (6 банков)
5. general      → General (по умолчанию)
```

#### Brute Bank - VCC Banks (14)
```
1. Chime VCC
2. PayPal VCC
3. One Pay VCC
4. Current VCC
5. Neteller VCC
6. Wise Personal VCC
7. Netspend VCC
8. GreenFi VCC
9. QuickBooks VCC
10. Go2Bank + VCC
11. Venmo
12. Kikoff
13. Shopify
14. Varo + VCC
```

#### Brute Bank - Personal Banks (15)
```
1. Citi Personal
2. Citi Gold Bank
3. Usalliance
4. US Bank
5. Ally Bank
6. Regions Bank
7. Chase
8. WellsFargo
9. Charles Schwab
10. Citizens Bank
11. Huntington Bank
12. TD bank
13. BankOFAmerica
14. Alliant Cu
15. Pnc Bank
```

#### Brute Bank - Business Banks (10)
```
1. QuickBooks (LLC/CORP)
2. Bmo Business
3. BankOFAmerica Business
4. Us Business
5. North One (LLC/Corp)
6. Lili Business Vcc
7. Pnc Business
8. Capital One Business
9. Chase Business
10. Wells Fargo Business
```

#### Brute Bank - Crypto Banks (6)
```
1. Cash App + BTC
2. Blockchain Gold
3. Kraken
4. CoinBase
5. Crypto.com
6. Binance
```

#### Brute Bank - Merchant Banks (9)
```
1. Mercury LLC
2. Rho LLC
3. Relay LLC Europe/USA Owner
4. Revolut Business LLC
5. Blue Vine LLC
6. Novobank LLC
7. Wise Business LLC
8. Payoneer LLC
9. Revolut Personal on EMU
```

#### Selfreg CC Categories (13)
```
1. citi         → CITI
2. chase        → Chase
3. wells        → Wells Fargo
4. onepay       → ONEPAY
5. boa          → BOA (Bank of America)
6. capital_one  → Capital One
7. discover     → Discover
8. amex         → American Express
9. usbank       → US Bank
10. pnc         → PNC Bank
11. td          → TD Bank
12. barclays    → Barclays
13. synchrony   → Synchrony
```

#### NFC Types (3)
```
1. ap           → Apple Pay 🍎
2. gp           → Google Pay 🤖
3. other        → Other NFC 📎
```

#### OTP SMS Access Types (2)
```
1. seller_mediated    → Via Seller 👤
2. account_access     → Direct Access 🔓
```

#### Enroll Portals (12)
```
1. fdecs                  → FDECS
2. digitalcardservice     → DIGITALCARDSERVICE
3. mycardinfo             → MYCARDINFO
4. card_suite_light       → CARD SUITE LIGHT
5. cardnav                → CardNav
6. firefighters           → FIREFIGHTERS
7. coast_central          → COAST CENTRAL
8. web_access             → WEB ACCESS
9. card_suite             → Card Suite
10. myaccountaccess       → Myaccountaccess
11. centresuite           → CENTRESUITE (minik)
12. elan                  → Elan
```

#### Check Types (4)
```
1. personal     → Personal
2. business     → Business
3. payroll      → Payroll
4. cashier      → Cashier
```

### 11.3 Запросы на создание новых категорий

#### Enroll - Запрос нового портала

**Модель:** `EnrollCategoryRequest`  
**Таблица:** `enroll_category_requests`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer | Primary Key |
| `seller_id` | Integer | FK → sellers |
| `requested_name` | String | Название портала |
| `status` | String | pending/approved/rejected |
| `admin_note` | Text | Заметка модератора |
| `created_at` | DateTime | Дата запроса |
| `resolved_at` | DateTime | Дата решения |

**Процесс:**
1. Seller нажимает "📝 Request new portal category"
2. Вводит название портала
3. Создается `EnrollCategoryRequest(status="pending")`
4. Модератор одобряет → создается `EnrollCategory(is_custom=True)`
5. Время модерации: 1-6 часов

#### Selfreg CC - Запрос нового банка

**Модель:** `SelfregCCCategoryRequest`  
**Таблица:** `selfreg_cc_category_requests`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer | Primary Key |
| `seller_id` | Integer | FK → sellers |
| `requested_name` | String | Название банка |
| `status` | String | pending/approved/rejected |
| `admin_note` | Text | Заметка модератора |
| `created_at` | DateTime | Дата запроса |
| `resolved_at` | DateTime | Дата решения |

**Процесс:**
1. Seller нажимает "📝 Request new bank category"
2. Вводит название банка
3. Создается `SelfregCCCategoryRequest(status="pending")`
4. Модератор одобряет → создается `SelfregCCCategory(is_custom=True)`
5. Время модерации: 1-6 часов

### 11.4 Источники данных

| Источник | Файл | Описание |
|----------|------|----------|
| Banks каталог | `shared/catalog_banks.py` | 54 банка в 5 категориях |
| Brute Bank каталог | `shared/catalog_banks.py` | 54 банка в 5 категориях |
| Enroll порталы | БД: `enroll_categories` | 12 предзагруженных + custom |
| Selfreg CC банки | БД: `selfreg_cc_categories` | 13 предзагруженных + custom |
| Selfreg CC карты | БД: `selfreg_cc_card_names` | 6-12 карт на банк |
| Категории веб-панели | `web_panel/constants/categories.py` | Все категории для UI |

---

## 12. Изменения в Mini App v2 (2026-03-24)

### Новые возможности

1. **Banks Section** — универсальная секция для всех банковских продуктов
   - 5 категорий: VCC, Personal, Business, Crypto, Merchant
   - Product Types для каждой категории
   - Поддержка баланса (не только 0)
   - Return Item функционал

2. **Расширенные Fullz поля** — детальные персональные данные
   - OTP: 10 дополнительных полей для Fullz
   - Enrollment: 11 дополнительных полей

3. **NON VBV ценообразование** — отдельные цены для NON VBV карт
   - `seller_price_non_vbv`
   - `buyer_price_non_vbv`

4. **Brute Bank детализация** — расширенные поля для combo
   - Account Number, Routing Number
   - Holder Name, Address, State, ZIP
   - Additional Info, Has Docs

5. **Selfreg CC расширение**
   - С 5 до 13 банков
   - Таблица названий карт (6-12 на банк)
   - Registration Date, VCC BIN
   - Return Item функционал

6. **Новые форматы Bulk**
   - CC: упрощенный формат (10 полей)
   - Brute Bank: детальный формат (11 полей)
   - Оба формата поддерживаются

### Миграция

**Файлы:**
- `docs/MINI_APP_VS_DATABASE_ANALYSIS.md` — детальный анализ
- `docs/DATABASE_MIGRATION_PLAN.md` — план миграции
- `shared/database/migrations/sync_mini_app_v2.py` — Alembic миграция

**Выполнить миграцию:**
```bash
alembic upgrade head
```

---

**Конец документа.**  
**Версия:** 2.0 (синхронизировано с Mini App v2)  
**Дата обновления:** 2026-03-24
