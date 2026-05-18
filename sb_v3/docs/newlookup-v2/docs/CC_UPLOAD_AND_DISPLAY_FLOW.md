# CC Upload and Display Flow — Complete Reference

## 1. Массовая загрузка (Bulk Upload)

### Процесс загрузки:

1. **Seller выбирает категорию**:
   - USA CC (`category_code = "usa"`)
   - World CC (`category_code = "world"`)
   - NON VBV (`is_non_vbv = True`, любая категория)

2. **Seller вставляет данные** (текст или файл):
   ```
   NUMBER|EXP|CVV|TYPE|BRAND|LVL|BANK|COUNTRY|HOLDER|ADDR|STATE|CITY|ZIP|Info|REF|PRICE
   ```
   - **Обязательные поля**: NUMBER, EXP, CVV
   - **Опциональные поля**: все остальные

3. **Парсинг каждой строки**:
   - `parse_cc_line_flexible()` извлекает данные
   - Проверяет валидность номера (≥12 цифр), expiry, CVV

4. **🆕 BIN Auto-Enrichment** (автоматическое обогащение):
   ```python
   await BinLookupService.enrich_parsed(parsed)
   ```
   - Если TYPE пустой → запрос к binlist.net → заполняет CREDIT/DEBIT/PREPAID
   - Если BRAND пустой → заполняет Visa/Mastercard/Amex/Discover
   - Если LVL пустой → заполняет Classic/Gold/Platinum/Signature
   - Если BANK пустой → заполняет название банка
   - Если COUNTRY пустой → заполняет код страны (US/GB/etc)
   - **Кэш**: 2000 записей, TTL 24 часа
   - **Rate limit**: 250ms между запросами

5. **Создание записей**:
   - Каждая карта → отдельная запись `SellerCCItem`
   - `moderation_status = "pending_moderation"`
   - `card_bin` = первые 6 цифр номера
   - `card_type` = CREDIT/DEBIT/PREPAID (из BIN lookup или из строки)
   - `card_brand` = Visa/Mastercard/etc
   - `card_level` = Classic/Gold/etc
   - `bank_name` = название банка
   - `buyer_price` = seller_price (до модерации)

6. **Модерация**:
   - Admin одобряет → `moderation_status = "approved"`
   - Admin применяет markup → `buyer_price` пересчитывается
   - Только после одобрения товар появляется у покупателя

---

## 2. Распределение по категориям у покупателя

### Логика фильтрации (`shared/cc_catalog.py`):

```python
# Источники товаров:
1. Admin catalog (CCItem) — статические позиции
2. Seller items (SellerCCItem) — одобренные загрузки

# Условия для показа seller items:
- SellerCCItem.is_active == True
- SellerCCItem.moderation_status == "approved"
- Seller.is_approved == True
- Seller.is_active == True

# Фильтр по категории:
if category_code == "non_vbv":
    # Показываем все карты с флагом NON VBV
    SellerCCItem.is_non_vbv == True
else:
    # Показываем карты из конкретной категории
    SellerCCItem.category_code == category_code  # "usa" или "world"
```

### Дополнительные фильтры:
- **BIN search**: `card_bin.startswith(query)` или `number.startswith(query)`
- **ZIP search**: `zip.ilike(f"%{query}%")`
- **Сортировка**: по `buyer_price` (↑ или ↓)
- **Pagination**: 10 items per page

---

## 3. Параметры в названии кнопок (Button Text)

### Формат для seller CC items:
```
{bank_name} {card_brand} ***{last4} | ${buyer_price:.2f}
```

### Пример:
```
Chase Visa ***1234 | $45.00
Wells Fargo Mastercard ***5678 | $52.50
CITI Amex ***9012 | $65.00
```

### Детали:
- `bank_name`: обрезается до 20 символов
- `card_brand`: обрезается до 16 символов
- `last4`: последние 4 цифры номера карты
- `buyer_price`: всегда 2 знака после запятой
- Максимальная длина кнопки: 64 символа (обрезается с `…`)

### Код генерации:
```python
# shared/cc_catalog.py, lines 102-109
last4 = num[-4:] if len(num) >= 4 else ""
bank = (s.bank_name or "")[:20]
brand = (s.card_brand or "")[:16]
btn = f"{bank} {brand} ***{last4} | ${float(s.buyer_price):.2f}"
```

---

## 4. Параметры в описании (Description)

### Полный список полей в `render_cc_description()`:

#### Основная информация:
```
💳 {card_brand} {BIN} — {bank_name}
━━━━━━━━━━━━━━━━━━━
BIN: {BIN} | Exp: {exp}
Type: {card_type} {card_level} | NON-VBV: {✅/❌}
Country: {flag} {country} | State: {state} | ZIP: {zip}
```

