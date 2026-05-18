# ПОЛНЫЙ АУДИТ ВСЕХ РАЗДЕЛОВ
## Seller Mini App + Mirror Bot v2.0

**Дата:** 2026-03-24  
**Версия:** 2.0 (Full Audit)

---

# 📊 СВОДНАЯ ТАБЛИЦА ВСЕХ РАЗДЕЛОВ

| # | Раздел | Статус | Категорий | Банков | Полей | Описание |
|---|--------|--------|-----------|--------|-------|----------|
| 1 | Banks | ✅ | 5 | 51 | 20 | Виртуальные и реальные банки |
| 2 | Brute Bank | ✅ | 1 | 67 | 15 | Доступы с балансам |
| 3 | CC/Debit | ✅ | 2 | BIN | 18 | Кредитные карты |
| 4 | NFC | ✅ | 3 | 20 | 12 | Apple/Google Pay |
| 5 | OTP | ✅ | 1 | 20 | 14 | OTP карты с SMS |
| 6 | Selfreg CC | ✅ | 1 | 12 | 16 | Самозарег карты |
| 7 | Enrollment | ✅ | 12 порталов | 20 | 20 | Enrollment аккаунты |
| 8 | Logs | ✅ | 1 | 20 | 22 | Полные логи банков |
| 9 | Checks | ✅ | 4 | 20 | 10 | Чеки всех типов |
| 10 | ~~Selfreg BA~~ | ❌ | - | - | - | **УДАЛЕН** |

---

# 1️⃣ BANKS (БАНКИ)

## 📋 Описание
Виртуальные и реальные банковские счета по категориям

## 🗂 Категории (5 штук)

| Код | Название | Описание | Product Types |
|-----|----------|----------|---------------|
| `vcc` | VCC | Виртуальные кредитные карты | Virtual Card, Prepaid Card, Gift Card |
| `personal` | Personal | Персональные счета | Checking, Savings, Money Market, CD |
| `business` | Business | Бизнес счета (LLC/CORP) | Business Checking, LLC Account, Corp |
| `crypto` | Crypto | Криптобиржи и кошельки | Spot, Futures, Wallet, Exchange |
| `merchant` | Merchant | Платежные шлюзы | Merchant Account, Payment Gateway |

## 🏦 Каталог банков (51 банк)

### VCC_BANKS (14)
```
Chime VCC, PayPal VCC, One Pay VCC, Current VCC,
Neteller VCC, Wise Personal VCC, Netspend VCC, GreenFi VCC,
QuickBooks VCC, Go2Bank + VCC, Venmo, Kikoff,
Shopify, Varo + VCC
```

### PERSONAL_BANKS (13)
```
Citi Personal, Citi Gold, Usalliance, US Bank, Ally Bank,
Regions Bank, Chase, Wells Fargo, Charles Schwab,
Citizens Bank, Huntington Bank, TD Bank, Bank of America,
Alliant CU, PNC Bank
```

### BUSINESS_BANKS (9)
```
QuickBooks (LLC/CORP), BMO Business, BofA Business, US Business,
North One (LLC/Corp), Lili Business VCC, PNC Business,
Capital One Business, Chase Business, Wells Fargo Business
```

### CRYPTO_BANKS (6)
```
Cash App + BTC, Blockchain Gold, Kraken, CoinBase,
Crypto.com, Binance
```

### MERCHANT_BANKS (9)
```
Mercury LLC, Rho LLC, Relay LLC Europe/USA, Revolut Business LLC,
Blue Vine LLC, Novobank LLC, Wise Business LLC, Payoneer LLC,
Revolut Personal EMU
```

## 📝 Поля товара (SellerBankItem)

**Основные:**
- `bank` (String 100)
- `category` (String 20): vcc/personal/business/crypto/merchant
- `bank_code` (String 50): vcc_chime, pers_chase
- `product_type` (String 100): Virtual Card, Checking Account...
- `registration_date` (Date): MM/DD/YYYY
- `state` (String 10)
- `zip` (String 20)
- `price` (Float)

**Доступ:**
- `email_access` (Boolean)
- `has_phone` (Boolean)
- `phone_days_remaining` (Integer)
- `phone_renewable` (Boolean)
- `phone_can_swap` (Boolean)
- `has_ssn` (Boolean)
- `has_docs` (Boolean)

