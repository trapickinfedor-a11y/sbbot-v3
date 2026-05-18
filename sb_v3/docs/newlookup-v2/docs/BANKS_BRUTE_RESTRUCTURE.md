# Реструктуризация Banks и Brute Bank

## Текущее состояние

### Banks (vcc, personal, business, crypto)
- **BankItem** (БД): bank_code, name, category, section (order/stock), price
- **BankData** (хардкод): fallback если BankItem пусто
- **Stock:** SellerBank.is_in_stock, stock_count — у селлеров
- **Flow:** banks → категория → список банков → bank_item → купить

### Brute Bank
- **BruteBankItem** (БД): bank_name, bank_code, credentials, balance_info, price
- **Flow:** brute идёт отдельной веткой; seller-flow без выбора category
- **Селлер:** загружает по одному item (банк → код → credentials → баланс → цена)

---

## Новая логика (по скринам)

### 1. Banks (vcc, pers, biz, crypto) — полная смена

**Структура:**
```
Banks
├── 💳 VCC
│   ├── В наличии [N] — список BankItem с section=stock, quantity
│   └── Под заказ — список BankItem с section=order
├── 🏦 Personal
│   ├── В наличии [N]
│   └── Под заказ
├── 🏢 Business
│   ├── В наличии [N]
│   └── Под заказ
├── 🪙 Crypto
│   ├── В наличии [N]
│   └── Под заказ
└── 🔓 Brute Bank (отдельная логика)
```

**Изменения:**
- В каждой категории два подраздела: **В наличии** (available [колво]) и **Под заказ**
- BankItem: добавить `stock_quantity` (int) для section=stock
- Полное управление в админке: CRUD для BankItem, переключение section, quantity

---

### 2. Brute Bank — новая иерархия

**Уровень 1 — список банков:**
```
CentraCU [AN:RN] [2]
Comerica [AN:RN+INST YODLEE+INST FINICITY+NAME+A...] [1]
DiscoverBank [AN:RN+INST FINICITY] [174]
...
Стр. 1 | Стр. 2
Назад | Корзина (146$)
Меню
```

- Группировка по **bank_code** (или bank_name)
- Атрибуты `[AN:RN]`, `[AN:RN+INST YODLEE+...]` — теги/фичи (селлера или общие)
- `[N]` — количество доступных по этому банку

**Уровень 2 — после клика на банк (распределение селлера):**
```
9-12k 226$ SAVINGS [3]
12-15k 249$ SAVINGS [1]
15-18k 271$ BUSINESS [2]
18-21k 292$ MONEY MARKET [10]
21-25k 313$ CHECKING [5]
25-35k 358$ CHECKING [18]
...
```

- **balance_range:** 9-12k, 12-15k, ...
- **price:** 226$, 249$, ...
- **account_type:** SAVINGS, BUSINESS, MONEY MARKET, CHECKING
- **quantity [N]:** сколько в наличии

**Селлер задаёт:** при добавлении item указывает bank_code, balance_range, account_type, price. Варианты с одинаковыми параметрами группируются, quantity = count.

---

## Модели и миграции

### BankItem (расширение)
```python
# Уже есть: bank_code, name, category, section (order/stock), price
# Добавить:
stock_quantity: int = 0  # для section=stock — сколько в наличии
```

### BruteBankItem (расширение)
```python
# Уже есть: bank_name, bank_code, category, credentials, balance_info, price
# Добавить:
balance_range: str  # "9-12k", "12-15k", "25-35k"
account_type: str   # "SAVINGS", "BUSINESS", "MONEY MARKET", "CHECKING"
# attributes для уровня 1 — можно вынести в отдельную таблицу или JSON
attributes: str     # "AN:RN", "AN:RN+INST YODLEE+INST FINICITY+NAME" (опционально)
```

### BruteBankAttributes (опционально)
Если атрибуты общие для банка, а не для item:
```python
# bank_code -> ["AN:RN", "AN:RN+INST YODLEE", ...]
# Или в BankItem-подобной справочной таблице
```

---

## API и админка

### Banks (bank_items)
- CRUD BankItem
- Фильтр: category, section (stock/order)
- Для section=stock: редактирование stock_quantity
- Разделы в UI: В наличии | Под заказ

### Brute Bank
- CRUD BruteBankItem
- Новые поля: balance_range, account_type
- Группировка в списке: по bank_code → по (balance_range, account_type, price)
- Селлер-панель: при добавлении — выбор/ввод balance_range, account_type

---

## Mirror Bot — хендлеры

### Banks
- `banks_vcc` → показать: В наличии [N] | Под заказ
- В наличии: список BankItem (section=stock) с quantity
- Под заказ: список BankItem (section=order)

### Brute Bank
- `banks_brute` → список банков (GROUP BY bank_code), атрибуты, quantity
- `brute_bank:{bank_code}` → варианты (balance_range, price, account_type, quantity)
- `brute_item:{id}` или `brute_variant:{bank_code}:{range}:{type}:{price}` → покупка

---

## Seller Bot — Brute Bank

- При загрузке: bank_name, bank_code, category, **balance_range**, **account_type**, credentials, price
- balance_range: выбор из списка или ввод (9-12k, 12-15k, ...)
- account_type: SAVINGS, BUSINESS, MONEY MARKET, CHECKING, ...

---

## Порядок внедрения

1. **Миграции:** добавить поля в BankItem, BruteBankItem
2. **API:** обновить bank_items, brute_bank
3. **Админка:** UI для stock_quantity, balance_range, account_type
4. **Mirror Bot:** новая навигация Banks и Brute Bank
5. **Seller Bot:** обновить flow загрузки Brute Bank