#### Дополнительные поля (если есть):
```
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

### Источники данных:
1. **Прямые поля модели**:
   - `item.bank_name`
   - `item.card_brand`
   - `item.card_level`
   - `item.country`, `item.state`, `item.zip`
   - `item.address`, `item.city`
   - `item.fname`, `item.lname`
   - `item.number` (для BIN и last4)
   - `item.is_non_vbv`

2. **Поле `extra_data` (JSON)**:
   - `extra_data.bin`
   - `extra_data.exp`
   - `extra_data.card_type` (CREDIT/DEBIT/PREPAID)
   - `extra_data.brand`
   - `extra_data.level`
   - `extra_data.bank`
   - `extra_data.country`
   - `extra_data.holder`
   - `extra_data.phone`
   - `extra_data.email`
   - `extra_data.ssn`
   - `extra_data.dob`
   - `extra_data.dl`
   - `extra_data.info`
   - `extra_data.ref`

### Приоритет данных:
```python
# Пример для bank_name:
bank_name = getattr(item, "bank_name", None) or extra.get("bank") or "—"

# Если поле есть в модели — берется оттуда
# Если нет — берется из extra_data
# Если нигде нет — показывается "—"
```

---

## 5. Полный цикл жизни CC item

```
┌─────────────────────────────────────────────────────────────┐
│ 1. SELLER UPLOAD                                            │
│    - Выбор категории (usa/world/non_vbv)                   │
│    - Вставка данных (bulk или single)                       │
│    - Парсинг: NUMBER|EXP|CVV|TYPE|BRAND|LVL|BANK|...       │
│    - 🆕 BIN Auto-Enrichment (binlist.net API)              │
│    - Создание SellerCCItem (status: pending_moderation)    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. MODERATION (Admin/Support Bot/Web Panel)                │
│    - Просмотр всех полей (BIN, bank, brand, type, level)   │
│    - 🆕 Поиск по BIN/bank/brand/type                       │
│    - Применение markup (buyer_price = seller_price + %)    │
│    - Одобрение → status: approved                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. BUYER CATALOG                                            │
│    - Фильтр по категории (usa/world/non_vbv)               │
│    - Фильтр по BIN/ZIP                                      │
│    - Сортировка по цене                                     │
│    - Кнопка: "{bank} {brand} ***{last4} | ${price}"        │
│    - Описание: все поля + BIN data + NON-VBV badge         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. PURCHASE                                                 │
│    - Buyer покупает → создается SellerCCOrder               │
│    - Reveal: показываются полные данные карты               │
│    - Feedback/Report system                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Ключевые улучшения (реализовано)

### ✅ BIN Auto-Checker:
- Автоматическое заполнение TYPE|BRAND|LVL|BANK
- Seller больше не обязан вводить эти поля вручную
- Кэширование для скорости и экономии API лимитов

### ✅ Стандартизация кнопок:
- Единый формат: `{title} | ${price:.2f}`
- Применено ко всем типам товаров (CC, Banks, Brute Bank, OTP, NFC, etc)

### ✅ Обогащение описаний:
- BIN data автоматически попадает в описание
- Показываются все доступные поля (SSN, DOB, phone, email, etc)

### ✅ Улучшенные фильтры в админке:
- **Support Bot**: команда "Search CC" с FSM для поиска по BIN/bank/brand/type
- **Web Panel**: поля поиска + dropdown для card_type и card_brand
- Фильтрация работает для всех статусов модерации

---

## 7. Примеры данных

### Пример загрузки (минимальный):
```
4111111111111111|12/26|123
```
→ BIN lookup заполнит: TYPE=DEBIT, BRAND=Visa, BANK=Test Bank

### Пример загрузки (полный):
```
4432644901621883|10/26|194|DEBIT|Visa|CLASSIC|U.S. BANK N.A.|US|Jesse Van Der Sluis|155 Rita Way|NY|Albany|42701||base01|14
```
→ Все поля уже заполнены, BIN lookup не нужен

### Пример кнопки в каталоге:
```
U.S. BANK N.A. Visa ***1883 | $45.00
```

### Пример описания:
```
💳 Visa 443264 — U.S. BANK N.A.
━━━━━━━━━━━━━━━━━━━
BIN: 443264 | Exp: 10/26
Type: DEBIT CLASSIC | NON-VBV: ❌
Country: 🇺🇸 US | State: NY | ZIP: 42701
Address: 155 Rita Way, Albany
Holder: Jesse Van Der Sluis
━━━━━━━━━━━━━━━━━━━
```