**Return Item:**
- `return_item_enabled` (Boolean)
- `return_days` (Integer)

**Служебные:**
- `seller_id`, `moderation_status`, `is_active`, `is_in_stock`, `raw_data`, `created_at`

## ⚠️ Balance: НЕТ
- Поле удалено из UI Mini App
- Не используется в форме загрузки
- В модели БД есть но не запрашивается

## 🔄 Moderation Request

**Модель:** `BankTypeRequest`

**Flow:**
```
1. Кнопка "📝 Request new bank"
2. Bank Name → State (2 letters) → ZIP
3. Has Docs? (Yes/No buttons)
4. Doc Type (if Yes)
5. Description (shown to buyers)
6. Save to DB → Admin review
```

**Поля:**
- `seller_id`, `requested_name`, `state`, `zip`
- `has_docs`, `doc_type`, `description`
- `product_type`, `product_subtype`, `category`
- `status` (pending/approved/rejected)
- `admin_note`, `created_at`, `resolved_at`

## 📄 Описание для покупателя

```
🏦 Chase | Personal

📋 Product Type: Checking Account
📅 Registration: 03/15/2025
📍 Location: CA, 90210

✅ Access:
  • Email: Yes
  • Phone: Yes (30 days, renewable: Yes, swap: No)
  • SSN: No
  • Docs: Yes

💰 Price: $45.00
🔄 Return: Yes (7 days)

📦 Stock: 15 items
```

---

# 2️⃣ BRUTE BANK

## 📋 Описание
Доступы к банковским счетам с полными данными

## 🏦 Банки (67 штук)

**Полный список:**
```
3RiversFCU, 53, AllianceCCU, BECU, Bellco, BMO, Canvas, CentraCU, Comerica,
Connexuscu, CorningCU, DesertfinancialCU, DFCUFinancial, DiscoverBank, EducatorsCU,
EmpowerFCU, EnrichmentFCU, FACU, 903 Pl, Familytrust, FibreFCU, FirstentCU,
FloridaCU, FNBO, FourLeafFCU, GlobalCU, GoldenwestCU, GrowFinancalFCU, GTE,
HarboreOne, Huntington, HVCU, Jeffersonfinancial, KFCU, Kinecta, Landmarkcu,
MACU, MaineStateCU, Members1st, MSUFCU, myoccu, NasaFCU, PacificCrestFCU,
Parkcommunity, Patelco, Pefcu, PSFCU, QualstarCU, Radiantcu, REVFCU,
RivermarkCCU, Santanderbank, SchoolsFirst, SkylaCU, Sunward, Synovus,
UnitusCCU, ValleyStrong, VantageWest, VeridianCU, WescomCU
```

## 📝 Поля товара (BruteBankItem)

**Основные:**
- `bank_name` (String 200)
- `category` (String 50): vcc/personal/business/crypto
- `attributes` (Text): AN:RN+INST YODLEE+INST FINICITY
- `exact_balance` (Float)
- `account_type` (String 20): CHECKING/SAVINGS/BUSINESS/MONEY MARKET

**Доступ (5 toggles):**
- `has_login_password` (Boolean)
- `has_account_routing` (Boolean)
- `has_holder_name_address` (Boolean)
- `has_additional_info` (Boolean)
- `has_docs` (Boolean)

**Данные:**
- `login` (String), `password` (String)
- `account_number` (String), `routing_number` (String)
- `holder_name` (String), `holder_address` (Text)
- `additional_info` (Text)
- `state` (String 10), `zip` (String 20)

**Цена:**
- `price` (Float)

**Служебные:**
- `seller_id`, `moderation_status`, `is_active`, `is_in_stock`
- `group_id` (BruteBankGroup), `raw_data`, `created_at`

## 🔄 Moderation Request

**Модель:** `BruteBankTypeRequest`

**Flow:**
```
1. Кнопка "📝 Request new bank"
2. Bank Name
3. Bank Code (auto-generate option)
4. Attributes (AN:RN+INST...)
5. Category (vcc/personal/business/crypto)
6. Save to DB → Admin review
```

