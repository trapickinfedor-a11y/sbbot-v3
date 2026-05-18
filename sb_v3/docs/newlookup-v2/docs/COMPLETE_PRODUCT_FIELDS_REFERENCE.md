# Полный справочник полей и данных — Все типы товаров

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
10. [Сводная таблица: Кто загружает](#10-сводная-таблица-кто-загружает)
11. [Что видит клиент — Краткая сводка](#11-что-видит-клиент--краткая-сводка)
12. [Краткая таблица: Что видит клиент](#12-краткая-таблица-что-видит-клиент)
13. [Общие принципы обработки данных](#13-общие-принципы-обработки-данных)
14. [API эндпоинты для модерации](#14-api-эндпоинты-для-модерации)

---

## 1. CC (Credit Cards)

### 1.1 Что принимает бот от Seller

**Формат загрузки (bulk/single):**
```
NUMBER|EXP|CVV|TYPE|BRAND|LVL|BANK|COUNTRY|HOLDER|ADDR|STATE|CITY|ZIP|Info|REF|PRICE
```

**Обязательные поля:**
- `NUMBER` — номер карты (≥12 цифр)
- `EXP` — срок действия (MM/YY или MMYY)
- `CVV` — CVV код (3-4 цифры)

**Опциональные поля:**
- `TYPE` — тип карты (CREDIT/DEBIT/PREPAID)
- `BRAND` — бренд (Visa/Mastercard/Amex/Discover)
- `LVL` — уровень (Classic/Gold/Platinum/Signature)
- `BANK` — название банка
- `COUNTRY` — код страны (US/GB/CA и т.д.)
- `HOLDER` — имя держателя
- `ADDR` — адрес
- `STATE` — штат (2 буквы)
- `CITY` — город
- `ZIP` — почтовый индекс
- `Info` — дополнительная информация
- `REF` — референс
- `PRICE` — цена seller (USD)

**Дополнительные параметры:**
- `phone` — телефон
- `email` — email
- `ssn` — SSN
- `dob` — дата рождения
- `dl` — driver license

**Выбор категории:**
- USA CC (`category_code = "usa"`)
- World CC (`category_code = "world"`)
- NON VBV (флаг `is_non_vbv = True`)

### 1.2 Обработка данных

**Парсинг:**
```python
# Функция: parse_cc_line_flexible()
# Файл: shared/services/seller_upload_pipeline_service.py

1. Разделение строки по "|"
2. Извлечение NUMBER, EXP, CVV (обязательные)
3. Валидация:
   - NUMBER: ≥12 цифр, проходит Luhn check
   - EXP: валидная дата (не истекла)
   - CVV: 3-4 цифры
4. Извлечение опциональных полей
5. Парсинг PRICE (если есть)
```

**🆕 BIN Auto-Enrichment:**
```python
# Функция: BinLookupService.enrich_parsed()
# Файл: shared/services/bin_lookup_service.py

1. Извлечение BIN (первые 6 цифр)
2. Запрос к binlist.net API
3. Автозаполнение пустых полей:
   - TYPE → CREDIT/DEBIT/PREPAID
   - BRAND → Visa/Mastercard/Amex/Discover
   - LVL → Classic/Gold/Platinum/Signature
   - BANK → название банка
   - COUNTRY → код страны
4. Кэширование (LRU, 2000 записей, TTL 24ч)
5. Rate limiting (250ms между запросами)
```

### 1.3 Хранение в БД

**Модель:** `SellerCCItem`  
**Таблица:** `seller_cc_items`

**Поля:**

| Поле | Тип | Источник | Обязательное |
|------|-----|----------|--------------|
| `id` | Integer | Auto | ✅ |
| `seller_id` | Integer | FK → sellers | ✅ |
| `category_code` | String(50) | Выбор seller | ✅ |
| `number` | String(255) | Encrypted | ✅ |
| `exp` | String(10) | Encrypted | ✅ |
| `cvv` | String(10) | Encrypted | ✅ |
| `card_bin` | String(6) | Первые 6 цифр NUMBER | ✅ |
| `card_brand` | String(50) | Seller или BIN lookup | ❌ |
| `card_level` | String(50) | Seller или BIN lookup | ❌ |
| `card_type` | String(20) | Seller или BIN lookup | ❌ |
| `bank_name` | String(255) | Seller или BIN lookup | ❌ |
| `country` | String(10) | Seller или BIN lookup | ❌ |
| `state` | String(10) | Seller input | ❌ |
| `city` | String(100) | Seller input | ❌ |
| `zip` | String(20) | Seller input | ❌ |
| `address` | String(500) | Seller input | ❌ |
| `fname` | String(100) | Из HOLDER | ❌ |
| `lname` | String(100) | Из HOLDER | ❌ |
| `is_non_vbv` | Boolean | Флаг NON VBV | ✅ (default: False) |
| `seller_price` | Decimal(10,2) | Seller input | ✅ |
| `buyer_price` | Decimal(10,2) | После модерации | ✅ |
| `moderation_status` | String(50) | pending_moderation | ✅ |
| `is_active` | Boolean | True | ✅ |
| `extra_data` | JSON | Доп. поля | ❌ |
| `created_at` | DateTime | Auto | ✅ |

**extra_data содержит:**
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

### 1.4 Модерация

**Статусы:**
- `pending_moderation` — ожидает проверки
- `approved` — одобрено
- `rejected` — отклонено

**Процесс:**
1. Admin просматривает все поля в support_bot или web_panel
2. Применяет markup → пересчитывает `buyer_price`
3. Одобряет → `moderation_status = "approved"`
4. Товар появляется в каталоге покупателя

**🆕 Фильтры модерации:**
- Поиск по BIN (префикс)
- Поиск по bank_name
- Фильтр по card_brand (Visa/Mastercard/Amex/Discover)
- Фильтр по card_type (CREDIT/DEBIT/PREPAID)

### 1.5 Распределение по категориям у покупателя

**Категории:**
1. 🇺🇸 USA CC (`category_code = "usa"`)
2. 🌍 ALL WORLD CC (`category_code = "world"`)
3. 🔓 NON VBV (виртуальная, `is_non_vbv = True`)

**Логика фильтрации:**
```python
# Функция: get_cc_items_for_category()
# Файл: shared/cc_catalog.py

# Базовые условия (всегда):
- SellerCCItem.is_active == True
- SellerCCItem.moderation_status == "approved"
- Seller.is_approved == True
- Seller.is_active == True

# По категории:
if category_code == "non_vbv":
    # Все карты с флагом NON VBV
    SellerCCItem.is_non_vbv == True
else:
    # Карты из конкретной категории
    SellerCCItem.category_code == category_code
```

**Дополнительные фильтры:**
- **BIN search:** `card_bin.startswith(query)` или `number.startswith(query)`
- **ZIP search:** `zip.ilike(f"%{query}%")`
- **Сортировка:** по `buyer_price` (↑ или ↓)

**Пагинация:** 10 items/page

**Важно:** Если карта имеет флаг `is_non_vbv = True`, она появляется ТОЛЬКО в категории NON VBV, независимо от `category_code`.

```
Пример:
- category_code = "usa"
- is_non_vbv = True

Появится ТОЛЬКО в:
🔓 NON VBV

Если is_non_vbv = False:
Появится в категории по category_code (🇺🇸 USA CC или 🌍 World CC)
```

### 1.6 Что отдает бот покупателю

**Кнопка в каталоге:**
```
{BIN} {card_brand} ***{last4} {zip_mark} | ${buyer_price:.2f}
```

**zip_mark:**
- `📍` — если есть ZIP
- `` — если нет ZIP

**Пример:**
```
443264 Visa ***1234 📍 | $45.00
512345 Mastercard ***5678 | $52.50
378282 Amex ***9012 📍 | $65.00
```

**Доступные фильтры для поиска:**
- BIN prefix (первые 6 цифр)
- ZIP code
- Сортировка по цене (↑ ↓)

**Генерация:**
```python
# Файл: shared/cc_catalog.py, lines 102-109
last4 = num[-4:] if len(num) >= 4 else ""
bank = (s.bank_name or "")[:20]
brand = (s.card_brand or "")[:16]
btn = f"{bank} {brand} ***{last4} | ${float(s.buyer_price):.2f}"[:64]
```

**Описание товара:**
```
💳 {card_brand} {BIN} — {bank_name}
━━━━━━━━━━━━━━━━━━━
BIN: {BIN} | Exp: {exp}
Type: {card_type} {card_level} | NON-VBV: {✅/❌}
Country: {flag} {country} | State: {state} | ZIP: {zip}
Address: {address}, {city}
Holder: {fname} {lname}
Phone: {phone}
Email: {email}
SSN: {ssn}
DOB: {dob}
Info: {info}
Ref: {ref}
━━━━━━━━━━━━━━━━━━━
```

**Генерация:**
```python
# Функция: render_cc_description()
# Файл: shared/utils/seller_card_renderers.py

# Приоритет данных:
1. Прямые поля модели (item.bank_name, item.card_brand, ...)
2. extra_data JSON (extra.get("bank"), extra.get("brand"), ...)
3. Дефолт "—" если нигде нет
```

**Таблица источников данных:**

| Параметр | Модель | extra_data | BIN Lookup | Приоритет |
|----------|--------|------------|------------|-----------|
| BIN | number[:6] | bin | ✅ | Модель → extra → BIN |
| Exp | exp | exp | ❌ | Модель → extra |
| Type | card_type | card_type | ✅ | Модель → extra → BIN |
| Brand | card_brand | brand | ✅ | Модель → extra → BIN |
| Level | card_level | level | ✅ | Модель → extra → BIN |
| Bank | bank_name | bank | ✅ | Модель → extra → BIN |
| Country | country | country | ✅ | Модель → extra → BIN |
| State | state | — | ❌ | Модель |
| ZIP | zip | — | ❌ | Модель |
| Address | address | — | ❌ | Модель |
| City | city | — | ❌ | Модель |
| Holder | fname+lname | holder | ❌ | Модель → extra |
| Phone | — | phone | ❌ | extra |
| Email | — | email | ❌ | extra |
| SSN | — | ssn | ❌ | extra |
| DOB | — | dob | ❌ | extra |
| DL | — | dl | ❌ | extra |
| Info | — | info | ❌ | extra |
| Ref | — | ref | ❌ | extra |
| NON-VBV | is_non_vbv | — | ❌ | Модель |

### 1.7 После покупки (Reveal)

**Что показывается:**
```
🎉 Your CC Purchase

💳 Full Card Data:
━━━━━━━━━━━━━━━━━━━
Number: {full_number}
Exp: {exp}
CVV: {cvv}
━━━━━━━━━━━━━━━━━━━

{полное описание из 1.6}

━━━━━━━━━━━━━━━━━━━
💰 Paid: ${buyer_price}
```

**Создается запись:**
- Модель: `SellerCCOrder`
- Статус: `completed`
- Seller получает уведомление о продаже

---

## 2. Bank Selfregs

### 2.1 Что принимает бот от Seller

**Формат загрузки (ZIP файл):**
```
bank_name/
  ├── account1/
  │   ├── credentials.txt (LOGIN|PASS|ACCOUNT_NUMBER|ROUTING)
  │   └── config.json
  └── account2/
      ├── credentials.txt
      └── config.json
```

**config.json:**
```json
{
  "bank_name": "Chase",
  "registration_date": "2024-01-15",
  "state": "NY",
  "zip": "10001",
  "has_phone": true,
  "phone_days_remaining": 30,
  "phone_renewable": true,
  "has_email": true,
  "email_access": true,
  "has_ssn": true,
  "has_docs": false,
  "online_access": true,
  "price": "145.00"
}
```

**Обязательные поля:**
- `bank_name` — название банка
- `registration_date` — дата регистрации аккаунта
- `state` — штат (2 буквы)
- `zip` — почтовый индекс
- `price` — цена seller (USD)

**Опциональные поля:**
- `has_phone` — есть телефон (yes/no)
- `phone_days_remaining` — дней осталось на телефоне
- `phone_renewable` — телефон продлеваемый (yes/no)
- `has_email` — есть email (yes/no)
- `email_access` — доступ к email (yes/no)
- `has_ssn` — есть SSN (yes/no)
- `has_docs` — есть документы (yes/no)
- `online_access` — онлайн доступ (yes/no)

**Примечание:** Баланс всегда 0 (новые аккаунты)

### 2.2 Хранение в БД

**Модель:** `SellerBankSelfregItem`  
**Таблица:** `seller_bank_selfreg_items`

**Основные поля:**

| Поле | Тип | Обязательное |
|------|-----|--------------|
| `id` | Integer | ✅ |
| `seller_id` | Integer | ✅ |
| `bank_name` | String(120) | ✅ |
| `registration_date` | Date | ✅ |
| `state` | String(10) | ✅ |
| `zip` | String(20) | ✅ |
| `has_phone` | Boolean | ✅ (default: False) |
| `phone_days_remaining` | Integer | ❌ |
| `phone_renewable` | Boolean | ❌ |
| `has_email` | Boolean | ✅ (default: False) |
| `email_access` | Boolean | ✅ (default: False) |
| `has_ssn` | Boolean | ✅ (default: False) |
| `has_docs` | Boolean | ✅ (default: False) |
| `online_access` | Boolean | ✅ (default: True) |
| `credentials_file_path` | String(500) | ✅ |
| `seller_price` | Decimal(10,2) | ✅ |
| `buyer_price` | Decimal(10,2) | ✅ |
| `moderation_status` | String(30) | ✅ |

### 2.3 Распределение по категориям у покупателя

**Группировка:** по bank_name

**Пагинация:** 15 banks/page

### 2.4 Что отдает бот покупателю

**Кнопка банка:**
```
{bank_name} [{count}]
```

**Пример:**
```
Chase [12]
Wells Fargo [8]
Bank of America [15]
```

**Кнопка товара:**
```
{bank_name} {state} 📍{zip} | ${buyer_price:.2f}
```

**Пример:**
```
Chase NY 📍10001 | $145.00
Wells Fargo CA 📍90210 | $165.00
```

**Описание товара:**
```
🏦 {bank_name} — Bank Selfreg
━━━━━━━━━━━━━━━━━━━
📅 Registered: {registration_date}
📍 State: {state} | ZIP: {zip}
━━━━━━━━━━━━━━━━━━━
📱 Phone: ✅ Active — {phone_days_remaining} days left / ❌
   Renewable: ✅/❌
📧 Email: ✅ | Access: ✅/❌
📋 SSN: ✅/❌ | Docs: ✅/❌
🌐 Online Access: ✅/❌
━━━━━━━━━━━━━━━━━━━
💰 Price: ${buyer_price}
```

---

## 3. Brute Bank

### 3.1 Что принимает бот от Seller

**Формат загрузки (ZIP файл):**
```
bank_name/
  ├── variant1/
  │   ├── combo.txt (LOGIN:PASS)
  │   └── config.json
  └── variant2/
      ├── combo.txt
      └── config.json
```

**config.json:**
```json
{
  "balance_range": "$1K-$5K",
  "account_type": "CHECKING",
  "price": "25.00"
}
```

**Обязательные поля:**
- `bank_name` — название банка (из структуры папок)
- `balance_range` — диапазон баланса
- `account_type` — тип аккаунта (CHECKING/SAVINGS/BUSINESS/MONEY MARKET)
- `price` — цена за 1 combo
- `combo.txt` — файл с логинами и паролями

### 3.2 Обработка данных

**Парсинг:**
```python
# Функция: create_brute_batch()
# Файл: shared/services/seller_upload_pipeline_service.py

1. Распаковка ZIP
2. Обход папок (bank_name/variant/)
3. Чтение config.json
4. Подсчет строк в combo.txt
5. Создание group_key для группировки вариантов
6. Валидация:
   - account_type в VALID_ACCOUNT_TYPES
   - price > 0
   - combo.txt не пустой
```

**group_key:**
```python
# Функция: make_brute_group_key()
# Файл: shared/brute_bank_group_key.py

# Формат: {slugified_bank_name}
# Используется для группировки вариантов одного банка
```

### 3.3 Хранение в БД

**Модели:**
1. `BruteBankGroup` — группа вариантов одного банка
2. `BruteBankItem` — отдельный combo

**Таблица:** `brute_bank_groups`, `brute_bank_items`

**BruteBankGroup:**

| Поле | Тип | Источник | Обязательное |
|------|-----|----------|--------------|
| `id` | Integer | Auto | ✅ |
| `seller_id` | Integer | FK → sellers | ✅ |
| `group_key` | String(100) | Auto-generated | ✅ |
| `bank_name` | String(255) | Из структуры ZIP | ✅ |
| `balance_range` | String(100) | config.json | ✅ |
| `account_type` | String(50) | config.json | ✅ |
| `display_price` | Decimal(10,2) | config.json | ✅ |
| `moderation_status` | String(50) | pending_moderation | ✅ |
| `is_active` | Boolean | True | ✅ |

**BruteBankItem:**

| Поле | Тип | Источник | Обязательное |
|------|-----|----------|--------------|
| `id` | Integer | Auto | ✅ |
| `group_id` | Integer | FK → brute_bank_groups | ✅ |
| `login` | String(255) | Encrypted | ✅ |
| `password` | String(255) | Encrypted | ✅ |
| `is_sold` | Boolean | False | ✅ |

### 3.4 Модерация

**Процесс:** аналогичен CC, но модерируется вся группа целиком

### 3.5 Распределение по категориям у покупателя

**Категории:** нет, все в одном списке

**Фильтры:**
- Поиск по bank_name
- Фильтр A-Z (первая буква)

**Логика:**
```python
# Файл: mirror_bot/handlers/brute_bank.py

# Группировка по group_key
SELECT group_key, bank_name, COUNT(items) as quantity
FROM brute_bank_groups
JOIN brute_bank_items ON group_id = groups.id
WHERE is_active = True
  AND moderation_status = "approved"
  AND items.is_sold = False
GROUP BY group_key
```

**Пагинация:** 12 groups/page

### 3.6 Что отдает бот покупателю

**Кнопка банка:**
```
{bank_name} [{total_quantity}]
```

**Пример:**
```
Chase [245]
Wells Fargo [189]
```

**Кнопка варианта:**
```
{balance_range} {account_type} | ${display_price:.2f} [{quantity}]
```

**Пример:**
```
$1K-$5K CHECKING | $25.00 [45]
$5K-$10K SAVINGS | $35.00 [28]
```

**Описание:**
```
🏦 {bank_name} — Brute Bank
━━━━━━━━━━━━━━━━━━━
💰 Balance Range: {balance_range}
📊 Account Type: {account_type}
📦 Available: {quantity} combos
━━━━━━━━━━━━━━━━━━━
💰 Price per combo: ${display_price}
```

**Кнопка покупки:**
```
⚡ Buy Now | ${price:.2f}
```

---

## 4. Selfreg CC

### 4.1 Что принимает бот от Seller

**Выбор категории:**
- Предзагруженные: CITI, Chase, Wells Fargo, ONEPAY, BOA
- Seller может запросить новую категорию (модерация 1-6 часов)

**Обязательные поля:**
- `bank_name` — название банка
- `seller_price` — цена (USD)

**Опциональные поля:**
- `card_name` — название карты
- `credit_limit` — кредитный лимит (USD)
- `vcc_limit` — VCC лимит (USD)
- `state` — штат (2 буквы)
- `zip` — почтовый индекс
- `has_email` — есть email (yes/no)
- `has_phone` — есть телефон (yes/no)
- `phone_days_remaining` — дней осталось на телефоне
- `phone_renewable` — телефон продлеваемый (yes/no)
- `phone_change_allowed` — можно сменить телефон (yes/no)
- `online_access` — онлайн доступ (yes/no)

### 4.2 Хранение в БД

**Модель:** `SellerSelfregCCItem`  
**Таблица:** `seller_selfreg_cc_items`

**Основные поля:**

| Поле | Тип | Обязательное |
|------|-----|--------------|
| `id` | Integer | ✅ |
| `seller_id` | Integer | ✅ |
| `selfreg_cc_category_id` | Integer | ❌ |
| `item_name` | String(200) | ✅ |
| `bank_name` | String(120) | ✅ |
| `card_name` | String(120) | ❌ |
| `credit_limit` | Decimal(10,2) | ❌ |
| `vcc_limit` | Decimal(10,2) | ❌ |
| `state` | String(50) | ❌ |
| `zip` | String(20) | ❌ |
| `has_email` | Boolean | ✅ (default: False) |
| `has_phone` | Boolean | ✅ (default: False) |
| `phone_days_remaining` | Integer | ❌ |
| `phone_renewable` | Boolean | ❌ |
| `phone_change_allowed` | Boolean | ❌ |
| `online_access` | Boolean | ✅ (default: False) |
| `seller_price` | Decimal(10,2) | ✅ |
| `buyer_price` | Decimal(10,2) | ✅ |
| `moderation_status` | String(30) | ✅ |

### 4.3 Распределение по категориям у покупателя

**Категории:** 8 шт/страница

**Кнопка категории:**
```
{category_name} [{count}]
```

**Пример:**
```
CITI [12]
Chase [8]
Wells Fargo [15]
```

**Внутри категории:** 15 items/page, все в одном списке

### 4.4 Что отдает бот покупателю

**Кнопка товара:**
```
{bank_name} {card_name} | ${buyer_price:.2f}
```

**Пример:**
```
Chase Sapphire | $125.00
CITI Double Cash | $95.00
```

**Описание:**
```
💳 {bank_name} — Selfreg CC
━━━━━━━━━━━━━━━━━━━
💰 Credit Limit: ${credit_limit:,.2f}
💳 VCC Limit: ${vcc_limit:,.2f}
📍 State: {state} | ZIP: {zip}
━━━━━━━━━━━━━━━━━━━
📧 Email: ✅/❌
📱 Phone: ✅ Active — {phone_days_remaining} days left / ❌
   Renewable: ✅/❌ | Change Allowed: ✅/❌
🌐 Online Access: ✅/❌
━━━━━━━━━━━━━━━━━━━
💰 Price: ${buyer_price}
```

---

## 5. NFC

### 5.1 Что принимает бот от Seller

**Выбор типа:**
- 🍎 Apple Pay (`nfc_type = "ap"`)
- 🤖 Google Pay (`nfc_type = "gp"`)
- 📎 Other (`nfc_type = "other"`)

**Обязательные поля:**
- `bank_name` — название банка
- `country` — код страны (US/GB/CA и т.д.)
- `seller_price` — цена (USD)
- `data_file` — файл с данными NFC

**Опциональные поля:**
- `state` — штат
- `zip` — почтовый индекс
- `description` — описание
- `instruction` — инструкция

### 5.2 Хранение в БД

**Модель:** `SellerNFCItem`  
**Таблица:** `seller_nfc_items`

**Основные поля:**

| Поле | Тип | Обязательное |
|------|-----|--------------|
| `id` | Integer | ✅ |
| `seller_id` | Integer | ✅ |
| `item_name` | String(200) | ✅ |
| `nfc_type` | String(10) | ✅ |
| `bank_name` | String(120) | ✅ |
| `country` | String(10) | ✅ |
| `state` | String(50) | ❌ |
| `zip` | String(20) | ❌ |
| `data_file_path` | String(500) | ✅ |
| `description` | Text | ❌ |
| `instruction` | Text | ❌ |
| `seller_price` | Decimal(10,2) | ✅ |
| `buyer_price` | Decimal(10,2) | ✅ |
| `moderation_status` | String(30) | ✅ |

### 5.3 Распределение по категориям у покупателю

**Категории:**
1. 🍎 Apple Pay
2. 🤖 Google Pay
3. 📎 Other NFC

**Пагинация:** 10 items/page

### 5.4 Что отдает бот покупателю

**Кнопка товара:**
```
{bank_name} {country} | ${buyer_price:.2f}
```

**Пример:**
```
Chase US | $35.00
Barclays GB | $42.00
```

**Описание:**
```
📱 {nfc_type_label} — {bank_name}
━━━━━━━━━━━━━━━━━━━
🌍 Country: {flag} {country}
📍 State: {state} | ZIP: {zip}
━━━━━━━━━━━━━━━━━━━
📝 {description}
━━━━━━━━━━━━━━━━━━━
💰 Price: ${buyer_price}
```

---

## 6. OTP

### 6.1 Что принимает бот от Seller

**Обязательные поля:**
- `bank_name` — название банка
- `balance` — баланс (USD)
- `sms_access_type` — тип доступа к SMS:
  - `seller_mediated` — через seller
  - `account_access` — прямой доступ к аккаунту
- `seller_price` — цена (USD)
- `data_file` — файл с данными доступа (credentials, phone info, etc)

**Опциональные поля:**
- `has_fullz` — есть fullz данные (yes/no)
- `description` — описание
- `instruction` — инструкция

### 6.2 Хранение в БД

**Модель:** `SellerOTPItem`  
**Таблица:** `seller_otp_items`

**Основные поля:**

| Поле | Тип | Обязательное |
|------|-----|--------------|
| `id` | Integer | ✅ |
| `seller_id` | Integer | ✅ |
| `item_name` | String(200) | ✅ |
| `bank_name` | String(120) | ✅ |
| `balance` | Decimal(10,2) | ✅ |
| `has_fullz` | Boolean | ✅ (default: False) |
| `sms_access_type` | String(30) | ✅ |
| `data_file_path` | String(500) | ✅ |
| `description` | Text | ❌ |
| `instruction` | Text | ❌ |
| `seller_price` | Decimal(10,2) | ✅ |
| `buyer_price` | Decimal(10,2) | ✅ |
| `moderation_status` | String(30) | ✅ |

### 6.3 Распределение по категориям у покупателя

**Категории:** нет, все в одном списке

**Пагинация:** 10 items/page

### 6.4 Что отдает бот покупателю

**Кнопка товара:**
```
{bank_name} ${balance:,.0f}{sms_hint} | ${buyer_price:.2f}
```

**sms_hint:**
- `seller_mediated` → " 👤"
- `account_access` → " 🔓"

**Пример:**
```
Chase $2,400 👤 | $45.00
Wells Fargo $5,000 🔓 | $65.00
```

**Описание:**
```
💳 {bank_name} — OTP Card
━━━━━━━━━━━━━━━━━━━
💰 Balance: ${balance:,.2f}
📱 SMS Access: {sms_access_label}
📋 Fullz: ✅/❌
━━━━━━━━━━━━━━━━━━━
📝 {description}
━━━━━━━━━━━━━━━━━━━
💰 Price: ${buyer_price}
```

**sms_access_label:**
- `seller_mediated` → "Via Seller (Mediated)"
- `account_access` → "Direct Account Access"

---

## 7. Enroll

### 7.1 Что принимает бот от Seller

**Выбор категории (portal):**
- Предзагруженные: FDECS, DIGITALCARDSERVICE, MYCARDINFO, CARD SUITE LIGHT, CardNav, FIREFIGHTERS, COAST CENTRAL, WEB ACCESS, Card Suite, Myaccountaccess, CENTRESUITE (minik)
- Seller может запросить новую категорию (модерация 1-6 часов)

**Обязательные поля:**
- `portal` — название портала (из категории)
- `bank_name` — название банка
- `balance` — баланс (USD)
- `card_zip` — ZIP код карты
- `card_state` — штат карты (2 буквы)
- `card_type` — тип карты (Credit/Debit)
- `seller_price` — цена (USD)
- `data_file` — файл с данными доступа (credentials, screenshots, etc)

**Опциональные поля (флаги yes/no):**
- `has_ssn` — есть SSN
- `has_dob` — есть DOB
- `has_address` — есть адрес
- `has_docs` — есть документы
- `online_access` — онлайн доступ

### 7.2 Хранение в БД

**Модель:** `SellerEnrollItem`  
**Таблица:** `seller_enroll_items`

**Основные поля:**

| Поле | Тип | Обязательное |
|------|-----|--------------|
| `id` | Integer | ✅ |
| `seller_id` | Integer | ✅ |
| `enroll_category_id` | Integer | ❌ |
| `portal` | String(100) | ✅ |
| `bank_name` | String(120) | ❌ |
| `card_zip` | String(20) | ❌ |
| `card_state` | String(50) | ❌ |
| `card_type` | String(20) | ❌ |
| `balance` | Float | ✅ |
| `data_file_path` | String(500) | ✅ |
| `has_ssn` | Boolean | ✅ (default: False) |
| `has_dob` | Boolean | ✅ (default: False) |
| `has_address` | Boolean | ✅ (default: False) |
| `has_docs` | Boolean | ✅ (default: False) |
| `online_access` | Boolean | ✅ (default: True) |
| `price` | Float | ✅ |
| `moderation_status` | String(20) | ✅ |

### 7.3 Распределение по категориям у покупателя

**Категории:** 12 шт/страница

**Кнопка категории:**
```
{portal_name} [{count}]
```

**Пример:**
```
FDECS [12]
DIGITALCARDSERVICE [8]
MYCARDINFO [15]
```

**Внутри категории:** 15 items/page, сортировка по цене

### 7.4 Что отдает бот покупателю

**Кнопка товара:**
```
{bank_name or portal} ${balance:,.0f} | ${price:.2f}
```

**Пример:**
```
Chase $2,400 | $45.00
Wells Fargo $5,000 | $65.00
```

**Описание:**
```
🔐 Enroll | {portal} | ${balance:,.0f}
━━━━━━━━━━━━━━━━━━━
📋 SSN: ✅/❌ | DOB: ✅/❌
🏠 Address: ✅/❌ | Docs: ✅/❌
🌐 Online Access: ✅/❌
━━━━━━━━━━━━━━━━━━━
💰 Price: ${price}
```

---

## 8. Logs

### 8.1 Что принимает бот от Seller

**Формат загрузки (файл .txt или .zip):**
```
SITE|LOGIN|PASS|COOKIES|BALANCE|STATE|ROUTING|NAME|...
```

**Обязательные поля:**
- `bank` — название банка
- `total_balance` — общий баланс (USD)
- `price` — цена (USD)
- `log_file` — файл с данными (credentials, cookies, screenshots)
- `description_en` — описание на английском языке

**Опциональные поля (флаги):**
- `has_cvv` — есть CVV
- `bt_available` — BT доступен
- `promo_available` — промо доступно
- `zelle_enroll` — Zelle подключен
- `wire_available` — Wire доступен
- `safepass_unlocked` — SafePass разблокирован
- `email_valid` — email валидный
- `has_cookies` — есть cookies
- `has_screenshot` — есть скриншот

### 8.2 Хранение в БД

**Модель:** `SellerLogsItem`  
**Таблица:** `seller_logs_items`

**Основные поля:**

| Поле | Тип | Обязательное |
|------|-----|--------------|
| `id` | Integer | ✅ |
| `seller_id` | Integer | ✅ |
| `bank` | String(100) | ✅ |
| `total_balance` | Float | ✅ |
| `log_file_path` | String(500) | ✅ |
| `description_en` | Text | ✅ |
| `has_cvv` | Boolean | ✅ (default: False) |
| `bt_available` | Boolean | ✅ (default: False) |
| `promo_available` | Boolean | ✅ (default: False) |
| `zelle_enroll` | Boolean | ✅ (default: False) |
| `wire_available` | Boolean | ✅ (default: False) |
| `safepass_unlocked` | Boolean | ✅ (default: False) |
| `email_valid` | Boolean | ✅ (default: False) |
| `has_cookies` | Boolean | ✅ (default: False) |
| `has_screenshot` | Boolean | ✅ (default: False) |
| `price` | Float | ✅ |
| `moderation_status` | String(20) | ✅ |
| `raw_data` | Text | ❌ |

### 8.3 Распределение по категориям у покупателя

**Категории:** нет, все в одном списке

**Фильтры по цене:**
- All
- $0-25
- $25-50
- $50-100
- $100+

**Пагинация:** 10 items/page, сортировка по цене

### 8.4 Что отдает бот покупателю

**Кнопка товара:**
```
{bank} | ${price:.2f}
```

**Пример:**
```
Chase | $35.00
Wells Fargo | $45.00
Bank of America | $55.00
```

**Описание:**
```
📋 {bank} — Bank Log
━━━━━━━━━━━━━━━━━━━
💰 Total balance: ${total_balance:,.2f}
━━━━━━━━━━━━━━━━━━━
🏷 Flags: {active_flags}
━━━━━━━━━━━━━━━━━━━
📧 Email Valid: ✅/❌
🍪 Cookies: ✅/❌ | Screenshot: ✅/❌
━━━━━━━━━━━━━━━━━━━
💰 Price: ${price}
```

**active_flags (показываются только если True):**
- CVV
- BT
- Promo
- Zelle
- Wire
- SafePass

---

## 9. Checks

### 9.1 Что принимает бот от Seller

**Выбор типа:**
- Personal
- Business
- Payroll
- Cashier

**Обязательные поля:**
- `check_type` — тип чека (из списка выше)
- `bank_name` — название банка
- `amount` — сумма чека (USD)
- `state` — штат (2 буквы)
- `seller_price` — цена (USD)
- `scan_file` — скан чека (изображение/документ)

**Опциональные поля:**
- `zip` — почтовый индекс
- `has_holder_name` — есть имя держателя (yes/no)
- `has_address` — есть адрес (yes/no)
- `check_date` — дата чека
- `seller_description` — описание от seller
- `template_file` — файл шаблона

### 9.2 Хранение в БД

**Модель:** `SellerCheckItem`  
**Таблица:** `seller_check_items`

**Основные поля:**

| Поле | Тип | Обязательное |
|------|-----|--------------|
| `id` | Integer | ✅ |
| `seller_id` | Integer | ✅ |
| `item_name` | String(200) | ✅ |
| `check_type` | String(30) | ✅ |
| `bank_name` | String(120) | ✅ |
| `amount` | Decimal(10,2) | ✅ |
| `state` | String(50) | ❌ |
| `zip` | String(20) | ❌ |
| `has_holder_name` | Boolean | ✅ (default: False) |
| `has_address` | Boolean | ✅ (default: False) |
| `check_date` | Date | ❌ |
| `seller_description` | Text | ❌ |
| `scan_file_path` | String(500) | ✅ |
| `template_file_path` | String(500) | ❌ |
| `seller_price` | Decimal(10,2) | ✅ |
| `buyer_price` | Decimal(10,2) | ✅ |
| `moderation_status` | String(30) | ✅ |

### 9.3 Распределение по категориям у покупателя

**Категории:**
1. Personal
2. Business
3. Payroll
4. Cashier

**Пагинация:** 10 items/page, сортировка по цене

### 9.4 Что отдает бот покупателю

**Кнопка типа:**
```
{type_label} [{count}]
```

**Пример:**
```
Personal [8]
Business [12]
Payroll [5]
```

**Кнопка товара:**
```
{item_name} | ${buyer_price:.2f}
```

**Пример:**
```
Chase Personal Check | $85.00
Wells Fargo Business Check | $125.00
```

**Описание:**
```
🖊 {bank_name} {check_type} Check
━━━━━━━━━━━━━━━━━━━
💰 Amount: ${amount:,.2f}
📍 State: {state} | ZIP: {zip}
👤 Holder: ✅/❌ | Address: ✅/❌
📅 Date: {check_date}
━━━━━━━━━━━━━━━━━━━
📄 Scan: ✅ | Template: ✅/❌
━━━━━━━━━━━━━━━━━━━
💰 Price: ${buyer_price}
```

---

## 10. Сводная таблица: Кто загружает

| Товар | Seller bot | Mini App |
|-------|-----------|----------|
| CC | ✅ | ✅ |
| Bank Selfregs | ✅ | ✅ |
| Brute Bank | ✅ | ✅ |
| Selfreg CC | ✅ | ✅ |
| NFC | ✅ | ❌ |
| OTP | ✅ | ❌ |
| Enroll | ✅ | ❌ |
| Logs | ✅ | ❌ |
| Checks | ✅ | ❌ |

---

## 11. Что видит клиент — Краткая сводка

### CC (Credit Cards)

**В списке товаров (кнопка):**
```
{BIN} {brand} ***{last4} {📍 если есть ZIP} | ${price}
```
Пример: `443264 Visa ***1234 📍 | $45.00`

**В описании товара:**
- BIN, Exp, Type, Level, NON-VBV badge
- Country, State, ZIP
- Address, City
- Holder name
- Phone, Email, SSN, DOB
- Info, Ref

---

### Bank Selfregs

**В списке товаров (кнопка):**
```
{bank} {state} 📍{zip} | ${price}
```
Пример: `Chase NY 📍10001 | $145.00`

**В описании товара:**
- Registration date
- State, ZIP
- Phone (days left, renewable)
- Email access
- SSN, Docs flags
- Online access

---

### Brute Bank

**В списке банков (кнопка):**
```
{bank} [{total_quantity}]
```
Пример: `Chase [245]`

**В списке вариантов (кнопка):**
```
{balance_range} {account_type} | ${price} [{quantity}]
```
Пример: `$1K-$5K CHECKING | $25.00 [45]`

**В описании товара:**
- Balance range
- Account type
- Available combos count
- Price per combo

---

### Selfreg CC

**В списке товаров (кнопка):**
```
{bank} {card_name} | ${price}
```
Пример: `Chase Sapphire | $125.00`

**В описании товара:**
- Credit limit
- VCC limit
- State, ZIP
- Email, Phone (days left, renewable, changeable)
- Online access

---

### NFC

**В списке товаров (кнопка):**
```
{bank} {country} | ${price}
```
Пример: `Chase US | $35.00`

**В описании товара:**
- NFC type (Apple Pay/Google Pay/Other)
- Country, State, ZIP
- Description
- Instruction

---

### OTP

**В списке товаров (кнопка):**
```
{bank} ${balance} {👤/🔓} | ${price}
```
Пример: `Chase $2,400 👤 | $45.00`

**В описании товара:**
- Balance
- SMS access type (Via Seller / Direct Access)
- Fullz flag
- Description
- Instruction

---

### Enroll

**В списке товаров (кнопка):**
```
{bank or portal} ${balance} | ${price}
```
Пример: `Chase $2,400 | $45.00`

**В описании товара:**
- Portal name
- Balance
- SSN, DOB, Address, Docs flags
- Online access

---

### Logs

**В списке товаров (кнопка):**
```
{bank} | ${price}
```
Пример: `Chase | $35.00`

**В описании товара:**
- Total balance
- Active flags (CVV, BT, Promo, Zelle, Wire, SafePass)
- Email valid
- Cookies, Screenshot flags
- English description

---

### Checks

**В списке товаров (кнопка):**
```
{item_name} | ${price}
```
Пример: `Chase Personal Check | $85.00`

**В описании товара:**
- Check type
- Amount
- State, ZIP
- Holder name, Address flags
- Date
- Scan, Template flags

---

### Selfreg BA

**В списке товаров (кнопка):**
```
{bank} | ${price}
```
Пример: `Chase | $145.00`

**В описании товара:**
- Balance
- State, ZIP
- Phone (days left)
- Email access
- SSN, Docs flags

---

## 12. Краткая таблица: Что видит клиент

| Тип товара | Кнопка в списке | Описание товара |
|------------|-----------------|-----------------|
| **CC** | `443264 Visa ***1234 📍 \| $45.00` | BIN, Exp, Type, Level, NON-VBV, Country, State, ZIP, Address, Holder, Phone, Email, SSN, DOB |
| **Bank Selfregs** | `Chase NY 📍10001 \| $145.00` | Registration date, State, ZIP, Phone (days/renewable), Email access, SSN, Docs, Online access |
| **Brute Bank** | `$1K-$5K CHECKING \| $25.00 [45]` | Balance range, Account type, Available combos, Price per combo |
| **Selfreg CC** | `Chase Sapphire \| $125.00` | Credit limit, VCC limit, State, ZIP, Email, Phone (days/renewable/changeable), Online access |
| **NFC** | `Chase US \| $35.00` | NFC type (Apple/Google/Other), Country, State, ZIP, Description, Instruction |
| **OTP** | `Chase $2,400 👤 \| $45.00` | Balance, SMS access type, Fullz flag, Description, Instruction |
| **Enroll** | `Chase $2,400 \| $45.00` | Portal name, Balance, SSN, DOB, Address, Docs flags, Online access |
| **Logs** | `Chase \| $35.00` | Total balance, Flags (CVV/BT/Promo/Zelle/Wire/SafePass), Email valid, Cookies, Screenshot, English description |
| **Checks** | `Chase Personal Check \| $85.00` | Check type, Amount, State, ZIP, Holder/Address flags, Date, Scan/Template |

**Легенда:**
- 📍 — есть ZIP код
- 👤 — SMS через seller
- 🔓 — прямой доступ к SMS

---

## 13. Общие принципы обработки данных

### 13.1 Модерация

**Все seller-загруженные товары проходят модерацию:**

1. **Статусы:**
   - `pending_moderation` — ожидает проверки
   - `approved` — одобрено
   - `rejected` — отклонено

2. **Процесс:**
   - Admin просматривает все поля
   - Применяет markup → пересчитывает `buyer_price`
   - Одобряет или отклоняет
   - Только одобренные товары появляются у покупателя

3. **Условия показа покупателю:**
   ```python
   - item.is_active == True
   - item.moderation_status == "approved"
   - seller.is_approved == True
   - seller.is_active == True
   ```

### 13.2 Ценообразование

**Формула:**
```python
buyer_price = seller_price + markup

# Markup может быть:
# 1. Процентный: markup = seller_price * (markup_percent / 100)
# 2. Фиксированный: markup = markup_fixed
# 3. Комбинированный
```

**Поля в БД:**
- `seller_price` — цена от seller
- `buyer_price` — цена для покупателя (после markup)
- `markup_percent` — процент наценки
- `markup_fixed` — фиксированная наценка
- `markup_code` — код наценки
- `markup_kind` — тип наценки
- `markup_value` — значение наценки

### 13.3 Стандартизация кнопок

**Единый формат для всех типов товаров:**
```
{title_info} | ${price:.2f}
```

**Примеры:**
- CC: `443264 Visa ***1234 📍 | $45.00`
- Bank Selfregs: `Chase NY 📍10001 | $145.00`
- Brute Bank: `$1K-$5K CHECKING | $25.00 [45]`
- OTP: `Chase $2,400 👤 | $45.00`
- NFC: `Chase US | $35.00`
- Enroll: `Chase $2,400 | $45.00`
- Logs: `Chase | $35.00`
- Checks: `Chase Personal Check | $85.00`
- Selfreg BA: `Chase | $145.00`

**Правила:**
- Цена всегда после `|`
- Формат цены: `$XX.XX` (2 знака после запятой)
- Максимальная длина кнопки: 64 символа

### 13.4 Пагинация

**Стандартные значения:**
- CC: 10 items/page
- Bank Selfregs: 15 banks/page
- Brute Bank: 12 groups/page
- Selfreg CC: 8 categories/page, 15 items/page внутри
- NFC: 10 items/page
- OTP: 10 items/page
- Enroll: 12 categories/page, 15 items/page внутри
- Logs: 10 items/page
- Checks: 10 items/page
- Selfreg BA: до 30 items

### 13.5 Шифрование чувствительных данных

**Поля, которые шифруются:**
- CC: `number`, `exp`, `cvv`
- Brute Bank: `login`, `password`
- Все товары: полные данные в `raw_data` или файлах

**Показываются покупателю только после покупки (Reveal)**

---

## 14. API эндпоинты для модерации

### 14.1 Support Bot

**Команды:**
- `/mod_cc` — модерация CC items
- `/mod_banks` — модерация Banks
- `/mod_brute` — модерация Brute Bank
- `/mod_nfc` — модерация NFC
- `/mod_otp` — модерация OTP
- `/mod_enroll` — модерация Enroll
- `/mod_logs` — модерация Logs
- `/mod_checks` — модерация Checks
- `/mod_selfreg_cc` — модерация Selfreg CC
- `/mod_selfreg_ba` — модерация Selfreg BA

**Фильтры (для CC):**
- Поиск по BIN
- Поиск по bank_name
- Фильтр по card_brand
- Фильтр по card_type

### 14.2 Web Panel

**Эндпоинты:**
- `GET /api/seller_moderation/list_pending_cc` — список CC на модерации
- `GET /api/seller_moderation/list_pending_banks` — список Banks
- `POST /api/seller_moderation/approve_cc` — одобрить CC
- `POST /api/seller_moderation/reject_cc` — отклонить CC

**Query параметры (для CC):**
- `status` — статус модерации
- `q` — текстовый поиск (BIN/bank/brand/type/name)
- `card_type` — фильтр по типу карты
- `card_brand` — фильтр по бренду

---

**Конец документа.**

