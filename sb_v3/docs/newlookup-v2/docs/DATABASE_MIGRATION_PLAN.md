# План миграции БД для синхронизации с Mini App v2

## Критические изменения (MUST HAVE)

### 1. Banks Section — Универсальная модель для всех банковских продуктов

**Решение:** Расширить `SellerBankSelfregItem` → переименовать в `SellerBankItem`

**Включает:**
- Bank Selfregs (оригинальная функциональность)
- Selfreg BA (объединено с Banks)
- VCC, Personal, Business, Crypto, Merchant категории

```python
class SellerBankItem(Base):
    """Универсальная модель для всех банковских продуктов"""
    __tablename__ = "seller_bank_items"
    
    # Существующие поля
    id: int
    seller_id: int
    bank_name: String(120)
    registration_date: Date
    state: String(10)
    zip: String(20)
    
    # НОВЫЕ поля
    category: String(20)  # vcc, personal, business, crypto, merchant
    bank_code: String(50)  # vcc_chime, pers_chase, etc.
    product_type: String(100)  # "Checking Account", "Virtual Card", etc.
    balance: Decimal(10,2)  # Было всегда 0, теперь может быть любое значение
    
    # Доступы (существующие)
    has_phone: Boolean
    phone_days_remaining: Integer
    phone_renewable: Boolean
    has_email: Boolean
    email_access: Boolean
    
    # НОВЫЕ поля для доступов
    phone_can_swap: Boolean  # Можно менять номер
    
    # НОВЫЕ поля для возврата
    return_item_enabled: Boolean  # Можно вернуть товар
    return_days: Integer  # Дней на возврат
    
    # Остальные поля
    has_ssn: Boolean
    has_docs: Boolean
    online_access: Boolean
    credentials_file_path: String(500)
    seller_price: Decimal(10,2)
    buyer_price: Decimal(10,2)
    moderation_status: String(30)
    is_active: Boolean
    created_at: DateTime
```

**Миграция:**
```sql
-- Переименовать таблицу
ALTER TABLE seller_bank_selfreg_items RENAME TO seller_bank_items;

-- Добавить новые поля
ALTER TABLE seller_bank_items ADD COLUMN category VARCHAR(20);
ALTER TABLE seller_bank_items ADD COLUMN bank_code VARCHAR(50);
ALTER TABLE seller_bank_items ADD COLUMN product_type VARCHAR(100);
ALTER TABLE seller_bank_items ADD COLUMN balance DECIMAL(10,2) DEFAULT 0;
ALTER TABLE seller_bank_items ADD COLUMN phone_can_swap BOOLEAN DEFAULT FALSE;
ALTER TABLE seller_bank_items ADD COLUMN return_item_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE seller_bank_items ADD COLUMN return_days INTEGER;

-- Обновить существующие записи (если есть)
UPDATE seller_bank_items SET category = 'personal' WHERE category IS NULL;
UPDATE seller_bank_items SET balance = 0 WHERE balance IS NULL;
```

---

### 2. Brute Bank — Расширение полей

```python
class BruteBankItem(Base):
    __tablename__ = "brute_bank_items"
    
    # Существующие
    id: int
    seller_id: int
    group_id: int
    login: String(255)  # encrypted
    password: String(255)  # encrypted
    is_sold: Boolean
    
    # НОВЫЕ поля
    exact_balance: String(50)  # "$4,820" - точный баланс
    account_number: String(255)  # encrypted
    routing_number: String(255)  # encrypted
    holder_name: String(200)
    address: String(500)
    state: String(10)
    zip: String(20)
    additional_info: Text
    has_docs: Boolean
    
    # Metadata
    created_at: DateTime
```