**Поля:**
- `seller_id`, `requested_name`, `bank_code`, `attributes`
- `category`, `status`, `admin_note`, `created_at`, `resolved_at`

## 📄 Описание для покупателя

```
🔓 Chase | CHECKING

💰 Balance: $5,240.00
📍 Location: CA

✅ Data Included:
  • Login/Password: Yes
  • Account/Routing: Yes
  • Holder Name/Address: Yes
  • Additional Info: No
  • Documents: Yes

📦 Attributes: AN:RN+INST YODLEE
💵 Price: $85.00
```

## 📦 Bulk Format

```
BANK|LOGIN|PASS|AN|RN|BALANCE|STATE|NAME|ADDRESS|ZIP|price
Chase|user@email.com|pass123|123456789|021000021|5000|CA|John Doe|123 Main St|90210|85.00
```

**Auto-detect attributes** из непустых полей

---

# 3️⃣ CC/DEBIT (КРЕДИТНЫЕ КАРТЫ)

## 📋 Описание
Кредитные и дебетовые карты (NON-VBV support)

## 🗂 Категории

| Тип | Описание |
|-----|----------|
| CC | Кредитные карты |
| Debit | Дебетовые карты |

## 📝 Поля товара (SellerCCItem)

**Данные карты:**
- `card_number` (String 19)
- `exp_month` (Integer)
- `exp_year` (Integer)
- `cvv` (String 4)
- `card_brand` (String 20): Visa/Mastercard/Amex/Discover
- `card_type` (String 10): credit/debit
- `card_category` (String 20): Standard/Gold/Platinum...
- `is_non_vbv` (Boolean) - 3D-Secure bypass

**Данные держателя:**
- `first_name` (String 100)
- `last_name` (String 100)
- `billing_address` (Text)
- `billing_city` (String 100)
- `billing_state` (String 10)
- `billing_zip` (String 20)
- `billing_country` (String 2)
- `phone` (String 50)
- `email` (String 200)

**Цена:**
- `price` (Float)
- `non_vbv_price` (Float) - отдельная цена для NON-VBV

**Служебные:**
- `seller_id`, `moderation_status`, `is_active`, `is_in_stock`
- `raw_data`, `created_at`

## 📄 Описание для покупателя

```
💳 Visa Platinum | NON-VBV

****1234 | Exp: 12/2027 | CVV: 123

👤 Holder: John Doe
📍 Billing: Los Angeles, CA 90210, US
📞 Phone: +1-555-123-4567
📧 Email: john@email.com

💰 Price: $25.00 (NON-VBV: $35.00)
📦 Stock: 42 items
```

## 📦 Bulk Format

```
NUMBER|EXP_MM|EXP_YY|CVV|FNAME|LNAME|ADDRESS|CITY|STATE|ZIP|COUNTRY|NON_VBV
4111111111111111|12|27|123|John|Doe|123 Main St|Los Angeles|CA|90210|US|1
```

---

# 4️⃣ NFC

## 📋 Описание
Apple Pay, Google Pay и другие NFC платежи

## 🗂 Типы (3 вида)

| Тип | Описание |
|-----|----------|
| Apple Pay | NFC для Apple устройств |
| Google Pay | NFC для Android устройств |
| Other | Другие NFC платежи |

## 📝 Поля товара (SellerNFCItem)

**Основные:**
- `nfc_type` (String 20): apple_pay/google_pay/other
- `bank_name` (String 200)
- `balance` (Float)
- `country` (String 2): US/CA/GB/AU...
- `state` (String 10)
- `zip` (String 20)

**Файлы:**
- `data_file_path` (String 500) - .zip с NFC данными

**Цена:**
- `price` (Float)

**Служебные:**
- `seller_id`, `moderation_status`, `is_active`, `is_in_stock`
- `raw_data`, `created_at`

## 📄 Описание для покупателя

```
📱 Apple Pay | Chase

💰 Balance: $3,500
📍 Location: CA, 90210, US

📦 Data File: Included (.zip)
💵 Price: $120.00
```

---

# 5️⃣ OTP

## 📋 Описание
OTP карты с SMS доступом

## 🏦 Банки (20 банков)

