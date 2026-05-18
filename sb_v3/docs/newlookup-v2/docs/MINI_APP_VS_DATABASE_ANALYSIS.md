# Анализ несоответствий: Seller Mini App v2 vs Database Schema

**Дата:** 2026-03-24  
**Источники:**
- Mini App: `/tmp/seller_mini_app_temp/seller_mini_app_v2/client/src/components/tabs/UploadsTab.tsx`
- Database Schema: `docs/SELLER_PRODUCTS_DATABASE_SCHEMA.md`

---

## 🔴 Критические несоответствия

### 1. **Banks Section — НОВАЯ СЕКЦИЯ**

**Mini App имеет:**
```typescript
Section: "Banks" — VCC, Personal, Business, Crypto, Merchant
- 5 категорий банков
- Product Type для каждой категории
- Registration Date (MM/DD/YYYY)
- Balance
- Email/Phone Access + rental + extend/swap
- Return toggle
- Access file upload
```

**В нашей БД:**
- ❌ Такой секции НЕТ
- Есть только `Bank Selfregs` (SellerBankSelfregItem)
- Нет разделения на VCC/Personal/Business/Crypto/Merchant
- Нет поля `product_type`

**Решение:**
- [ ] Создать новую модель `SellerBankItem` с категориями
- [ ] Или расширить `SellerBankSelfregItem` добавив `category` и `product_type`

---

### 2. **Brute Bank — Разное количество банков**

**Mini App:**
```typescript
BRUTE_BANKS = 22 банка (плоский список)
```

**В нашей БД (catalog_banks.py):**
```
54 банка в 5 категориях:
- VCC: 14 банков
- Personal: 15 банков
- Business: 10 банков
- Crypto: 6 банков
- Merchant: 9 банков
```

**Решение:** ✅ **Использовать список из БД (54 банка) в Mini App**
- Mini App будет использовать категоризированный список из `catalog_banks.py`
- Seller выбирает категорию, затем банк из списка
- Поддерживается custom bank name для гибкости

---

### 3. **Selfreg CC — Разное количество банков**

**Mini App:**
```typescript
SELFREG_CC_BANKS = 12 банков:
Chase, Bank of America, Citi, Wells Fargo, Capital One, Discover,
American Express, US Bank, PNC Bank, TD Bank, Barclays, Synchrony

+ Card Names для каждого банка (6-12 карт на банк)
```

**В нашей БД:**
```
5 банков:
CITI, Chase, Wells Fargo, ONEPAY, BOA
```

**Проблема:**
- Mini App: 12 банков с детальными списками карт
- БД: 5 банков без списков карт
- Mini App более детальный!

**Решение:** ✅ **Реализовано**
- ✅ Расширить БД до 13 банков (5 базовых + 8 новых)
- ✅ Создана таблица `selfreg_cc_card_names` для хранения названий карт
- ✅ 78 названий карт загружены через seed скрипт

---

### 4. **Enroll Portals — Небольшое расхождение**

**Mini App:**
```typescript
12 порталов:
FDECS, Digital Card Service, MyCardInfo, Card Suite Light, CardNav,
FIREFIGHTERS, Coast Central, Web Access, Card Suite, MyAccountAccess,
CentreSuite (minik), Elan
```

**В нашей БД:**
```
11 порталов (без Elan)
```

**Решение:**
- [ ] Добавить `Elan` в БД

---

### 5. **Selfreg BA — Объединено с Banks**

**Решение:** ✅ **Selfreg BA = Banks Section**

**Mini App имел:**
```typescript
Section: "Selfreg BA" — Self-registered bank accounts
```

**Новое решение:**
- ✅ Selfreg BA объединен с универсальной секцией Banks
- ✅ Banks поддерживает все категории: VCC, Personal, Business, Crypto, Merchant
- ✅ Один интерфейс для всех банковских продуктов
- ✅ Bulk upload поддерживается через Banks section

**Преимущества:**
- Упрощенная структура (одна секция вместо двух)
- Единый интерфейс загрузки
- Меньше дублирования кода

---

## 🟡 Средние несоответствия

### 6. **Product Types в Banks**

**Mini App:**
```typescript
PRODUCT_TYPES = {
  vcc:      ["Virtual Card", "Prepaid Card", "Gift Card"],
  personal: ["Checking Account", "Savings Account", "Money Market", "CD Account"],
  business: ["Business Checking", "Business Savings", "Merchant Account", "LLC Account", "Corp Account"],
  crypto:   ["Spot Account", "Futures Account", "Wallet", "Exchange Account"],
  merchant: ["Merchant Account", "Business Account", "Payment Gateway", "LLC Account"],
}
```

