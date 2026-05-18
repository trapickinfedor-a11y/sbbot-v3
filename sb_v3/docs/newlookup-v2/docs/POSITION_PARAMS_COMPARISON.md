# Полный список параметров позиций и сравнение с формулами

## Твои формулы

| Тип | Формула |
|-----|---------|
| **Bank** | тип товара + цена + чат + остаток |
| **CC** | тип карты + цена + данные карты |
| **Brute** | банк + range + account_type + credentials + price |

---

## 1. Bank позиция (`SellerBank`)

### Все параметры в коде

| Параметр | Тип | Описание |
|----------|-----|----------|
| `id` | int | PK |
| `seller_id` | int | FK → sellers |
| `upload_batch_id` | int? | FK → seller_upload_batches (партия загрузки) |
| `bank_name` | str | Название банка |
| `bank_code` | str | Код банка в каталоге |
| `category` | str | vcc, personal, business, crypto |
| `seller_price` | Decimal | Цена селлера |
| `buyer_price` | Decimal | Цена для покупателя |
| `is_in_stock` | bool | В наличии |
| `stock_count` | int | Остаток |
| `description` | str? | Описание |
| `has_chat` | bool | Чат с селлером (on/off) |
| `is_active` | bool | Активен |
| `moderation_status` | str | pending_moderation, approved, rejected, changes_requested, suspended |
| `moderation_comment` | str? | Комментарий модератора |
| `moderated_at` | datetime? | Когда модерировали |
| `moderated_by` | int? | Admin telegram_id |
| `created_at` | datetime | |
| `updated_at` | datetime | |

### Сопоставление с формулой

| Твой термин | В коде |
|-------------|--------|
| **тип товара** | `bank_code` + `category` (+ `bank_name`) |
| **цена** | `seller_price` / `buyer_price` |
| **чат** | `has_chat` |
| **остаток** | `stock_count` |

✅ Все параметры из формулы есть в коде.

---

## 2. CC позиция (`SellerCCItem`)

### Все параметры в коде

| Параметр | Тип | Описание |
|----------|-----|----------|
| `id` | int | PK |
| `seller_id` | int | FK → sellers |
| `upload_batch_id` | int? | FK → seller_upload_batches |
| `item_name` | str | Название позиции |
| `cc_code` | str | Тип карты (код в каталоге) |
| `category_code` | str | Категория CC |
| `seller_price` | Decimal | Цена селлера |
| `buyer_price` | Decimal | Цена для покупателя |
| `is_in_stock` | bool | В наличии |
| `stock_count` | int | Остаток |
| `description` | str? | Описание |
| `extra_data` | dict? | JSON — данные карты |
| `is_active` | bool | Активен |
| `is_approved` | bool | deprecated, использовать moderation_status |
| `moderation_status` | str | pending_moderation, approved, rejected, changes_requested, suspended |
| `moderation_comment` | str? | |
| `moderated_at` | datetime? | |
| `moderated_by` | int? | Admin telegram_id |
| `created_at` | datetime | |
| `updated_at` | datetime | |

### Формат `extra_data` (данные карты)

Строка при вводе: `BIN|Card|Exp|CVC|Type|Level|Bank|Country`

| Поле в extra_data | Описание |
|-------------------|----------|
| `bin` | BIN (первые 6 цифр) |
| `card` | Номер карты |
| `exp` | Срок действия |
| `cvc` | CVC |
| `type` | Тип (Visa, MC и т.п.) |
| `level` | Уровень карты |
| `bank` | Банк |
| `country` | Страна |

### Сопоставление с формулой

| Твой термин | В коде |
|-------------|--------|
| **тип карты** | `cc_code` + `category_code` |
| **цена** | `seller_price` / `buyer_price` |
| **данные карты** | `extra_data` (bin, card, exp, cvc, type, level, bank, country) |

✅ Все параметры из формулы есть в коде.

---

## 3. Brute позиция (`BruteBankItem`)