```
Chase, Bank of America, Wells Fargo, Citi, US Bank, PNC Bank,
TD Bank, Capital One, Regions Bank, Truist, Fifth Third, KeyBank,
Huntington, Citizens Bank, M&T Bank, Ally Bank, SunTrust, BB&T,
Navy Federal CU, USAA
```

## 📝 Поля товара (SellerOTPItem)

**Основные:**
- `bank_name` (String 200)
- `balance` (Float)
- `state` (String 10)
- `zip` (String 20)

**SMS доступ:**
- `sms_in_chat` (Boolean) - пересылка OTP через чат
- `sms_file` (Boolean) - файл с доступом к SMS

**Fullz данные:**
- `has_fullz` (Boolean)
- `first_name` (String 100)
- `last_name` (String 100)
- `dob` (Date)
- `ssn` (String 20)
- `phone` (String 50)
- `email` (String 200)

**Файлы:**
- `access_file_path` (String 500)

**Цена:**
- `price` (Float)

**Служебные:**
- `seller_id`, `moderation_status`, `is_active`, `is_in_stock`
- `raw_data`, `created_at`

## 📄 Описание для покупателя

```
📲 OTP | Chase

💰 Balance: $2,800
📍 Location: FL, 33101

✅ SMS Access:
  • In Chat: Yes
  • File: No

👤 Fullz: Included
  • Name: John Doe
  • DOB: 01/15/1985
  • SSN: XXX-XX-1234
  • Phone: +1-555-123-4567
  • Email: john@email.com

💵 Price: $95.00
```

---

# 6️⃣ SELFREG CC

## 📋 Описание
Самозарегистрированные кредитные карты

## 🏦 Банки (12 банков)

```
Chase, Bank of America, Citi, Wells Fargo,
Capital One, Discover, American Express, US Bank,
PNC Bank, TD Bank, Barclays, Synchrony
```

## 🎴 Названия карт (по банкам)

**Chase (6 карт):**
```
Chase Freedom Unlimited, Chase Freedom Flex,
Chase Sapphire Preferred, Chase Sapphire Reserve,
Chase Ink Business Cash, Chase Ink Business Unlimited
```

**Bank of America (4 карты):**
```
Customized Cash Rewards, Unlimited Cash Rewards,
Travel Rewards, Premium Rewards
```

**Citi (5 карт):**
```
Citi Double Cash, Citi Custom Cash, Citi Premier,
Citi Rewards+, Citi Simplicity
```

**Wells Fargo (4 карты):**
```
Wells Fargo Active Cash, Wells Fargo Autograph,
Wells Fargo Reflect, Wells Fargo Attune
```

**Capital One (5 карт):**
```
Capital One Venture X, Capital One Venture,
Capital One Quicksilver, Capital One SavorOne, Capital One Savor
```

**Discover (4 карты):**
```
Discover it Cash Back, Discover it Miles,
Discover it Student Cash Back, Discover it Chrome
```

**American Express (5 карт):**
```
Amex Gold, Amex Platinum, Blue Cash Preferred,
Blue Cash Everyday, Amex Green
```

**US Bank (4 карты):**
```
US Bank Altitude Connect, US Bank Altitude Go,
US Bank Cash+, US Bank Shopper Cash Rewards
```

**PNC (3 карты):**
```
PNC Cash Rewards, PNC Points Visa, PNC Core Visa
```

**TD Bank (3 карты):**
```
TD Cash Credit Card, TD First Class Visa, TD Aeroplan Visa
```

**Barclays (3 карты):**
```
Barclays AAdvantage Aviator Red, Barclays Wyndham Rewards Earner,
Barclays JetBlue Plus
```

**Synchrony (3 карты):**
```
Synchrony Premier World Mastercard, Synchrony HOME Credit Card,
Synchrony Car Care
```

**ВСЕГО: 49 уникальных названий карт**

## 📝 Поля товара (SellerSelfregCCItem)

**Основные:**
- `bank_name` (String 200)
- `card_name` (String 300)
- `registration_date` (Date): MM/DD/YYYY
- `state` (String 10)
- `zip` (String 20)

**VCC:**
- `has_vcc` (Boolean)
- `vcc_limit` (Float)