**В нашей БД:**
- ❌ Поля `product_type` НЕТ в `SellerBankSelfregItem`

**Решение:**
- [ ] Добавить поле `product_type: String(100)` в модель

---

### 7. **NFC/OTP Banks**

**Mini App:**
```typescript
NFC_OTP_BANKS = 20 банков:
Chase, Bank of America, Wells Fargo, Citi, US Bank, PNC Bank,
TD Bank, Capital One, Regions Bank, Truist, Fifth Third, KeyBank,
Huntington, Citizens Bank, M&T Bank, Ally Bank, SunTrust, BB&T,
Navy Federal CU, USAA
```

**В нашей БД:**
- ❌ Нет предзагруженного списка банков для NFC/OTP
- Seller может указать любой bank_name

**Решение:**
- [ ] Добавить предзагруженный список (опционально)
- [ ] Или оставить как есть (любой bank_name)

---

### 8. **CC Bulk Format**

**Mini App:**
```typescript
Bulk Format:
NUMBER|EXP|CVV|NAME|ZIP|STATE|COUNTRY|BANK|TYPE|NON_VBV

Two prices:
- Regular price
- NON VBV price
```

**В нашей БД:**
```
Bulk Format:
NUMBER|EXP|CVV|TYPE|BRAND|LVL|BANK|COUNTRY|HOLDER|ADDR|STATE|CITY|ZIP|Info|REF|PRICE

One price:
- seller_price
```

**Проблема:**
- Разные форматы!
- Mini App: упрощенный формат + 2 цены
- БД: расширенный формат + 1 цена

**Решение:**
- [ ] **Вариант A:** Использовать формат из БД (более полный)
- [ ] **Вариант B:** Поддерживать оба формата
- [ ] **Вариант C:** Унифицировать на один формат

---

### 9. **Brute Bank Bulk Format**

**Mini App:**
```typescript
Format:
BANK|LOGIN|PASS|AN|RN|BALANCE|STATE|NAME|ADDRESS|ZIP|price

Auto-detect attributes from non-empty fields
```

**В нашей БД:**
```
Format:
login|password|balance|price|balance_range|account_type|extra
```

**Проблема:**
- Разные форматы!
- Mini App: более детальный (AN, RN, NAME, ADDRESS, ZIP)
- БД: упрощенный

**Решение:**
- [ ] Использовать формат из Mini App (более полный)
- [ ] Обновить парсер в `seller_upload_pipeline_service.py`

---

### 10. **Logs Format**

**Mini App:**
```typescript
Format:
LOGIN|PASS|AN|RN|BALANCE|STATE|ROUTING|NAME|ADDRESS|ZIP|
CVV|ZELLE|WIRE|BT|PROMO|SAFEPASS|EMAIL|SCREENSHOT

Multiple accounts feature
```

**В нашей БД:**
```
Format:
SITE|LOGIN|PASS|COOKIES|BALANCE|STATE|ROUTING|NAME|...

Single account
```

**Проблема:**
- Mini App поддерживает multiple accounts
- БД: single account

**Решение:**
- [ ] Добавить поддержку multiple accounts в БД
- [ ] Создать связанную таблицу `SellerLogsAccount`

---

## 🟢 Совпадения (все ОК)

### ✅ Checks
- 4 типа: Personal, Business, Payroll, Cashier
- Совпадает полностью

### ✅ NFC Types
- 3 типа: Apple Pay, Google Pay, Other
- Совпадает полностью

### ✅ OTP SMS Access
- 2 типа: seller_mediated, account_access
- Совпадает (но названия разные: "In Chat" vs "seller_mediated")

---

## 📊 Сводная таблица параметров

### Banks (NEW)

| Параметр | Mini App | БД | Статус |
|----------|----------|-----|--------|
| category | ✅ vcc/personal/business/crypto/merchant | ❌ | 🔴 Добавить |
| bank_id | ✅ | ❌ | 🔴 Добавить |
| bank_name | ✅ | ✅ | ✅ |
| product_type | ✅ | ❌ | 🔴 Добавить |
| registration_date | ✅ MM/DD/YYYY | ✅ Date | ✅ |
| balance | ✅ | ❌ (всегда 0) | 🟡 Изменить |
| email_access | ✅ | ✅ has_email | ✅ |
| phone_access | ✅ | ✅ has_phone | ✅ |
| phone_rental_days | ✅ | ✅ phone_days_remaining | ✅ |
| phone_can_extend | ✅ | ✅ phone_renewable | ✅ |
| phone_can_swap | ✅ | ❌ | 🔴 Добавить |
| return_item | ✅ | ❌ | 🔴 Добавить |
| return_days | ✅ | ❌ | 🔴 Добавить |
| access_file | ✅ | ✅ credentials_file_path | ✅ |

