# CC Category Distribution — Полное описание

## 1. Структура категорий

### Основные категории:
```python
# Дефолтные категории (если нет в БД):
categories = [
    {"code": "usa",   "name": "🇺🇸 USA CC"},
    {"code": "world", "name": "🌍 ALL WORLD CC"},
]

# Специальная категория (виртуальная):
{"code": "non_vbv", "name": "🔓 NON VBV"}
```

### Источник категорий:
```python
# Функция: get_cc_categories(session)
# Файл: shared/cc_catalog.py, lines 14-29

1. Пытается загрузить из таблицы CCCategory:
   - WHERE is_active = True
   - ORDER BY position, id
   
2. Если таблица пустая или ошибка → возвращает дефолтные категории
```

---

## 2. Логика распределения товаров по категориям

### Функция: `get_cc_items_for_category()`
**Файл**: `shared/cc_catalog.py`, lines 50-121

### Входные параметры:
```python
category_code: str        # "usa", "world", "non_vbv"
bin_prefix: str | None    # Фильтр по BIN (первые 6 цифр)
zip_q: str | None         # Фильтр по ZIP коду
sort_price: str           # "asc" или "desc"
```

### Шаг 1: Загрузка admin items (статические позиции)
```python
# Источник: таблица CCItem
SELECT * FROM cc_items 
WHERE category_code = {category_code}
  AND is_active = True
ORDER BY position, id

# Результат:
items.append({
    "id": c.cc_code,
    "name": c.name,
    "price": float(c.price),
    "source": "admin"
})
```

### Шаг 2: Загрузка seller items (одобренные загрузки)

#### Базовые условия (всегда применяются):
```python
conditions = [
    SellerCCItem.is_active == True,              # Товар активен
    SellerCCItem.moderation_status == "approved", # Одобрен модератором
    Seller.is_approved == True,                   # Seller одобрен
    Seller.is_active == True,                     # Seller активен
]
```

#### Условие по категории:
```python
if category_code == "non_vbv":
    # Специальная категория: показываем ВСЕ карты с флагом NON-VBV
    # независимо от их category_code (usa/world)
    conditions.append(SellerCCItem.is_non_vbv == True)
else:
    # Обычная категория: показываем только карты из этой категории
    conditions.append(SellerCCItem.category_code == category_code)
```

**Важно**: Карта может быть одновременно:
- В категории "usa" (`category_code = "usa"`)
- И в категории "non_vbv" (`is_non_vbv = True`)

Пример:
```
Seller загружает карту:
- category_code = "usa"
- is_non_vbv = True

Эта карта появится в ДВУХ категориях:
1. 🇺🇸 USA CC (по category_code)
2. 🔓 NON VBV (по флагу is_non_vbv)
```

#### Дополнительные фильтры:

**Фильтр по BIN:**
```python
if bin_prefix:
    conditions.append(
        OR(
            SellerCCItem.card_bin == bin_prefix,      # Точное совпадение BIN
            SellerCCItem.number.startswith(bin_prefix) # Или начало номера
        )
    )
```

Примеры:
- Поиск `443264` → найдет карты с BIN 443264
- Поиск `4432` → найдет все карты, начинающиеся с 4432

**Фильтр по ZIP:**
```python
if zip_q:
    conditions.append(
        SellerCCItem.zip.ilike(f"%{zip_q}%")  # Case-insensitive LIKE
    )
```

Примеры:
- Поиск `10001` → найдет ZIP: 10001, 100012, 210001
- Поиск `NY` → найдет ZIP: NY10001, BRONXNY

#### Сортировка:
```python
order_col = SellerCCItem.buyer_price

if sort_price == "desc":
    order_dir = order_col.desc()  # От дорогих к дешевым
else:
    order_dir = order_col.asc()   # От дешевых к дорогим (по умолчанию)

ORDER BY order_dir, SellerCCItem.item_name
```

**Важно**: Вторичная сортировка по `item_name` для стабильного порядка при одинаковых ценах.

### Шаг 3: Формирование результата для seller items