**Доступ:**
- `email_access` (Boolean)
- `phone_access` (Boolean)
- `phone_days_remaining` (Integer)
- `phone_renewable` (Boolean)
- `phone_can_swap` (Boolean)

**Данные:**
- `credit_limit` (Float)
- `first_name` (String 100)
- `last_name` (String 100)
- `dob` (Date)
- `ssn` (String 20)
- `address` (Text)
- `phone` (String 50)
- `email` (String 200)

**Return Item:**
- `return_item_enabled` (Boolean)
- `return_days` (Integer)

**Цена:**
- `price` (Float)

**Служебные:**
- `seller_id`, `moderation_status`, `is_active`, `is_in_stock`
- `raw_data`, `created_at`

## 🔄 Moderation Request

**Модель:** `SelfregCCCategoryRequest`

**Flow:**
```
1. Кнопка "📝 Request new bank category"
2. Bank Name
3. Save to DB → Admin review
```

**Поля:**
- `seller_id`, `requested_name`
- `status`, `admin_note`, `created_at`, `resolved_at`

## 📄 Описание для покупателя

```
🏧 Selfreg CC | Chase | Chase Freedom Unlimited

📅 Registration: 02/20/2025
📍 Location: NY, 10001

💳 Credit Limit: $5,000
💳 VCC: Yes (Limit: $2,000)

✅ Access:
  • Email: Yes
  • Phone: Yes (30 days, renewable: Yes, swap: No)

👤 Holder: John Doe
📍 Address: 123 Main St, New York, NY 10001
📞 Phone: +1-555-123-4567
📧 Email: john@email.com

🔄 Return: Yes (7 days)
💵 Price: $150.00
```

---

# 7️⃣ ENROLLMENT

## 📋 Описание
Enrollment аккаунты на порталах

## 🌐 Порталы (12 порталов)

```
FDECS, Digital Card Service, MyCardInfo, Card Suite Light,
CardNav, FIREFIGHTERS, Coast Central, Web Access,
Card Suite, MyAccountAccess, CentreSuite (minik), Elan
```

## 🏦 Банки (20 банков)

```
Chase, Bank of America, Wells Fargo, Citi, US Bank, PNC Bank,
TD Bank, Capital One, Regions Bank, Truist, Fifth Third, KeyBank,
Huntington, Citizens Bank, M&T Bank, Ally Bank, Navy Federal CU, USAA,
Discover, American Express, Barclays, Synchrony
```

## 📝 Поля товара (SellerEnrollItem)

**Основные:**
- `enroll_category_id` (Integer) - ссылка на категорию
- `portal` (String 100)
- `bank_name` (String 120)
- `card_type` (String 20): credit/debit

**Данные карты:**
- `card_zip` (String 20)
- `card_state` (String 50)
- `balance` (Float)

**Персональные данные:**
- `first_name` (String 100)
- `last_name` (String 100)
- `dob` (Date)
- `ssn` (String 20)
- `address` (Text)
- `city` (String 100)
- `state` (String 10)
- `zip` (String 20)
- `phone` (String 50)
- `email` (String 200)

**Дополнительно:**
- `has_ssn` (Boolean)
- `has_dob` (Boolean)
- `has_address` (Boolean)
- `has_docs` (Boolean)
- `online_access` (Boolean)
- `additional_info` (Text)

**Файлы:**
- `data_file_path` (String 500)

**Цена:**
- `price` (Float)

**Служебные:**
- `seller_id`, `moderation_status`, `is_active`, `is_in_stock`
- `raw_data`, `created_at`

## 🔄 Moderation Request

**Модель:** `EnrollCategoryRequest`

**Flow:**
```
1. Кнопка "📝 Request new portal category"
2. Portal Name
3. Save to DB → Admin review
```

**Поля:**
- `seller_id`, `requested_name`
- `status`, `admin_note`, `created_at`, `resolved_at`

## 📄 Описание для покупателя

```
🔐 Enrollment | FDECS | Chase

💰 Balance: $4,200
📍 Card Location: CA, 90210

✅ Data Included:
  • SSN: Yes
  • DOB: Yes
  • Address: Yes
  • Docs: Yes
  • Online Access: Yes

👤 Full Personal Data:
  • Name: John Doe
  • DOB: 01/15/1985
  • SSN: XXX-XX-1234
  • Address: 123 Main St, Los Angeles, CA 90210
  • Phone: +1-555-123-4567
  • Email: john@email.com

💵 Price: $75.00
```

