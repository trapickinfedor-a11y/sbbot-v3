# КРАТКИЙ СПРАВОЧНИК: ВСЕ РАЗДЕЛЫ
## Шпаргалка для разработчика

---

## 📊 СВОДНАЯ ТАБЛИЦА

| # | Раздел | Категорий | Банков | Полей | Баланс | Moderation Request |
|---|--------|-----------|--------|-------|--------|-------------------|
| 1 | Banks | 5 | 51 | 20 | ❌ НЕТ | ✅ |
| 2 | Brute | 1 | 67 | 15 | ✅ ДА | ✅ |
| 3 | CC | 2 | BIN | 18 | ❌ | ❌ |
| 4 | NFC | 3 | 20 | 12 | ✅ | ❌ |
| 5 | OTP | 1 | 20 | 14 | ✅ | ❌ |
| 6 | Selfreg CC | 1 | 12 | 16 | ❌ | ✅ |
| 7 | Enrollment | 12 | 20 | 20 | ✅ | ✅ |
| 8 | Logs | 1 | 20 | 22 | ✅ | ❌ |
| 9 | Checks | 4 | 20 | 10 | ❌ | ❌ |
| 10 | Documents | 4 | - | 12 | ❌ | ❌ |
| 11 | Fullz | 2 | - | 15 | ❌ | ❌ |
| ~~12~~ | ~~Selfreg BA~~ | - | - | - | - | ❌ **УДАЛЕН** |

---

## 🏦 BANKS КАТЕГОРИИ

```
vcc (14 банков)
├─ Chime VCC, PayPal VCC, Current VCC...
personal (13 банков)
├─ Chase, BofA, Wells Fargo...
business (9 банков)
├─ QuickBooks, Mercury, Relay...
crypto (6 банков)
├─ Coinbase, Binance, Cash App...
merchant (9 банков)
├─ Stripe, PayPal Business...
```

**ВСЕГО: 51 банк**

---

## 🔓 BRUTE BANK СПИСОК (67)

```
3RiversFCU, 53, AllianceCCU, BECU, Bellco, BMO, Canvas,
CentraCU, Comerica, Connexuscu, CorningCU, DesertfinancialCU,
DFCUFinancial, DiscoverBank, EducatorsCU, EmpowerFCU,
EnrichmentFCU, FACU, 903 Pl, Familytrust, FibreFCU,
FirstentCU, FloridaCU, FNBO, FourLeafFCU, GlobalCU,
GoldenwestCU, GrowFinancalFCU, GTE, HarboreOne, Huntington,
HVCU, Jeffersonfinancial, KFCU, Kinecta, Landmarkcu, MACU,
MaineStateCU, Members1st, MSUFCU, myoccu, NasaFCU,
PacificCrestFCU, Parkcommunity, Patelco, Pefcu, PSFCU,
QualstarCU, Radiantcu, REVFCU, RivermarkCCU, Santanderbank,
SchoolsFirst, SkylaCU, Sunward, Synovus, UnitusCCU,
ValleyStrong, VantageWest, VeridianCU, WescomCU
```

---

## 🔄 MODERATION REQUEST FLOW

### Banks
```
Name → State → ZIP → Has Docs? → Doc Type → Description
```

### Brute Bank
```
Name → Code → Attributes → Category
```

### Selfreg CC
```
Bank Name
```

### Enrollment
```
Portal Name
```

---

## 📄 BULK FORMATS

### CC/Debit
```
NUMBER|EXP_MM|EXP_YY|CVV|FNAME|LNAME|ADDRESS|CITY|STATE|ZIP|COUNTRY|NON_VBV
```

### Brute Bank
```
BANK|LOGIN|PASS|AN|RN|BALANCE|STATE|NAME|ADDRESS|ZIP|price
```

### Logs
```
LOGIN|PASS|AN|RN|BALANCE|STATE|ROUTING|NAME|ADDRESS|ZIP|CVV|ZELLE|WIRE|BT|PROMO|SAFEPASS|EMAIL|SCREENSHOT
```

### Checks (ZIP)
```
check_data.json + scan.jpg
```

---

## ⚠️ ВАЖНЫЕ ЗАМЕТКИ

1. **Balance в Banks**: ❌ УДАЛЕНО из UI, есть в БД но не используется
2. **Selfreg BA**: ❌ ПОЛНОСТЬЮ УДАЛЕН (слияние с Banks)
3. **Custom Request**: ✅ Есть в Banks, Brute, Selfreg CC, Enrollment
4. **NON-VBV цена**: ✅ Только в CC/Debit (отдельная цена)
5. **Return Item**: ✅ Только в Banks и Selfreg CC

---

## 🔑 МОДЕЛИ ДАННЫХ

### SellerBankItem (20 полей)
```python
bank, category, bank_code, product_type, registration_date,
state, zip, price,
email_access, has_phone, phone_days_remaining, phone_renewable,
phone_can_swap, has_ssn, has_docs,
return_item_enabled, return_days,
seller_id, moderation_status, created_at
```

### BruteBankItem (15 полей)
```python
bank_name, category, attributes, exact_balance, account_type,
has_login_password, has_account_routing, has_holder_name_address,
has_additional_info, has_docs,
login, password, account_number, routing_number,
holder_name, holder_address, additional_info,
state, zip, price,
seller_id, moderation_status, group_id, created_at
```

### SellerCCItem (18 полей)
```python
card_number, exp_month, exp_year, cvv, card_brand, card_type,
card_category, is_non_vbv,
first_name, last_name, billing_address, billing_city,
billing_state, billing_zip, billing_country, phone, email,
price, non_vbv_price,
seller_id, moderation_status, created_at
```

---

## 🎯 ПРИОРИТЕТЫ ДОРАБОТКИ MINI APP

**P0 (Критично):**
- ✅ Кнопка "Request new bank" (Banks, Brute)
- ✅ Исправить format: "bank" вместо "selfreg_ba"
- ✅ Решить с Balance (удалить из БД?)

**P1 (Важно):**
- Генерация описаний товаров
- Валидация данных
- BIN lookup унификация

**P2 (Желательно):**
- Преобразование форматов
- Превью перед отправкой
- Кэширование

---

**ВЕРСИЯ:** 1.0  
**ДАТА:** 2026-03-24