```python
for s in seller_cc_items:
    # Извлечение последних 4 цифр номера
    num = (s.number or "").replace(" ", "")
    last4 = num[-4:] if len(num) >= 4 else ""
    
    # Обрезка длинных названий
    bank = (s.bank_name or "")[:20]   # Макс 20 символов
    brand = (s.card_brand or "")[:16] # Макс 16 символов
    
    # Формирование текста кнопки
    btn = f"{bank} {brand} ***{last4} | ${float(s.buyer_price):.2f}"
    
    items.append({
        "id": str(s.id),
        "name": btn,                              # Текст кнопки
        "price": float(s.buyer_price),            # Цена для сортировки
        "source": "seller",                       # Источник
        "seller_item_id": s.id,                   # ID для покупки
        "product_subtype": s.product_subtype,     # "with_fullz", "standard", etc
        "description": render_cc_description(s),  # Полное описание
    })
```

---

## 3. Параметры в названии кнопок (Button Text)

### Формат:
```
{bank_name} {card_brand} ***{last4} | ${buyer_price:.2f}
```

### Детальная разбивка:

#### 1. `bank_name` (макс 20 символов):
```python
bank = (s.bank_name or "")[:20]
```

**Источники данных** (приоритет):
1. `SellerCCItem.bank_name` — прямое поле модели
2. Если пусто → из `extra_data->>'bank'`
3. Если пусто → заполнено через BIN lookup (binlist.net)

**Примеры**:
- `"Chase"` → `"Chase"`
- `"U.S. BANK NATIONAL ASSOCIATION"` → `"U.S. BANK NATIONAL A"` (обрезано)
- `"Wells Fargo"` → `"Wells Fargo"`

#### 2. `card_brand` (макс 16 символов):
```python
brand = (s.card_brand or "")[:16]
```

**Источники данных**:
1. `SellerCCItem.card_brand` — прямое поле
2. Если пусто → из `extra_data->>'brand'`
3. Если пусто → заполнено через BIN lookup
4. Если пусто → определено по номеру карты (первая цифра)

**Возможные значения**:
- `"Visa"`
- `"Mastercard"`
- `"Amex"` (American Express)
- `"Discover"`
- `"JCB"`
- `"UnionPay"`
- `"Maestro"`

#### 3. `***{last4}`:
```python
num = (s.number or "").replace(" ", "")
last4 = num[-4:] if len(num) >= 4 else ""
```

**Формат**: Всегда 3 звездочки + последние 4 цифры

**Примеры**:
- Номер `4111111111111111` → `***1111`
- Номер `5500 0055 5555 5559` → `***5559`
- Номер `378282246310005` → `***0005`

#### 4. `|` (разделитель):
Фиксированный символ pipe для единообразия

#### 5. `${buyer_price:.2f}`:
```python
f"${float(s.buyer_price):.2f}"
```

**Формат**: Всегда 2 знака после запятой

**Примеры**:
- `45.00` → `$45.00`
- `52.5` → `$52.50`
- `100` → `$100.00`

### Полные примеры кнопок:

```
Chase Visa ***1234 | $45.00
Wells Fargo Mastercard ***5678 | $52.50
CITI Amex ***9012 | $65.00
U.S. BANK NATIONAL A Visa ***4321 | $38.00
Bank of America Discover ***8765 | $55.00
```

### Ограничения:
- **Максимальная длина кнопки**: 64 символа (Telegram API limit)
- Если текст длиннее → обрезается с добавлением `…`
- Обрезка происходит в `mirror_bot/keyboards/cc.py`:
  ```python
  text=f"{item['name'][:58]}{'…' if len(item['name']) > 58 else ''}"
  ```

---

## 4. Параметры в описании (Description)

### Функция: `render_cc_description(item)`
**Файл**: `shared/utils/seller_card_renderers.py`, lines 36-90

### Полный формат описания:

```
💳 {card_brand} {BIN} — {bank_name}
━━━━━━━━━━━━━━━━━━━
BIN: {BIN} | Exp: {exp}
Type: {card_type} {card_level} | NON-VBV: {✅/❌}
Country: {flag} {country} | State: {state} | ZIP: {zip}
[Address: {address}, {city}]              ← если есть
[Holder: {fname} {lname}]                 ← если есть
[Phone: {phone}]                          ← если есть
[Email: {email}]                          ← если есть
[SSN: {ssn}]                              ← если есть
[DOB: {dob}]                              ← если есть
[Info: {info}]                            ← если есть
[Ref: {ref}]                              ← если есть
━━━━━━━━━━━━━━━━━━━
```

### Детальная разбивка всех параметров:

#### 1. Заголовок:
```python
f"💳 <b>{card_brand}</b> {bin_val} — {bank_name}"
```