---

# 8️⃣ LOGS (ЛОГИ)

## 📋 Описание
Полные логи банков с всеми данными

## 📝 Поля товара (SellerLogsItem)

**Основные:**
- `bank` (String 100)
- `total_balance` (Float)
- `state` (String 10)

**Файлы:**
- `log_file_path` (String 500)

**Данные (toggles):**
- `has_cvv` (Boolean)
- `bt_available` (Boolean) - Bank Transfer
- `promo_available` (Boolean)
- `zelle_enroll` (Boolean)
- `wire_available` (Boolean)
- `safepass_unlocked` (Boolean)
- `email_valid` (Boolean)
- `has_cookies` (Boolean)
- `has_screenshot` (Boolean)

**Описание:**
- `description_en` (Text)

**Цена:**
- `price` (Float)

**Служебные:**
- `seller_id`, `moderation_status`, `is_active`, `is_in_stock`
- `raw_data`, `created_at`

## 📄 Описание для покупателя

```
📋 Logs | Chase

💰 Total Balance: $8,450
📍 Location: CA

✅ Data Included:
  • CVV: Yes
  • Bank Transfer: Yes
  • Promo Available: No
  • Zelle Enrolled: Yes
  • Wire Available: Yes
  • SafePass Unlocked: Yes
  • Email Valid: Yes
  • Cookies: Yes
  • Screenshot: Yes

📝 Description: Full logs with all access...
💵 Price: $200.00
```

## 📦 Bulk Format

```
LOGIN|PASS|AN|RN|BALANCE|STATE|ROUTING|NAME|ADDRESS|ZIP|CVV|ZELLE|WIRE|BT|PROMO|SAFEPASS|EMAIL|SCREENSHOT
user123|pass123|123456789|021000021|5000|CA|021000021|John Doe|123 Main St|90210|123|1|1|1|0|1|1|1
```

---

# 9️⃣ CHECKS (ЧЕКИ)

## 📋 Описание
Персональные, бизнес, payroll и cashier чеки

## 🗂 Типы чеков (4 вида)

| Тип | Описание |
|-----|----------|
| Personal | Персональные чеки |
| Business | Бизнес чеки |
| Payroll | Зарплатные чеки |
| Cashier | Кассирские чеки |

## 📝 Поля товара (SellerCheckItem)

**Основные:**
- `check_type` (String 20): personal/business/payroll/cashier
- `bank_name` (String 200)
- `amount` (Float)
- `state` (String 10)

**Файлы:**
- `scan_file_path` (String 500) - скан/фото чека
- `check_data_json` (Text) - данные чека

**Цена:**
- `price` (Float)

**Служебные:**
- `seller_id`, `moderation_status`, `is_active`, `is_in_stock`
- `raw_data`, `created_at`

## 📄 Описание для покупателя

```
🖊 Check | Personal | Chase

💰 Amount: $2,500.00
📍 Location: CA

📄 Scan: Included (.jpg)
💵 Price: $45.00
```

## 📦 ZIP Format

```
check_data.json + scan.jpg

check_data.json:
{
  "check_type": "personal",
  "amount": 2500.00,
  "has_holder_name": true,
  "bank_name": "Chase",
  "state": "CA"
}
```

---

# 🔟 DOCUMENTS (ДОКУМЕНТЫ)

## 📋 Описание
Документы: DL, паспорт, бизнес документы

## 🗂 Типы документов

| Тип | Описание |
|-----|----------|
| DL Front+Back | Водительские права (2 стороны) |
| DL+Selfie | Права + селфи |
| Passport | Паспорт |
| Business Docs | Бизнес документы |

## 📝 Поля товара (Product)

**Основные:**
- `category` (String 20): "docs"
- `service` (String 50): dl/dl_selfie/passport/business
- `state` (String 10)
- `quality` (String 20): standard/premium

**Опции:**
- `has_hologram` (Boolean)
- `has_selfie` (Boolean)