**Миграция:**
```sql
ALTER TABLE brute_bank_items ADD COLUMN exact_balance VARCHAR(50);
ALTER TABLE brute_bank_items ADD COLUMN account_number VARCHAR(255);  -- будет encrypted
ALTER TABLE brute_bank_items ADD COLUMN routing_number VARCHAR(255);  -- будет encrypted
ALTER TABLE brute_bank_items ADD COLUMN holder_name VARCHAR(200);
ALTER TABLE brute_bank_items ADD COLUMN address VARCHAR(500);
ALTER TABLE brute_bank_items ADD COLUMN state VARCHAR(10);
ALTER TABLE brute_bank_items ADD COLUMN zip VARCHAR(20);
ALTER TABLE brute_bank_items ADD COLUMN additional_info TEXT;
ALTER TABLE brute_bank_items ADD COLUMN has_docs BOOLEAN DEFAULT FALSE;
```

---

### 3. CC — Добавить NON VBV цену

```python
class SellerCCItem(Base):
    __tablename__ = "seller_cc_items"
    
    # Все существующие поля...
    
    # НОВОЕ поле
    seller_price_non_vbv: Decimal(10,2)  # Цена для NON VBV карт
    buyer_price_non_vbv: Decimal(10,2)   # Цена для покупателя (NON VBV)
```

**Миграция:**
```sql
ALTER TABLE seller_cc_items ADD COLUMN seller_price_non_vbv DECIMAL(10,2);
ALTER TABLE seller_cc_items ADD COLUMN buyer_price_non_vbv DECIMAL(10,2);

-- Установить дефолтные значения = обычной цене
UPDATE seller_cc_items 
SET seller_price_non_vbv = seller_price, 
    buyer_price_non_vbv = buyer_price 
WHERE seller_price_non_vbv IS NULL;
```

---

### 4. Selfreg CC — Расширение

```python
class SellerSelfregCCItem(Base):
    __tablename__ = "seller_selfreg_cc_items"
    
    # Существующие поля...
    
    # НОВЫЕ поля
    registration_date: Date  # Дата регистрации карты
    vcc_bin: String(6)  # BIN виртуальной карты
    return_item_enabled: Boolean
    return_days: Integer
```

**Миграция:**
```sql
ALTER TABLE seller_selfreg_cc_items ADD COLUMN registration_date DATE;
ALTER TABLE seller_selfreg_cc_items ADD COLUMN vcc_bin VARCHAR(6);
ALTER TABLE seller_selfreg_cc_items ADD COLUMN return_item_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE seller_selfreg_cc_items ADD COLUMN return_days INTEGER;
```

---

### 5. OTP — Расширение Fullz полей

```python
class SellerOTPItem(Base):
    __tablename__ = "seller_otp_items"
    
    # Существующие поля...
    
    # НОВЫЕ поля
    state: String(10)
    zip: String(20)
    
    # Fullz данные (можно в JSON или отдельные поля)
    fullz_data: JSON  # или отдельные поля ниже
    
    # Или отдельные поля:
    fullz_first_name: String(100)
    fullz_last_name: String(100)
    fullz_dob: Date
    fullz_ssn: String(20)  # encrypted
    fullz_address: String(500)
    fullz_city: String(100)
    fullz_state: String(10)
    fullz_zip: String(20)
    fullz_phone: String(50)
    fullz_email: String(200)
```

**Миграция (вариант с JSON):**
```sql
ALTER TABLE seller_otp_items ADD COLUMN state VARCHAR(10);
ALTER TABLE seller_otp_items ADD COLUMN zip VARCHAR(20);
ALTER TABLE seller_otp_items ADD COLUMN fullz_data JSON;
```