**Параметры**:
- `card_brand`: Visa, Mastercard, Amex, etc
- `bin_val`: Первые 6 цифр номера карты
- `bank_name`: Название банка

**Источники**:
```python
card_brand = getattr(item, "card_brand", None) or extra.get("brand") or "CC"
bin_val = extra.get("bin") or (number[:6] if len(number) >= 6 else number) or "—"
bank_name = getattr(item, "bank_name", None) or extra.get("bank") or "—"
```

**Пример**:
```
💳 Visa 443264 — U.S. BANK N.A.
```

#### 2. Основная информация (строка 1):
```python
f"BIN: {bin_val} | Exp: {exp}"
```

**Параметры**:
- `bin_val`: Первые 6 цифр (уже извлечено выше)
- `exp`: Срок действия в формате MM/YY

**Источник exp**:
```python
exp = extra.get("exp") or "—"
# Формат при загрузке: "10/26", "12/28", etc
```

**Пример**:
```
BIN: 443264 | Exp: 10/26
```

#### 3. Основная информация (строка 2):
```python
f"Type: {type_level} | NON-VBV: {non_vbv}"
```

**Параметры**:
- `type_level`: Комбинация card_type и card_level
- `non_vbv`: ✅ или ❌

**Источники**:
```python
card_type = extra.get("card_type") or ""  # DEBIT, CREDIT, PREPAID
card_level = extra.get("level") or getattr(item, "card_level", None) or getattr(item, "item_name", None) or ""
type_level = " ".join(p for p in [card_type, card_level] if p) or card_brand
non_vbv = "✅" if getattr(item, "is_non_vbv", False) else "❌"
```

**Примеры**:
```
Type: DEBIT CLASSIC | NON-VBV: ❌
Type: CREDIT GOLD | NON-VBV: ✅
Type: PREPAID | NON-VBV: ❌
Type: Visa | NON-VBV: ❌  ← если type и level пустые
```

#### 4. Основная информация (строка 3):
```python
f"Country: {country_with_flag} | State: {state} | ZIP: {zip}"
```

**Параметры**:
- `country_with_flag`: Флаг + код страны
- `state`: Штат (2 буквы)
- `zip`: Почтовый индекс

**Источники**:
```python
country = getattr(item, "country", None) or extra.get("country") or "—"
state = getattr(item, "state", None) or extra.get("state") or "—"
zip_code = getattr(item, "zip", None) or extra.get("zip") or "—"

# Генерация флага:
def _flag(country_code):
    code = str(country_code or "").strip().upper()
    if len(code) != 2 or not code.isalpha():
        return ""
    return "".join(chr(127397 + ord(char)) for char in code)

country_with_flag = f"{_flag(country)} {country}".strip()
```

**Примеры**:
```
Country: 🇺🇸 US | State: NY | ZIP: 10001
Country: 🇬🇧 GB | State: — | ZIP: SW1A 1AA
Country: — | State: CA | ZIP: 90210
```

#### 5. Дополнительные поля (показываются только если есть):

**Address:**
```python
if address != "—":
    lines.append(f"Address: {address}, {city}")
```

**Источники**:
```python
address = getattr(item, "address", None) or extra.get("address") or "—"
city = getattr(item, "city", None) or extra.get("city") or "—"
```

**Пример**:
```
Address: 155 Rita Way, Albany
```

**Holder:**
```python
if holder != "—":
    lines.append(f"Holder: {holder}")
```

**Источники**:
```python
holder = extra.get("holder") or ""
if not holder:
    fname = getattr(item, "fname", None) or ""
    lname = getattr(item, "lname", None) or ""
    holder = " ".join(p for p in [fname, lname] if p) or "—"
```

**Пример**:
```
Holder: Jesse Van Der Sluis
```

**Phone:**
```python
if phone != "—":
    lines.append(f"Phone: {phone}")
```

**Источник**:
```python
phone = extra.get("phone") or "—"
```

**Пример**:
```
Phone: +1 (555) 123-4567
```

**Email:**
```python
if email != "—":
    lines.append(f"Email: {email}")
```

**Источник**:
```python
email = extra.get("email") or "—"
```

**Пример**:
```
Email: john.doe@example.com
```

**SSN:**
```python
if ssn != "—":
    lines.append(f"SSN: {ssn}")
```

**Источник**:
```python
ssn = extra.get("ssn") or "—"
```