### Brute Bank

| Параметр | Mini App | БД | Статус |
|----------|----------|-----|--------|
| mode | ✅ single/bulk | ❌ | 🟡 Опционально |
| bank_name | ✅ (22 банка) | ✅ (54 банка) | 🔴 Синхронизировать |
| exact_balance | ✅ | ❌ | 🔴 Добавить |
| account_type | ✅ CHECKING/SAVINGS/BUSINESS/MONEY MARKET | ✅ | ✅ |
| has_login | ✅ toggle | ❌ | 🔴 Добавить |
| login | ✅ | ✅ (encrypted) | ✅ |
| password | ✅ | ✅ (encrypted) | ✅ |
| has_an_rn | ✅ toggle | ❌ | 🔴 Добавить |
| account_number | ✅ | ❌ | 🔴 Добавить |
| routing_number | ✅ | ❌ | 🔴 Добавить |
| has_name_addr | ✅ toggle | ❌ | 🔴 Добавить |
| holder_name | ✅ | ❌ | 🔴 Добавить |
| address | ✅ | ❌ | 🔴 Добавить |
| has_add_info | ✅ toggle | ❌ | 🔴 Добавить |
| add_info | ✅ | ❌ | 🔴 Добавить |
| has_docs | ✅ toggle | ❌ | 🔴 Добавить |
| bulk_data | ✅ BANK\|LOGIN\|PASS\|AN\|RN\|... | ✅ (другой формат) | 🔴 Изменить формат |

### CC

| Параметр | Mini App | БД | Статус |
|----------|----------|-----|--------|
| mode | ✅ single/bulk | ❌ | 🟡 Опционально |
| number | ✅ | ✅ (encrypted) | ✅ |
| exp | ✅ | ✅ (encrypted) | ✅ |
| cvv | ✅ | ✅ (encrypted) | ✅ |
| holder_name | ✅ | ✅ fname+lname | ✅ |
| zip | ✅ | ✅ | ✅ |
| state | ✅ | ✅ | ✅ |
| country | ✅ | ✅ | ✅ |
| bank | ✅ (auto from BIN) | ✅ bank_name | ✅ |
| card_type | ✅ | ✅ | ✅ |
| is_non_vbv | ✅ toggle | ✅ | ✅ |
| price | ✅ | ✅ seller_price | ✅ |
| price_non_vbv | ✅ | ❌ | 🔴 Добавить |
| bulk_format | ✅ NUMBER\|EXP\|CVV\|NAME\|ZIP\|... | ✅ (другой) | 🔴 Унифицировать |

### Selfreg CC

| Параметр | Mini App | БД | Статус |
|----------|----------|-----|--------|
| bank_code | ✅ (12 банков) | ✅ (5 банков) | 🔴 Расширить до 12 |
| card_name | ✅ (списки карт) | ❌ | 🔴 Добавить |
| registration_date | ✅ MM/DD/YYYY | ❌ | 🔴 Добавить |
| has_vcc | ✅ toggle | ❌ | 🔴 Добавить |
| vcc_limit | ✅ | ✅ | ✅ |
| vcc_bin | ✅ | ❌ | 🔴 Добавить |
| state | ✅ | ✅ | ✅ |
| zip | ✅ | ✅ | ✅ |
| email_access | ✅ | ✅ has_email | ✅ |
| phone_access | ✅ | ✅ has_phone | ✅ |
| phone_rental_days | ✅ | ✅ phone_days_remaining | ✅ |
| phone_can_extend | ✅ | ✅ phone_renewable | ✅ |
| phone_can_swap | ✅ | ✅ phone_change_allowed | ✅ |
| return_item | ✅ toggle | ❌ | 🔴 Добавить |
| return_days | ✅ | ❌ | 🔴 Добавить |

### OTP