**Миграция (вариант с отдельными полями):**
```sql
ALTER TABLE seller_otp_items ADD COLUMN state VARCHAR(10);
ALTER TABLE seller_otp_items ADD COLUMN zip VARCHAR(20);
ALTER TABLE seller_otp_items ADD COLUMN fullz_first_name VARCHAR(100);
ALTER TABLE seller_otp_items ADD COLUMN fullz_last_name VARCHAR(100);
ALTER TABLE seller_otp_items ADD COLUMN fullz_dob DATE;
ALTER TABLE seller_otp_items ADD COLUMN fullz_ssn VARCHAR(20);  -- encrypted
ALTER TABLE seller_otp_items ADD COLUMN fullz_address VARCHAR(500);
ALTER TABLE seller_otp_items ADD COLUMN fullz_city VARCHAR(100);
ALTER TABLE seller_otp_items ADD COLUMN fullz_state VARCHAR(10);
ALTER TABLE seller_otp_items ADD COLUMN fullz_zip VARCHAR(20);
ALTER TABLE seller_otp_items ADD COLUMN fullz_phone VARCHAR(50);
ALTER TABLE seller_otp_items ADD COLUMN fullz_email VARCHAR(200);
```

---

### 6. Enrollment — Расширение полей

```python
class SellerEnrollItem(Base):
    __tablename__ = "seller_enroll_items"
    
    # Существующие поля...
    
    # НОВЫЕ поля
    first_name: String(100)
    last_name: String(100)
    dob: Date
    ssn: String(20)  # encrypted
    address: String(500)
    city: String(100)
    state: String(10)
    zip: String(20)
    phone: String(50)
    email: String(200)
    additional_info: Text
```

**Миграция:**
```sql
ALTER TABLE seller_enroll_items ADD COLUMN first_name VARCHAR(100);
ALTER TABLE seller_enroll_items ADD COLUMN last_name VARCHAR(100);
ALTER TABLE seller_enroll_items ADD COLUMN dob DATE;
ALTER TABLE seller_enroll_items ADD COLUMN ssn VARCHAR(20);  -- encrypted
ALTER TABLE seller_enroll_items ADD COLUMN address VARCHAR(500);
ALTER TABLE seller_enroll_items ADD COLUMN city VARCHAR(100);
ALTER TABLE seller_enroll_items ADD COLUMN state VARCHAR(10);
ALTER TABLE seller_enroll_items ADD COLUMN zip VARCHAR(20);
ALTER TABLE seller_enroll_items ADD COLUMN phone VARCHAR(50);
ALTER TABLE seller_enroll_items ADD COLUMN email VARCHAR(200);
ALTER TABLE seller_enroll_items ADD COLUMN additional_info TEXT;
```

---

## Синхронизация списков

### 1. Brute Bank — Обновить каталог

**Текущий:** 54 банка в 5 категориях  
**Mini App:** 22 банка плоский список  

**Решение:** Использовать 54 банка из БД, но добавить 22 банка из Mini App как "популярные"

```python
# shared/catalog_banks.py

# Добавить новую категорию
POPULAR_BRUTE_BANKS = [
    "Chase", "Bank of America", "Wells Fargo", "Citi", "US Bank", "PNC Bank",
    "TD Bank", "Capital One", "Regions Bank", "Truist", "Fifth Third", "KeyBank",
    "Huntington", "Citizens Bank", "M&T Bank", "Ally Bank", "SunTrust", "BB&T",
    "Navy Federal CU", "USAA", "Discover", "American Express",
]

BANK_CATALOG = {
    "popular": POPULAR_BRUTE_BANKS,  # НОВАЯ категория
    "vcc": VCC_BANKS,
    "personal": PERSONAL_BANKS,
    "business": BUSINESS_BANKS,
    "crypto": CRYPTO_BANKS,
    "merchant": MERCHANT_BANKS,
}
```

---

### 2. Selfreg CC — Расширить до 12 банков

**Добавить в БД:**

```sql
-- Добавить новые банки в selfreg_cc_categories
INSERT INTO selfreg_cc_categories (code, name, position, is_active, is_custom) VALUES
('capital_one', 'Capital One', 5, TRUE, FALSE),
('discover', 'Discover', 6, TRUE, FALSE),
('amex', 'American Express', 7, TRUE, FALSE),
('usbank', 'US Bank', 8, TRUE, FALSE),
('pnc', 'PNC Bank', 9, TRUE, FALSE),
('td', 'TD Bank', 10, TRUE, FALSE),
('barclays', 'Barclays', 11, TRUE, FALSE),
('synchrony', 'Synchrony', 12, TRUE, FALSE);
```