**Пример**:
```
SSN: 123-45-6789
```

**DOB:**
```python
if dob != "—":
    lines.append(f"DOB: {dob}")
```

**Источник**:
```python
dob = extra.get("dob") or "—"
```

**Пример**:
```
DOB: 01/15/1985
```

**Info:**
```python
if info:
    lines.append(f"Info: {info}")
```

**Источник**:
```python
info = extra.get("info") or ""
```

**Пример**:
```
Info: Fresh base, high balance
```

**Ref:**
```python
if ref:
    lines.append(f"Ref: {ref}")
```

**Источник**:
```python
ref = extra.get("ref") or ""
```

**Пример**:
```
Ref: base01
```

---

## 5. Полный пример описания

### Минимальное описание (только обязательные поля):
```
💳 Visa 411111 — Test Bank
━━━━━━━━━━━━━━━━━━━
BIN: 411111 | Exp: 12/26
Type: Visa | NON-VBV: ❌
Country: — | State: — | ZIP: —
━━━━━━━━━━━━━━━━━━━
```

### Полное описание (все поля заполнены):
```
💳 Visa 443264 — U.S. BANK N.A.
━━━━━━━━━━━━━━━━━━━
BIN: 443264 | Exp: 10/26
Type: DEBIT CLASSIC | NON-VBV: ❌
Country: 🇺🇸 US | State: NY | ZIP: 42701
Address: 155 Rita Way, Albany
Holder: Jesse Van Der Sluis
Phone: +1 (555) 123-4567
Email: jesse.vds@example.com
SSN: 123-45-6789
DOB: 03/15/1990
Info: Fresh base, verified balance
Ref: base01
━━━━━━━━━━━━━━━━━━━
```

---

## 6. Источники данных — приоритеты

### Для всех полей действует единая логика:

```python
# Приоритет 1: Прямое поле модели
value = getattr(item, "field_name", None)

# Приоритет 2: Поле extra_data (JSON)
if not value:
    value = extra.get("field_name")

# Приоритет 3: BIN lookup (только для card_type, card_brand, card_level, bank_name, country)
# Заполняется автоматически при загрузке через BinLookupService.enrich_parsed()

# Приоритет 4: Дефолтное значение
if not value:
    value = "—"  # или "" в зависимости от поля
```

### Таблица источников:

| Параметр | Модель (SellerCCItem) | extra_data | BIN Lookup | Дефолт |
|----------|----------------------|------------|------------|--------|
| bank_name | ✅ bank_name | ✅ bank | ✅ | "—" |
| card_brand | ✅ card_brand | ✅ brand | ✅ | "CC" |
| card_level | ✅ card_level | ✅ level | ✅ | "" |
| card_type | ✅ card_type | ✅ card_type | ✅ | "" |
| country | ✅ country | ✅ country | ✅ | "—" |
| state | ✅ state | ✅ state | ❌ | "—" |
| zip | ✅ zip | ✅ zip | ❌ | "—" |
| city | ✅ city | ✅ city | ❌ | "—" |
| address | ✅ address | ✅ address | ❌ | "—" |
| fname | ✅ fname | ❌ | ❌ | "" |
| lname | ✅ lname | ❌ | ❌ | "" |
| number | ✅ number | ✅ card | ❌ | "" |
| exp | ❌ | ✅ exp | ❌ | "—" |
| cvv | ✅ cvv | ✅ cvc | ❌ | "" |
| phone | ❌ | ✅ phone | ❌ | "—" |
| email | ❌ | ✅ email | ❌ | "—" |
| ssn | ❌ | ✅ ssn | ❌ | "—" |
| dob | ❌ | ✅ dob | ❌ | "—" |
| dl | ❌ | ✅ dl | ❌ | "—" |
| info | ❌ | ✅ info | ❌ | "" |
| ref | ❌ | ✅ ref | ❌ | "" |
| is_non_vbv | ✅ is_non_vbv | ❌ | ❌ | False |

---

## 7. Примеры распределения по категориям

### Пример 1: Карта только в USA
```python
# Seller загружает:
category_code = "usa"
is_non_vbv = False

# Карта появится в:
✅ 🇺🇸 USA CC
❌ 🌍 ALL WORLD CC
❌ 🔓 NON VBV
```