**Файлы:**
- `sample_file_path` (String 500)

**Цена:**
- `price` (Float)
- `markup_value` (Decimal) - наценка

**Служебные:**
- `seller_id`, `moderation_status`, `is_available`
- `status`, `created_at`, `approved_at`

## 📄 Описание для покупателя

```
📄 Documents | DL Front+Back | CA

✅ Quality: Premium
✅ Hologram: Yes
✅ Selfie: No

📦 Sample: Included
💵 Price: $35.00
```

---

# 1️⃣1️⃣ FULLZ

## 📋 Описание
Полные досье на людей (SSN, DOB, адрес и т.д.)

## 🗂 Типы Fullz

| Тип | Описание |
|-----|----------|
| Personal | Персональные Fullz |
| Business | Бизнес Fullz |

## 📝 Поля товара (SellerFullzItem)

**Основные:**
- `fullz_type` (String 20): personal/business
- `credit_score` (Integer): 300-850
- `age_range` (String 20): 18-25/25-35/35-50/50+
- `gender` (String 10): male/female

**Данные:**
- `ssn` (String 20)
- `dob` (Date)
- `first_name` (String 100)
- `last_name` (String 100)
- `address` (Text)
- `city` (String 100)
- `state` (String 10)
- `zip` (String 20)
- `phone` (String 50)
- `email` (String 200)

**Отчеты:**
- `report_group` (String 50): basic/cr/cr_dl/cr_dl_mvr/cr_dl_full_mvr

**Цена:**
- `price` (Float)

**Служебные:**
- `seller_id`, `moderation_status`, `is_active`, `is_in_stock`
- `raw_data`, `created_at`

## 📄 Описание для покупателя

```
📦 Fullz | Personal

👤 Profile:
  • Name: John Doe
  • SSN: XXX-XX-1234
  • DOB: 01/15/1985 (Age: 35-50)
  • Gender: Male
  • Credit Score: 720

📍 Address: 123 Main St, Los Angeles, CA 90210
📞 Phone: +1-555-123-4567
📧 Email: john@email.com

📊 Report Group: CR+DL+MVR
💵 Price: $25.00
```

---

# 📚 СПРАВОЧНИКИ И КАТЕГОРИИ

## CC Categories (Динамические из БД)

**Структура:**
```python
class CCCategory(Base):
    code: String(80)  # unique
    name: String(200)
    position: Integer
    is_active: Boolean
    is_custom: Boolean  # добавлена пользователем
```

## Enroll Categories (12 порталов)

**Структура:**
```python
class EnrollCategory(Base):
    code: String(80)  # unique
    name: String(200)
    position: Integer
    is_active: Boolean
    is_custom: Boolean
```

## Brute Bank Groups (67 банков)

**Структура:**
```python
class BruteBankGroup(Base):
    group_key: String(220)  # unique
    bank_code: String(100)
    bank_name: String(200)
    category: String(50)  # vcc/personal/business/crypto
    attributes: Text  # AN:RN+INST YODLEE...
    position: Integer
    is_active: Boolean
```

---

# 🔄 ТАБЛИЦА ПРЕОБРАЗОВАНИЙ ДАННЫХ

| Поле | Mini App | Bot | DB | Преобразование |
|------|----------|-----|-----|----------------|
| `registration_date` | "MM/DD/YYYY" | "MM/DD/YYYY" | date | strptime("%m/%d/%Y") |
| `dob` | "MM/DD/YYYY" | "MM/DD/YYYY" | date | strptime("%m/%d/%Y") |
| `email_access` | "true"/"false" | True/False | bool | value.lower()=="true" |
| `phone_access` | "true"/"false" | True/False | bool | value.lower()=="true" |
| `has_ssn` | "true"/"false" | True/False | bool | value.lower()=="true" |
| `price` | "15.00" | "15.00" | float | float(value) |
| `balance` | "$5,000" | "5000" | float | replace("$","").replace(",","") |
| `category` | "vcc" | "vcc" | String(20) | ✅ |
| `bank_id` | "vcc_chime" | "vcc_chime" | String(50) | ✅ |
| `product_type` | "Virtual Card" | "Virtual Card" | String(100) | ✅ |
| `state` | "CA" | "CA" | String(10) | ✅ |
| `zip` | "90210" | "90210" | String(20) | ✅ |
| `country` | "US" | "US" | String(2) | ✅ |