**Создать таблицу для названий карт:**

```sql
CREATE TABLE selfreg_cc_card_names (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES selfreg_cc_categories(id),
    card_name VARCHAR(200) NOT NULL,
    position INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Заполнить данными из Mini App
INSERT INTO selfreg_cc_card_names (category_id, card_name, position) VALUES
-- Chase
(2, 'Chase Freedom Unlimited', 1),
(2, 'Chase Freedom Flex', 2),
(2, 'Chase Sapphire Preferred', 3),
(2, 'Chase Sapphire Reserve', 4),
(2, 'Chase Ink Business Cash', 5),
(2, 'Chase Ink Business Unlimited', 6),
-- ... и так далее для всех банков
```

---

### 3. Enroll — Добавить Elan

```sql
INSERT INTO enroll_categories (code, name, position, is_active, is_custom) VALUES
('elan', 'Elan', 12, TRUE, FALSE);
```

---

## Обновление парсеров

### 1. CC Bulk Parser

**Поддержать оба формата:**

```python
# shared/services/seller_upload_pipeline_service.py

def parse_cc_bulk_line(line: str) -> dict:
    """
    Поддерживает два формата:
    
    Формат 1 (Mini App):
    NUMBER|EXP|CVV|NAME|ZIP|STATE|COUNTRY|BANK|TYPE|NON_VBV
    
    Формат 2 (Legacy):
    NUMBER|EXP|CVV|TYPE|BRAND|LVL|BANK|COUNTRY|HOLDER|ADDR|STATE|CITY|ZIP|Info|REF|PRICE
    """
    parts = line.split("|")
    
    # Определить формат по количеству полей
    if len(parts) == 10:
        # Mini App формат
        return {
            "number": parts[0],
            "exp": parts[1],
            "cvv": parts[2],
            "holder": parts[3],
            "zip": parts[4],
            "state": parts[5],
            "country": parts[6],
            "bank_name": parts[7],
            "card_type": parts[8],
            "is_non_vbv": parts[9].lower() in ("1", "true", "yes"),
        }
    elif len(parts) >= 16:
        # Legacy формат
        return {
            "number": parts[0],
            "exp": parts[1],
            "cvv": parts[2],
            "card_type": parts[3],
            "card_brand": parts[4],
            "card_level": parts[5],
            "bank_name": parts[6],
            "country": parts[7],
            "holder": parts[8],
            "address": parts[9],
            "state": parts[10],
            "city": parts[11],
            "zip": parts[12],
            "info": parts[13],
            "ref": parts[14],
            "price": parts[15] if len(parts) > 15 else None,
        }
    else:
        raise ValueError(f"Invalid CC format: expected 10 or 16+ fields, got {len(parts)}")
```

---

### 2. Brute Bank Bulk Parser

**Обновить формат:**

```python
def parse_brute_bulk_line(line: str) -> dict:
    """
    Формат: BANK|LOGIN|PASS|AN|RN|BALANCE|STATE|NAME|ADDRESS|ZIP|price
    """
    parts = line.split("|")
    if len(parts) < 11:
        raise ValueError(f"Invalid Brute format: expected 11 fields, got {len(parts)}")
    
    # Auto-detect attributes
    attrs = []
    if parts[3].strip(): attrs.append("AN")
    if parts[4].strip(): attrs.append("RN")
    if parts[7].strip(): attrs.append("NAME")
    if parts[8].strip(): attrs.append("ADDRESS")
    if parts[9].strip(): attrs.append("ZIP")
    
    return {
        "bank_name": parts[0],
        "login": parts[1],
        "password": parts[2],
        "account_number": parts[3],
        "routing_number": parts[4],
        "exact_balance": parts[5],
        "state": parts[6],
        "holder_name": parts[7],
        "address": parts[8],
        "zip": parts[9],
        "price": parts[10],
        "attributes": "+".join(attrs) if attrs else "LOGIN",
    }
```