### Пример 2: Карта только в WORLD
```python
# Seller загружает:
category_code = "world"
is_non_vbv = False

# Карта появится в:
❌ 🇺🇸 USA CC
✅ 🌍 ALL WORLD CC
❌ 🔓 NON VBV
```

### Пример 3: Карта USA + NON VBV
```python
# Seller загружает:
category_code = "usa"
is_non_vbv = True

# Карта появится в:
✅ 🇺🇸 USA CC (по category_code)
❌ 🌍 ALL WORLD CC
✅ 🔓 NON VBV (по флагу is_non_vbv)
```

### Пример 4: Карта WORLD + NON VBV
```python
# Seller загружает:
category_code = "world"
is_non_vbv = True

# Карта появится в:
❌ 🇺🇸 USA CC
✅ 🌍 ALL WORLD CC (по category_code)
✅ 🔓 NON VBV (по флагу is_non_vbv)
```

### Важно:
- Категория NON VBV — это **виртуальная категория**
- Она не хранится в `category_code`, а определяется флагом `is_non_vbv`
- Одна карта может быть в 2 категориях одновременно (основная + NON VBV)

---

## 8. Фильтры и поиск

### Доступные фильтры для покупателя:

#### 1. Фильтр по BIN:
```
Buyer вводит: 443264
Система ищет: card_bin = "443264" OR number LIKE "443264%"
```

#### 2. Фильтр по ZIP:
```
Buyer вводит: 10001
Система ищет: zip LIKE "%10001%"
```

#### 3. Сортировка по цене:
```
Price ↑ (по умолчанию): ORDER BY buyer_price ASC
Price ↓: ORDER BY buyer_price DESC
```

### Доступные фильтры для админа (модерация):

#### 1. Текстовый поиск (q):
```python
if q.isdigit() and len(q) >= 4:
    # Поиск по BIN
    WHERE card_bin LIKE "q%"
else:
    # Поиск по тексту
    WHERE bank_name ILIKE "%q%" 
       OR card_brand ILIKE "%q%"
       OR card_type ILIKE "%q%"
       OR item_name ILIKE "%q%"
```

#### 2. Фильтр по card_type:
```
Dropdown: CREDIT, DEBIT, PREPAID
WHERE card_type ILIKE "selected_type"
```

#### 3. Фильтр по card_brand:
```
Dropdown: Visa, Mastercard, Amex, Discover
WHERE card_brand ILIKE "selected_brand"
```

#### 4. Фильтр по статусу модерации:
```
Dropdown: pending_moderation, approved, rejected
WHERE moderation_status = "selected_status"
```

---

## 9. Pagination

### Для покупателя:
```python
CC_ITEMS_PER_PAGE = 10  # mirror_bot/keyboards/cc.py, line 49

# Навигация:
⬅️ Prev | 📄 {page + 1}/{total_pages} | Next ➡️
```

### Для админа (support bot):
```python
LIMIT 15  # support_bot/handlers/seller_moderation.py, line 846
```

### Для админа (web panel):
```python
LIMIT 100  # web_panel/api/seller_moderation.py, line 179
```

---

## 10. Полный SQL запрос (пример)

```sql
-- Для категории "usa" с фильтром по BIN "443264" и сортировкой по цене ↑
SELECT seller_cc_items.* 
FROM seller_cc_items
JOIN sellers ON seller_cc_items.seller_id = sellers.id
WHERE seller_cc_items.is_active = TRUE
  AND seller_cc_items.moderation_status = 'approved'
  AND sellers.is_approved = TRUE
  AND sellers.is_active = TRUE
  AND seller_cc_items.category_code = 'usa'
  AND (seller_cc_items.card_bin = '443264' OR seller_cc_items.number LIKE '443264%')
ORDER BY seller_cc_items.buyer_price ASC, seller_cc_items.item_name ASC
LIMIT 10 OFFSET 0;
```

```sql
-- Для категории "non_vbv" без фильтров
SELECT seller_cc_items.* 
FROM seller_cc_items
JOIN sellers ON seller_cc_items.seller_id = sellers.id
WHERE seller_cc_items.is_active = TRUE
  AND seller_cc_items.moderation_status = 'approved'
  AND sellers.is_approved = TRUE
  AND sellers.is_active = TRUE
  AND seller_cc_items.is_non_vbv = TRUE
ORDER BY seller_cc_items.buyer_price ASC, seller_cc_items.item_name ASC
LIMIT 10 OFFSET 0;
```