---

# 📄 ОПИСАНИЯ ТОВАРОВ (ФОРМАТЫ)

## Banks Description Template

```python
def render_bank_description(item):
    return f"""
🏦 {item.bank_name} | {item.category}

📋 Product Type: {item.product_type}
📅 Registration: {item.registration_date}
📍 Location: {item.state}, {item.zip}

✅ Access:
  • Email: {'Yes' if item.email_access else 'No'}
  • Phone: {'Yes' if item.has_phone else 'No'} ({item.phone_days_remaining} days)
  • SSN: {'Yes' if item.has_ssn else 'No'}
  • Docs: {'Yes' if item.has_docs else 'No'}

💰 Price: ${item.price:.2f}
🔄 Return: {'Yes' if item.return_item_enabled else 'No'} ({item.return_days} days)

📦 Stock: {item.stock_count} items
"""
```

## CC Description Template

```python
def render_cc_description(item):
    return f"""
💳 {item.card_brand} {item.card_category} | {'NON-VBV' if item.is_non_vbv else 'VBV'}

****{item.card_number[-4:]} | Exp: {item.exp_month:02d}/{item.exp_year} | CVV: {item.cvv}

👤 Holder: {item.first_name} {item.last_name}
📍 Billing: {item.billing_city}, {item.billing_state} {item.billing_zip}, {item.billing_country}
📞 Phone: {item.phone}
📧 Email: {item.email}

💰 Price: ${item.price:.2f}{' (NON-VBV: $' + str(item.non_vbv_price) + ')' if item.is_non_vbv else ''}
📦 Stock: {item.stock_count} items
"""
```

## NFC Description Template

```python
def render_nfc_description(item):
    return f"""
📱 {item.nfc_type} | {item.bank_name}

💰 Balance: ${item.balance:.0f}
📍 Location: {item.state}, {item.zip}, {item.country}

📦 Data File: Included (.zip)
💵 Price: ${item.price:.2f}
"""
```

## OTP Description Template

```python
def render_otp_description(item):
    return f"""
📲 OTP | {item.bank_name}

💰 Balance: ${item.balance:.0f}
📍 Location: {item.state}, {item.zip}

✅ SMS Access:
  • In Chat: {'Yes' if item.sms_in_chat else 'No'}
  • File: {'Yes' if item.sms_file else 'No'}

{'👤 Fullz: Included' if item.has_fullz else ''}
💵 Price: ${item.price:.2f}
"""
```

## Check Description Template

```python
def render_check_description(item):
    return f"""
🖊 Check | {item.check_type} | {item.bank_name}

💰 Amount: ${item.amount:.2f}
📍 Location: {item.state}

📄 Scan: Included
💵 Price: ${item.price:.2f}
"""
```

---

# ✅ ИТОГОВАЯ ТАБЛИЦА

| Раздел | Статус | Категорий | Банков | Полей | Moderation Request |
|--------|--------|-----------|--------|-------|-------------------|
| Banks | ✅ | 5 | 51 | 20 | ✅ |
| Brute Bank | ✅ | 1 | 67 | 15 | ✅ |
| CC/Debit | ✅ | 2 | BIN | 18 | ❌ |
| NFC | ✅ | 3 | 20 | 12 | ❌ |
| OTP | ✅ | 1 | 20 | 14 | ❌ |
| Selfreg CC | ✅ | 1 | 12 | 16 | ✅ |
| Enrollment | ✅ | 12 | 20 | 20 | ✅ |
| Logs | ✅ | 1 | 20 | 22 | ❌ |
| Checks | ✅ | 4 | 20 | 10 | ❌ |
| Documents | ✅ | 4 | - | 12 | ❌ |
| Fullz | ✅ | 2 | - | 15 | ❌ |
| ~~Selfreg BA~~ | ❌ | - | - | - | ❌ |

**ВСЕГО: 11 активных разделов**

---

**ВЕРСИЯ:** 2.0  
**ДАТА:** 2026-03-24  
**СТАТУС:** ✅ Полный аудит завершен