### Все параметры в коде

| Параметр | Тип | Описание |
|----------|-----|----------|
| `id` | int | PK |
| `seller_id` | int | FK → sellers |
| `upload_batch_id` | int? | FK → seller_upload_batches |
| `group_id` | int? | FK → brute_bank_groups |
| `bank_name` | str | Название банка |
| `bank_code` | str | Код банка |
| `category` | str | vcc, personal, business, crypto |
| `balance_range` | str? | Диапазон баланса |
| `account_type` | str? | CHECKING, SAVINGS, BUSINESS, MONEY MARKET |
| `credentials` | dict | JSON: login, password, extra |
| `balance_info` | str? | "$12,450" — отображаемый баланс |
| `account_details` | str? | Доп. описание |
| `price` | Decimal | Цена |
| `status` | str | available, sold, removed |
| `moderation_status` | str | pending, approved, rejected |
| `moderation_comment` | str? | |
| `moderated_by` | int? | |
| `buyer_user_id` | int? | Кто купил |
| `mirror_bot_id` | int? | FK → mirror_bots |
| `is_active` | bool | |
| `created_at` | datetime | |
| `approved_at` | datetime? | |
| `sold_at` | datetime? | |

### Формат `credentials`

JSON: `{"login": "...", "password": "...", "extra": "..."}`

Bulk-формат строки: `login|password|balance|price|balance_range|account_type|extra`

| Позиция | Поле | Описание |
|---------|------|----------|
| 0 | login | Логин |
| 1 | password | Пароль |
| 2 | balance_info | Баланс (отображаемый) |
| 3 | price | Цена |
| 4 | balance_range | Диапазон |
| 5 | account_type | Тип аккаунта |
| 6 | extra | Доп. данные |

### Сопоставление с формулой

| Твой термин | В коде |
|-------------|--------|
| **банк** | `bank_code` + `bank_name` |
| **range** | `balance_range` |
| **account_type** | `account_type` |
| **credentials** | `credentials` (login, password, extra) |
| **price** | `price` |

✅ Все параметры из формулы есть в коде.

---

## Сравнение: твои формулы vs код

| Формула | Параметры | В коде | Статус |
|---------|-----------|--------|--------|
| **Bank** | тип товара | bank_code, category | ✅ |
| | цена | seller_price, buyer_price | ✅ |
| | чат | has_chat | ✅ |
| | остаток | stock_count | ✅ |
| **CC** | тип карты | cc_code, category_code | ✅ |
| | цена | seller_price, buyer_price | ✅ |
| | данные карты | extra_data | ✅ |
| **Brute** | банк | bank_code, bank_name | ✅ |
| | range | balance_range | ✅ |
| | account_type | account_type | ✅ |
| | credentials | credentials | ✅ |
| | price | price | ✅ |

---

## Дополнительно: что есть в коде, но не в формулах

- **Модерация:** moderation_status, moderation_comment, moderated_at, moderated_by
- **Партии:** upload_batch_id (для batch-модерации)
- **Служебные:** seller_id, is_active, created_at, updated_at
- **Bank:** description
- **CC:** item_name, stock_count, description
- **Brute:** balance_info, account_details, status, group_id

---

## Спецификация SELLER_BOT_SPEC vs код

| В спецификации | В коде | Примечание |
|----------------|--------|------------|
| Bank: brute / selfreg / log | brute без category; selfreg/log через bank-flow | brute — отдельная модель `BruteBankItem`; seller не выбирает category вручную |
| CC: with_zip / with_fullz | — | Нет явных полей; можно добавить в category_code или отдельное поле |
| Enrol | — | Отдельной модели нет |
| Deposit: Banks $100, CC $150 | deposit_balance | В коде есть deposit_balance; лимиты по типу — в логике бота (BANK_DEPOSIT, CC_DEPOSIT) |
| product_type, product_subtype | — | В SellerOrder/SellerBank не добавлены; можно добавить |
