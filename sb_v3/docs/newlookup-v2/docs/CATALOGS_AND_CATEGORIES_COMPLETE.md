# 📚 Полная документация: Каталоги, Категории и Запросы на создание разделов

## 📋 Содержание

1. [Предзагруженные каталоги банков](#1-предзагруженные-каталоги-банков)
2. [Категории веб-панели](#2-категории-веб-панели)
3. [Brute Bank - Группы и категории](#3-brute-bank---группы-и-категории)
4. [Логика создания разделов](#4-логика-создания-разделов)
5. [Запросы на создание новых категорий](#5-запросы-на-создание-новых-категорий)
6. [API эндпоинты](#6-api-эндпоинты)
7. [Модели БД](#7-модели-бд)

---

## 1. Предзагруженные каталоги банков

### 1.1 Файл: `shared/catalog_banks.py` (83 строки)

**Назначение:** Хардкодированный fallback-каталог банков, используется когда `BankItem` пуст в БД.

**Структура:**

```python
BANK_CATALOG = {
    "vcc": VCC_BANKS,           # 14 банков
    "personal": PERSONAL_BANKS,  # 15 банков
    "business": BUSINESS_BANKS,  # 10 банков
    "crypto": CRYPTO_BANKS,      # 6 банков
    "merchant": MERCHANT_BANKS,  # 9 банков
}
```

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

### 1.2 Файл: `shared/catalog.py` (60 строк)

**Функции:**

```python
async def get_bank_types_for_category(session, category: str) -> List[Dict]:
    """
    Получить банки для категории.
    1. Сначала из БД (BankItem)
    2. Если пусто → fallback на BANK_CATALOG
    Возвращает: [{"id": bank_code, "name": display_name}, ...]
    """

async def get_bank_name_by_id(session, bank_id: str) -> str:
    """
    Получить название банка по ID.
    1. Сначала из БД (BankItem)
    2. Если не найдено → из BANK_CATALOG
    """

def get_bank_by_id_from_catalog(bank_id: str) -> Optional[Dict]:
    """
    Поиск банка в хардкодированном каталоге.
    """
```

---

## 2. Категории веб-панели

### 2.1 Файл: `web_panel/constants/categories.py` (473 строки)

**Структура `CATEGORIES_DATA`:**

```python
CATEGORIES_DATA = {
    "📶 eSIM": {
        "emoji": "📶",
        "name": "eSIM",
        "services": {
            "eSIM for receive SMS": [...],
            "eSIM for Data": [...]
        }
    },
    "📄 DOCUMENTS": {...},
    "🧰 PROS & FULLZ": {...},
    "🏦 BANKS": {...},
    "🧾 Subscriptions / Accounts": {...},
    "✍️ Add info in CR": {...},
    "🔎 Search": {...},
    "📈 CREDIT REPORTS": {...}
}
```

**Категория "🏦 BANKS" (полная структура):**

```python
"🏦 BANKS": {
    "emoji": "🏦",
    "name": "BANKS",
    "services": {
        "PERSONAL VCC": [
            {"code": "vcc_chime", "name": "Chime VCC"},
            {"code": "vcc_paypal", "name": "PayPal VCC"},
            # ... 14 банков
        ],
        "PERSONAL BANKS": [
            {"code": "pers_citi", "name": "Citi Personal"},
            {"code": "pers_chase", "name": "Chase"},
            # ... 15 банков
        ],
        "BUSINESS BANKS": [
            {"code": "biz_quickbooks", "name": "QuickBooks (LLC/ CORP)"},
            # ... 10 банков
        ],
        "CRYPTO BANKS": [
            {"code": "crypto_cashapp", "name": "Cash App + BTC"},
            # ... 6 банков
        ]
    }
}
```

**Маппинг сервисов на категории:**

```python
SERVICE_TO_CATEGORY_MAPPING = {
    # Banks - VCC
    "vcc_chime": "🏦 BANKS",
    "vcc_paypal": "🏦 BANKS",
    # ... все VCC банки
    
    # Banks - Personal
    "pers_citi": "🏦 BANKS",
    "pers_chase": "🏦 BANKS",
    # ... все Personal банки
    
    # Banks - Business
    "biz_quickbooks": "🏦 BANKS",
    # ... все Business банки
    
    # Banks - Crypto
    "crypto_cashapp": "🏦 BANKS",
    # ... все Crypto банки
}
```

**Функции:**

```python
def get_category_by_service(service_name: str) -> str:
    """Получить категорию по названию сервиса"""

def get_services_by_category(category: str) -> list:
    """Получить все сервисы категории"""

def get_service_name_by_code(code: str) -> str:
    """Получить название сервиса по коду"""
```

---

## 3. Brute Bank - Группы и категории

### 3.1 Модель: `BruteBankGroup`

**Файл:** `shared/database/models.py` (строки 1817-1833)

```python
class BruteBankGroup(Base):
    """Группа Brute Bank на уровне банка/витрины"""
    __tablename__ = "brute_bank_groups"
    
    id: int
    group_key: str          # Уникальный ключ (bank_code|attributes)
    bank_code: str          # Код банка (chase, bofa, wells)
    bank_name: str          # Название банка (Chase, Bank of America)
    category: str           # vcc, personal, business, crypto
    attributes: str         # AN:RN+INST YODLEE, CHECKING, etc.
    position: int           # Порядок отображения
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

### 3.2 Генерация `group_key`

**Файл:** `shared/brute_bank_group_key.py`

```python
def make_brute_group_key(bank_code: str, attributes: Optional[str]) -> str:
    """
    Создает уникальный ключ для группы.
    
    Примеры:
    - make_brute_group_key("chase", None) → "chase"
    - make_brute_group_key("chase", "AN:RN") → "chase|an:rn"
    - make_brute_group_key("BOFA", "CHECKING") → "bofa|checking"
    """
    bc = (bank_code or "").strip().lower()
    attr = (attributes or "").strip()
    key = f"{bc}|{attr}" if attr else bc
    return key[:220]  # Обрезка до 220 символов
```

### 3.3 Категории Brute Bank

**Доступные категории:**
- `vcc` - VCC банки
- `personal` - Личные банки
- `business` - Бизнес банки
- `crypto` - Крипто банки
- `general` - Общая категория (по умолчанию)

**Примеры `attributes`:**
- `AN:RN` - Account Number + Routing Number
- `AN:RN+INST YODLEE` - + интеграция Yodlee
- `CHECKING` - Тип счета
- `SAVINGS` - Сберегательный счет
- `$1K-$5K` - Диапазон баланса

### 3.4 Модель: `BruteBankItem`

```python
class BruteBankItem(Base):
    """Отдельный combo (логин/пароль)"""
    __tablename__ = "brute_bank_items"
    
    id: int
    seller_id: int
    group_id: int           # FK → brute_bank_groups
    bank_name: str
    bank_code: str
    category: str           # vcc, personal, business, crypto
    credentials: dict       # {"login": "...", "password": "...", "extra": "..."}
    balance_info: str       # "$5,000" или "5K-10K"
    balance_range: str      # "$1K-$5K"
    account_type: str       # CHECKING, SAVINGS, BUSINESS
    account_details: str
    price: Decimal
    base_price: Decimal
    buyer_price: Decimal
    state: str              # US state (CA, NY, TX)
    moderation_status: str  # pending, approved, rejected
    status: str             # available, sold, reserved
    is_active: bool
```

---

## 4. Логика создания разделов

### 4.1 Menu Categories (Главное меню Mirror Bot)

**Файл:** `web_panel/api/menu_categories.py`

**Модель:** `MirrorMenuCategory`

```python
class MirrorMenuCategory(Base):
    __tablename__ = "mirror_menu_categories"
    
    id: int
    code: str               # banks, docs, fullz, etc.
    route_key: str          # banks_main, docs_main
    count_key: str          # banks_count (опционально)
    label_en: str           # "Banks"
    label_ru: str           # "Банки"
    label_zh: str           # "银行"
    label_es: str           # "Bancos"
    row_index: int          # Номер строки (0, 1, 2)
    position: int           # Позиция в строке (0, 1, 2)
    is_active: bool
```

**API эндпоинты:**

```python
POST /api/menu-categories
# Создать новую категорию меню

PUT /api/menu-categories/{id}
# Обновить категорию

POST /api/menu-categories/{id}/toggle
# Включить/выключить категорию
```

**Пример создания:**

```json
{
  "code": "new_section",
  "route_key": "new_section_main",
  "count_key": "new_section_count",
  "label_en": "New Section",
  "label_ru": "Новый раздел",
  "row_index": 2,
  "position": 0,
  "is_active": true
}
```

### 4.2 Brute Bank Groups (Админ-панель)

**Файл:** `web_panel/api/brute_bank.py`

**API эндпоинты:**

```python
POST /api/brute-bank/groups
# Создать новую группу банка

PUT /api/brute-bank/groups/{id}
# Обновить группу

POST /api/brute-bank/groups/{id}/toggle
# Включить/выключить группу
```

**Пример создания группы:**

```json
{
  "bank_code": "chase",
  "bank_name": "Chase Bank",
  "category": "personal",
  "attributes": "AN:RN+INST YODLEE",
  "position": 0,
  "is_active": true
}
```

**Автоматическая генерация `group_key`:**
```
bank_code="chase" + attributes="AN:RN" → group_key="chase|an:rn"
```

---

## 5. Запросы на создание новых категорий

### 5.1 Enroll Categories (Порталы)

**Модели:**

```python
class EnrollCategory(Base):
    """Предзагруженные порталы"""
    __tablename__ = "enroll_categories"
    
    id: int
    code: str               # fdecs, digitalcardservice, etc.
    name: str               # "FDECS", "Digital Card Service"
    position: int
    is_active: bool
    is_custom: bool         # True если создан по запросу селлера

class EnrollCategoryRequest(Base):
    """Запросы селлеров на новые порталы"""
    __tablename__ = "enroll_category_requests"
    
    id: int
    seller_id: int
    requested_name: str     # Название портала
    status: str             # pending, approved, rejected
    admin_note: str
    created_at: datetime
    resolved_at: datetime
```

**Процесс запроса:**

1. **Селлер** нажимает "📝 Request new portal category"
2. **Вводит название** портала (например, "NEWPORTAL")
3. **Создается запись** в `enroll_category_requests`:
   ```python
   EnrollCategoryRequest(
       seller_id=seller.id,
       requested_name="NEWPORTAL",
       status="pending"
   )
   ```
4. **Модератор** видит запрос в админ-панели
5. **Одобрение**: создается новая запись в `enroll_categories`:
   ```python
   EnrollCategory(
       code="newportal",
       name="NEWPORTAL",
       is_custom=True,
       is_active=True
   )
   ```
6. **Селлер получает уведомление** и может загружать в новую категорию

**Файл:** `seller_bot/handlers/special_products.py` (строки 370-431)

```python
# Кнопка запроса
rows.append([InlineKeyboardButton(
    text="📝 Request new portal category",
    callback_data=f"seller_enroll_cat:{ENROLL_REQ_CODE}"
)])

# Обработка запроса
@router.message(AddEnrollStates.waiting_request_name, F.text)
async def add_enroll_request_name(message, state, session, seller):
    name = message.text.strip()
    session.add(EnrollCategoryRequest(
        seller_id=seller.id,
        requested_name=name,
        status="pending"
    ))
    await session.commit()
    await message.answer(
        "Request submitted. Our team will review within 1–6 hours."
    )
```

### 5.2 Selfreg CC Categories (Банки для Selfreg CC)

**Модели:**

```python
class SelfregCCCategory(Base):
    """Предзагруженные банки для Selfreg CC"""
    __tablename__ = "selfreg_cc_categories"
    
    id: int
    code: str               # chase, bofa, wells, etc.
    name: str               # "Chase", "Bank of America"
    position: int
    is_active: bool
    is_custom: bool         # True если создан по запросу

class SelfregCCCategoryRequest(Base):
    """Запросы селлеров на новые банки"""
    __tablename__ = "selfreg_cc_category_requests"
    
    id: int
    seller_id: int
    requested_name: str     # Название банка
    status: str             # pending, approved, rejected
    admin_note: str
    created_at: datetime
    resolved_at: datetime
```

**Процесс запроса:**

1. **Селлер** нажимает "📝 Request new bank category"
2. **Вводит название** банка (например, "New Bank")
3. **Создается запись** в `selfreg_cc_category_requests`
4. **Модератор** одобряет → создается `SelfregCCCategory` с `is_custom=True`
5. **Селлер** может загружать в новую категорию

**Файл:** `seller_bot/handlers/special_products.py` (строки 540-599)

```python
# Кнопка запроса
rows.append([InlineKeyboardButton(
    text="📝 Request new bank category",
    callback_data=f"seller_selfreg_cc_cat:{SELFREG_CC_REQ_CODE}"
)])

# Обработка запроса
@router.message(AddSelfregCCStates.waiting_request_name, F.text)
async def add_selfreg_cc_request_name(message, state, session, seller):
    name = message.text.strip()
    session.add(SelfregCCCategoryRequest(
        seller_id=seller.id,
        requested_name=name,
        status="pending"
    ))
    await session.commit()
    await message.answer(
        "Request submitted. Our team will review within 1–6 hours."
    )
```

---

## 6. API эндпоинты

### 6.1 Menu Categories

```
GET    /api/menu-categories              # Список всех категорий
GET    /api/menu-categories/{id}         # Получить категорию
POST   /api/menu-categories              # Создать категорию
PUT    /api/menu-categories/{id}         # Обновить категорию
POST   /api/menu-categories/{id}/toggle  # Включить/выключить
```

### 6.2 Brute Bank Groups

```
GET    /api/brute-bank/stats             # Статистика
GET    /api/brute-bank/groups            # Список групп
POST   /api/brute-bank/groups            # Создать группу
PUT    /api/brute-bank/groups/{id}       # Обновить группу
POST   /api/brute-bank/groups/{id}/toggle # Включить/выключить
```

### 6.3 Brute Bank Items

```
GET    /api/brute-bank/items             # Список items
GET    /api/brute-bank/items/{id}        # Получить item
PUT    /api/brute-bank/items/{id}        # Обновить item
POST   /api/brute-bank/items/{id}/approve   # Одобрить
POST   /api/brute-bank/items/{id}/reject    # Отклонить
POST   /api/brute-bank/items/{id}/toggle    # Включить/выключить
```

---

## 7. Модели БД

### 7.1 Сводная таблица

| Модель | Таблица | Назначение |
|--------|---------|------------|
| `MirrorMenuCategory` | `mirror_menu_categories` | Категории главного меню |
| `BankItem` | `bank_items` | Банки в каталоге (БД) |
| `BruteBankGroup` | `brute_bank_groups` | Группы Brute Bank |
| `BruteBankItem` | `brute_bank_items` | Отдельные combos |
| `EnrollCategory` | `enroll_categories` | Порталы для Enroll |
| `EnrollCategoryRequest` | `enroll_category_requests` | Запросы на порталы |
| `SelfregCCCategory` | `selfreg_cc_categories` | Банки для Selfreg CC |
| `SelfregCCCategoryRequest` | `selfreg_cc_category_requests` | Запросы на банки |

### 7.2 Связи

```
BruteBankGroup (1) ←→ (N) BruteBankItem
    ↓
group_id

EnrollCategory (1) ←→ (N) SellerEnrollItem
    ↓
enroll_category_id

SelfregCCCategory (1) ←→ (N) SellerSelfregCCItem
    ↓
selfreg_cc_category_id
```

---

## 8. Примеры использования

### 8.1 Загрузка Brute Bank (Seller Bot)

```python
# 1. Селлер выбирает "Upload Brute Bank"
# 2. Выбирает режим: Single / Bulk
# 3. Вводит bank_name: "Chase"
# 4. Вводит bank_code: "chase"
# 5. Вводит attributes: "AN:RN+INST YODLEE" (опционально)
# 6. Вводит credentials: login|password
# 7. Вводит balance_info: "$5,000"
# 8. Вводит price: "25.00"

# Система автоматически:
# - Генерирует group_key = "chase|an:rn+inst yodlee"
# - Находит или создает BruteBankGroup
# - Создает BruteBankItem с group_id
# - Устанавливает moderation_status = "pending"
```

### 8.2 Запрос новой категории Enroll

```python
# 1. Селлер выбирает "Add Enroll Item"
# 2. Видит список порталов + кнопку "📝 Request new portal category"
# 3. Нажимает кнопку запроса
# 4. Вводит название: "NEWPORTAL"
# 5. Система создает EnrollCategoryRequest(status="pending")
# 6. Модератор одобряет → создается EnrollCategory(is_custom=True)
# 7. Селлер получает уведомление
# 8. Теперь может загружать в "NEWPORTAL"
```

### 8.3 Создание группы Brute Bank (Admin Panel)

```python
# POST /api/brute-bank/groups
{
  "bank_code": "wells",
  "bank_name": "Wells Fargo",
  "category": "personal",
  "attributes": "CHECKING",
  "position": 5,
  "is_active": true
}

# Система автоматически:
# - Генерирует group_key = "wells|checking"
# - Создает BruteBankGroup
# - Теперь селлеры могут загружать items в эту группу
```

---

## 9. Файлы для изучения

### 9.1 Каталоги
- `shared/catalog_banks.py` - хардкодированный каталог банков
- `shared/catalog.py` - логика получения банков
- `web_panel/constants/categories.py` - все категории веб-панели

### 9.2 API
- `web_panel/api/menu_categories.py` - управление категориями меню
- `web_panel/api/brute_bank.py` - управление Brute Bank

### 9.3 Seller Bot
- `seller_bot/handlers/special_products.py` - запросы категорий (Enroll, Selfreg CC)
- `seller_bot/handlers/brute_bank.py` - загрузка Brute Bank

### 9.4 Модели
- `shared/database/models.py` - все модели БД
- `shared/brute_bank_group_key.py` - генерация group_key

### 9.5 Документация
- `docs/COMPLETE_PRODUCT_FIELDS_REFERENCE.md` - полный справочник полей
- `docs/DATABASE_SCHEMA.md` - схема БД
- `DATABASE_SCHEMA.md` - краткая схема

---

## 10. Итоги

✅ **Предзагруженные каталоги:**
- 54 банка в `catalog_banks.py` (VCC, Personal, Business, Crypto, Merchant)
- 8 категорий в `categories.py` (eSIM, Documents, PROS & FULLZ, Banks, Accounts, Add Info, Search, Credit Reports)

✅ **Brute Bank:**
- Группы (`BruteBankGroup`) с уникальным `group_key`
- Items (`BruteBankItem`) привязаны к группам
- Категории: vcc, personal, business, crypto, general
- Атрибуты: AN:RN, CHECKING, SAVINGS, balance ranges

✅ **Запросы на категории:**
- Enroll: `EnrollCategoryRequest` → `EnrollCategory` (is_custom=True)
- Selfreg CC: `SelfregCCCategoryRequest` → `SelfregCCCategory` (is_custom=True)
- Модерация: 1-6 часов

✅ **API:**
- Menu Categories: создание/редактирование категорий меню
- Brute Bank Groups: управление группами банков
- Полный CRUD для всех сущностей

---

**Дата создания:** 2026-03-23  
**Версия:** 1.0  
**Статус:** ✅ Полная документация