| Параметр | Mini App | БД | Статус |
|----------|----------|-----|--------|
| bank_name | ✅ (20 банков) | ✅ | ✅ |
| balance | ✅ | ✅ | ✅ |
| state | ✅ | ❌ | 🔴 Добавить |
| zip | ✅ | ❌ | 🔴 Добавить |
| sms_access_type | ✅ in_chat/file | ✅ seller_mediated/account_access | 🟡 Разные названия |
| has_fullz | ✅ toggle | ✅ | ✅ |
| fullz_first | ✅ | ❌ | 🔴 Добавить в extra_data |
| fullz_last | ✅ | ❌ | 🔴 Добавить в extra_data |
| fullz_dob | ✅ MM/DD/YYYY | ❌ | 🔴 Добавить в extra_data |
| fullz_ssn | ✅ | ❌ | 🔴 Добавить в extra_data |
| fullz_address | ✅ | ❌ | 🔴 Добавить в extra_data |
| fullz_city | ✅ | ❌ | 🔴 Добавить в extra_data |
| fullz_state | ✅ | ❌ | 🔴 Добавить в extra_data |
| fullz_zip | ✅ | ❌ | 🔴 Добавить в extra_data |
| fullz_phone | ✅ | ❌ | 🔴 Добавить в extra_data |
| fullz_email | ✅ | ❌ | 🔴 Добавить в extra_data |
| access_file | ✅ required | ✅ data_file_path | ✅ |

### Enrollment

| Параметр | Mini App | БД | Статус |
|----------|----------|-----|--------|
| portal_code | ✅ (12 порталов) | ✅ (11 порталов) | 🟡 Добавить Elan |
| bank_name | ✅ (22 банка) | ✅ | ✅ |
| has_name | ✅ toggle | ❌ | 🔴 Добавить |
| first_name | ✅ | ❌ | 🔴 Добавить |
| last_name | ✅ | ❌ | 🔴 Добавить |
| has_address | ✅ toggle | ✅ has_address | ✅ |
| address | ✅ | ❌ | 🔴 Добавить |
| city | ✅ | ❌ | 🔴 Добавить |
| state | ✅ | ❌ | 🔴 Добавить |
| zip | ✅ | ❌ | 🔴 Добавить |
| has_dob | ✅ toggle | ✅ has_dob | ✅ |
| dob | ✅ MM/DD/YYYY | ❌ | 🔴 Добавить |
| has_ssn | ✅ toggle | ✅ has_ssn | ✅ |
| ssn | ✅ | ❌ | 🔴 Добавить |
| has_phone | ✅ toggle | ❌ | 🔴 Добавить |
| phone | ✅ | ❌ | 🔴 Добавить |
| has_email | ✅ toggle | ❌ | 🔴 Добавить |
| email | ✅ | ❌ | 🔴 Добавить |
| add_info | ✅ | ❌ | 🔴 Добавить |
| has_docs | ✅ toggle | ✅ has_docs | ✅ |
| data_file | ✅ | ✅ data_file_path | ✅ |

---

## 🎯 Приоритеты исправлений

### Критично (должно быть исправлено):

1. **Banks Section** — решить: новая модель или расширить существующую
2. **Brute Bank списки** — синхронизировать 22 vs 54 банка
3. **Selfreg CC списки** — расширить с 5 до 12 банков
4. **Bulk форматы** — унифицировать CC и Brute Bank
5. **Return Item** — добавить поля во все модели где нужно

### Важно (желательно исправить):

6. **Product Types** — добавить в Banks
7. **OTP Fullz fields** — добавить детальные поля
8. **Enrollment fields** — добавить детальные поля
9. **Logs multiple accounts** — поддержка нескольких аккаунтов
10. **Elan portal** — добавить в Enroll

### Опционально (можно оставить как есть):

11. **NFC/OTP bank lists** — предзагруженные списки
12. **Mode field** — single/bulk индикатор
13. **SMS access naming** — in_chat vs seller_mediated

---

## 📝 Рекомендации

### Подход 1: Адаптировать Mini App под БД
- Изменить форматы в Mini App
- Использовать списки из БД
- Минимальные изменения в БД

### Подход 2: Адаптировать БД под Mini App
- Расширить модели БД
- Добавить новые поля
- Синхронизировать списки
- **Рекомендуется** ✅

### Подход 3: Гибридный
- Критичные вещи — адаптировать БД
- Некритичные — адаптировать Mini App
- Компромисс

---

**Следующие шаги:**
1. Обсудить какой подход выбрать
2. Создать список конкретных изменений
3. Обновить модели БД
4. Обновить Mini App (если нужно)
5. Синхронизировать списки банков/порталов