---

## Порядок выполнения

### Фаза 1: Критические миграции (1-2 дня)
1. ✅ Banks — расширить модель
2. ✅ Brute Bank — добавить поля
3. ✅ CC — добавить NON VBV цену
4. ✅ Selfreg CC — добавить поля
5. ✅ OTP — добавить Fullz поля
6. ✅ Enrollment — добавить детальные поля

### Фаза 2: Синхронизация списков (1 день)
7. ✅ Обновить каталог банков
8. ✅ Расширить Selfreg CC до 12 банков
9. ✅ Добавить Elan в Enroll
10. ✅ Создать таблицу card_names

### Фаза 3: Обновление парсеров (1 день)
11. ✅ Обновить CC bulk parser
12. ✅ Обновить Brute bulk parser
13. ✅ Тестирование всех форматов

### Фаза 4: Обновление API (1 день)
14. ✅ Обновить эндпоинты seller_bot
15. ✅ Обновить эндпоинты mini_app
16. ✅ Обновить валидацию

---

## SQL Скрипт полной миграции

```sql
-- ============================================
-- МИГРАЦИЯ: Синхронизация с Mini App v2
-- Дата: 2026-03-24
-- ============================================

BEGIN;

-- 1. Banks Section
ALTER TABLE seller_bank_selfreg_items RENAME TO seller_bank_items;
ALTER TABLE seller_bank_items ADD COLUMN category VARCHAR(20);
ALTER TABLE seller_bank_items ADD COLUMN bank_code VARCHAR(50);
ALTER TABLE seller_bank_items ADD COLUMN product_type VARCHAR(100);
ALTER TABLE seller_bank_items ADD COLUMN balance DECIMAL(10,2) DEFAULT 0;
ALTER TABLE seller_bank_items ADD COLUMN phone_can_swap BOOLEAN DEFAULT FALSE;
ALTER TABLE seller_bank_items ADD COLUMN return_item_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE seller_bank_items ADD COLUMN return_days INTEGER;

-- 2. Brute Bank
ALTER TABLE brute_bank_items ADD COLUMN exact_balance VARCHAR(50);
ALTER TABLE brute_bank_items ADD COLUMN account_number VARCHAR(255);
ALTER TABLE brute_bank_items ADD COLUMN routing_number VARCHAR(255);
ALTER TABLE brute_bank_items ADD COLUMN holder_name VARCHAR(200);
ALTER TABLE brute_bank_items ADD COLUMN address VARCHAR(500);
ALTER TABLE brute_bank_items ADD COLUMN state VARCHAR(10);
ALTER TABLE brute_bank_items ADD COLUMN zip VARCHAR(20);
ALTER TABLE brute_bank_items ADD COLUMN additional_info TEXT;
ALTER TABLE brute_bank_items ADD COLUMN has_docs BOOLEAN DEFAULT FALSE;

-- 3. CC
ALTER TABLE seller_cc_items ADD COLUMN seller_price_non_vbv DECIMAL(10,2);
ALTER TABLE seller_cc_items ADD COLUMN buyer_price_non_vbv DECIMAL(10,2);

-- 4. Selfreg CC
ALTER TABLE seller_selfreg_cc_items ADD COLUMN registration_date DATE;
ALTER TABLE seller_selfreg_cc_items ADD COLUMN vcc_bin VARCHAR(6);
ALTER TABLE seller_selfreg_cc_items ADD COLUMN return_item_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE seller_selfreg_cc_items ADD COLUMN return_days INTEGER;

-- 5. OTP
ALTER TABLE seller_otp_items ADD COLUMN state VARCHAR(10);
ALTER TABLE seller_otp_items ADD COLUMN zip VARCHAR(20);
ALTER TABLE seller_otp_items ADD COLUMN fullz_first_name VARCHAR(100);
ALTER TABLE seller_otp_items ADD COLUMN fullz_last_name VARCHAR(100);
ALTER TABLE seller_otp_items ADD COLUMN fullz_dob DATE;
ALTER TABLE seller_otp_items ADD COLUMN fullz_ssn VARCHAR(20);
ALTER TABLE seller_otp_items ADD COLUMN fullz_address VARCHAR(500);
ALTER TABLE seller_otp_items ADD COLUMN fullz_city VARCHAR(100);
ALTER TABLE seller_otp_items ADD COLUMN fullz_state VARCHAR(10);
ALTER TABLE seller_otp_items ADD COLUMN fullz_zip VARCHAR(20);
ALTER TABLE seller_otp_items ADD COLUMN fullz_phone VARCHAR(50);
ALTER TABLE seller_otp_items ADD COLUMN fullz_email VARCHAR(200);

-- 6. Enrollment
ALTER TABLE seller_enroll_items ADD COLUMN first_name VARCHAR(100);
ALTER TABLE seller_enroll_items ADD COLUMN last_name VARCHAR(100);
ALTER TABLE seller_enroll_items ADD COLUMN dob DATE;
ALTER TABLE seller_enroll_items ADD COLUMN ssn VARCHAR(20);
ALTER TABLE seller_enroll_items ADD COLUMN address VARCHAR(500);
ALTER TABLE seller_enroll_items ADD COLUMN city VARCHAR(100);
ALTER TABLE seller_enroll_items ADD COLUMN state VARCHAR(10);
ALTER TABLE seller_enroll_items ADD COLUMN zip VARCHAR(20);
ALTER TABLE seller_enroll_items ADD COLUMN phone VARCHAR(50);
ALTER TABLE seller_enroll_items ADD COLUMN email VARCHAR(200);
ALTER TABLE seller_enroll_items ADD COLUMN additional_info TEXT;

-- 7. Создать таблицу для названий карт Selfreg CC
CREATE TABLE IF NOT EXISTS selfreg_cc_card_names (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES selfreg_cc_categories(id) ON DELETE CASCADE,
    card_name VARCHAR(200) NOT NULL,
    position INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. Добавить новые банки в Selfreg CC
INSERT INTO selfreg_cc_categories (code, name, position, is_active, is_custom) VALUES
('capital_one', 'Capital One', 5, TRUE, FALSE),
('discover', 'Discover', 6, TRUE, FALSE),
('amex', 'American Express', 7, TRUE, FALSE),
('usbank', 'US Bank', 8, TRUE, FALSE),
('pnc', 'PNC Bank', 9, TRUE, FALSE),
('td', 'TD Bank', 10, TRUE, FALSE),
('barclays', 'Barclays', 11, TRUE, FALSE),
('synchrony', 'Synchrony', 12, TRUE, FALSE)
ON CONFLICT (code) DO NOTHING;

-- 9. Добавить Elan в Enroll
INSERT INTO enroll_categories (code, name, position, is_active, is_custom) VALUES
('elan', 'Elan', 12, TRUE, FALSE)
ON CONFLICT (code) DO NOTHING;

-- 10. Обновить существующие записи
UPDATE seller_bank_items SET category = 'personal' WHERE category IS NULL;
UPDATE seller_bank_items SET balance = 0 WHERE balance IS NULL;
UPDATE seller_cc_items SET seller_price_non_vbv = seller_price WHERE seller_price_non_vbv IS NULL;
UPDATE seller_cc_items SET buyer_price_non_vbv = buyer_price WHERE buyer_price_non_vbv IS NULL;

COMMIT;
```

---

**Готово к выполнению!**
